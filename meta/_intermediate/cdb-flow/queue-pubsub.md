# QUEUE テーブル — 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-15
対象ソース:
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/qosorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`

---

## 1. Producer/Consumer ペア

### CONFIG_DB → orchagent QosOrch (SubscriberStateTable)

| 項目 | 値 |
|------|----|
| 購読方式 | `Orch(db, tableNames)` 基底クラスの `addConsumer()` 経由の `SubscriberStateTable` |
| keyspace パターン | `__keyspace@{config_db_id}__:QUEUE\|*` |
| 購読テーブル | `CFG_QUEUE_TABLE_NAME` (`QUEUE`) |
| Consumer クラス | `Consumer` (wraps `SubscriberStateTable`) — CONFIG_DB は `SubscriberStateTable` 固定 (`orch.cpp:1188-1190`) |
| ハンドラ登録 | `QosOrch::initTableHandlers()` で `CFG_QUEUE_TABLE_NAME → &QosOrch::handleQueueTable` を `m_qos_handler_map` に登録 (`qosorch.cpp:1334`) |
| 優先度 | `default_orch_pri` (= 0) |

QosOrch のコンストラクタは `Orch(db, tableNames)` を呼び出す。`tableNames` には `CFG_QUEUE_TABLE_NAME` を含む 15 テーブルが列挙される (`orchdaemon.cpp:367-383`)。

`Orch::addConsumer()` は CONFIG_DB を検出すると `SubscriberStateTable` を生成し `Consumer` でラップして `m_consumerMap` に追加する。

### APPL_DB 書き込みなし

QUEUE テーブルの処理は orchagent 内で完結する。QosOrch は CONFIG_DB の QUEUE エントリを読んで直接 SAI API を呼び出す。APPL_DB への中継は行わない。

---

## 2. keyspace notification (SubscriberStateTable)

`SubscriberStateTable` は CONFIG_DB の keyspace notification を使う。

```
PSUBSCRIBE __keyspace@{config_db_id}__:QUEUE|*
```

- 通知イベントの種類: `hset`, `hdel`, `del` などの hash 操作イベント
- `readData()` が `redisGetReply()` でイベントを受信し `m_keyspace_event_buffer` に蓄積
- `pops()` がバッファからキーを取り出し `m_table.get(key, ...)` で現在の hash 値を取得
- 初回起動時: `SubscriberStateTable` コンストラクタが `m_table.getKeys()` で既存キーを `m_buffer` に先読みし、起動前の設定も確実に処理する

---

## 3. select() ループと doTask

`orchdaemon.cpp:959`:
```cpp
ret = m_select->select(&s, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
```

- 1000 ms タイムアウト: タイムアウト時に `flush()` を呼び SAI パイプラインをフラッシュ
- イベント受信時: `(Executor *)s)->execute()` → `Consumer::drain()` → `QosOrch::doTask(Consumer&)` 呼び出し

### doTask 実行順序制御

`QosOrch::doTask()` (`qosorch.cpp:2231-2252`) はカスタム実行順序を実装する:

```cpp
// 1. PORT_QOS_MAP と QUEUE 以外のテーブルを先に処理 (scheduler, wred_profile 等の参照先)
for (const auto &it : m_consumerMap) {
    if (exec == port_qos_map_cfg_exec || exec == queue_exec) continue;
    exec->drain();
}
// 2. PORT_QOS_MAP を処理
port_qos_map_cfg_exec->drain();
// 3. 最後に QUEUE を処理 (参照先が揃った状態で実行)
queue_exec->drain();
```

**意図**: SCHEDULER / WRED_PROFILE が先に解決されてから QUEUE を処理することで `task_need_retry` の発生を最小化する。

### doTask ガード

```cpp
void QosOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return;  // 全ポート初期化待ち
    // ...
}
```

全ポートの初期化完了 (`PortInitDone`) まで QUEUE の処理を保留する。

---

## 4. handleQueueTable の動作フロー

```
Consumer::drain()
  → QosOrch::doTask(Consumer&)
    → m_qos_handler_map[CFG_QUEUE_TABLE_NAME](consumer, tuple)
      → QosOrch::handleQueueTable(consumer, tuple)
        → key トークン解析 (非 VOQ: 2 トークン, VOQ: 4 トークン)
        → parseIndexRange() でキュー範囲解析
        → SET: resolveFieldRefValue(scheduler) → applySchedulerToQueueSchedulerGroup()
        → SET: resolveFieldRefValue(wred_profile) → applyWredProfileToQueue()
        → DEL: removeObject()
```

| task_status | 条件 | 次の動作 |
|-------------|------|----------|
| `task_success` | SAI 呼び出し成功 | `m_toSync` から削除 |
| `task_invalid_entry` | key 不正 / index 範囲外 | `m_toSync` から削除 (silent drop) |
| `task_failed` | SAI エラー / 参照永続未解決 | `m_toSync` から削除, `return` (即終了) |
| `task_need_retry` | 参照先未解決 | `m_toSync` に残留 → 次ループで再試行 |

---

## 5. retry メカニズム

- `task_need_retry` 時はエントリが `m_toSync` に残る
- 次の SELECT イベント発火時 or 1000 ms タイムアウト時に `doTask()` が再度呼ばれ再試行
- 参照先 (`SCHEDULER`, `WRED_PROFILE`) が登録されると `doTask` の実行順序制御により即座に解決される

---

## 6. SAI 書き込み経路

```
QosOrch::applySchedulerToQueueSchedulerGroup()
  → sai_scheduler_group_api->set_scheduler_group_attribute(
        SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID, scheduler_profile_id)
  → (VOQ remote port は no-op で即 true 返却)

QosOrch::applyWredProfileToQueue()
  → sai_queue_api->set_queue_attribute(
        SAI_QUEUE_ATTR_WRED_PROFILE_ID, sai_wred_profile)
```

SAI 呼び出し結果は `handleSaiSetStatus(SAI_API_QUEUE, ...)` で `task_process_status` に変換される。

---

## 7. STATE_DB / APPL_DB 書き込み

QUEUE テーブル処理において:
- STATE_DB 書き込み: **なし** (queue 設定は STATUS_DB にも反映されない)
- APPL_DB 書き込み: **なし** (CONFIG_DB → SAI の直接経路)

---

## 8. Producer/Consumer 対応まとめ

```
CONFIG_DB[QUEUE|*]
  ↓ SubscriberStateTable
  ↓ PSUBSCRIBE __keyspace@config_db_id__:QUEUE|*
orchagent (orchdaemon.cpp main loop)
  ↓ select() (1000 ms タイムアウト)
  ↓ Consumer::drain()
  ↓ QosOrch::doTask(Consumer&) — allPortsReady() チェック後
  ↓ handleQueueTable()
    ↓ applySchedulerToQueueSchedulerGroup()
    ↓   → sai_scheduler_group_api (SAI_SCHEDULER_GROUP_ATTR_SCHEDULER_PROFILE_ID)
    ↓ applyWredProfileToQueue()
    ↓   → sai_queue_api (SAI_QUEUE_ATTR_WRED_PROFILE_ID)
ASIC (ASIC_DB 経由、sairedis が仲介)

NotificationConsumer: なし (QUEUE テーブルでは使用しない)
ProducerStateTable: なし (APPL_DB への中継なし)
```
