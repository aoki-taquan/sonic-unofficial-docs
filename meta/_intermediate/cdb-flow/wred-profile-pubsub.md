# WRED_PROFILE テーブル — 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-16
対象ソース:
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`

---

## 1. Producer/Consumer ペア

### CONFIG_DB → orchagent QosOrch (SubscriberStateTable)

| 項目 | 値 |
|------|----|
| 購読方式 | `Orch(db, tableNames)` 基底クラスの `addConsumer()` 経由の `SubscriberStateTable` |
| keyspace パターン | `__keyspace@{config_db_id}__:WRED_PROFILE\|*` |
| 購読テーブル | `CFG_WRED_PROFILE_TABLE_NAME` (`"WRED_PROFILE"`) |
| Consumer クラス | `Consumer` (wraps `SubscriberStateTable`) — CONFIG_DB は `SubscriberStateTable` 固定 (`orch.cpp:1188-1190`) |
| ハンドラ登録 | `QosOrch::initTableHandlers()` で `CFG_WRED_PROFILE_TABLE_NAME → &QosOrch::handleWredProfileTable` を `m_qos_handler_map` に登録 (`qosorch.cpp:1336`) |
| 優先度 | `default_orch_pri` (= 0) |

`QosOrch` のコンストラクタは `Orch(db, tableNames)` を呼び出す。`tableNames` には `CFG_WRED_PROFILE_TABLE_NAME` を含む 15 テーブルが列挙される (`orchdaemon.cpp:367-383`)。

`Orch::addConsumer()` は CONFIG_DB を検出すると `SubscriberStateTable` を生成し `Consumer` でラップして `m_consumerMap` に追加する。

### APPL_DB 書き込みなし

WRED_PROFILE テーブルの処理は orchagent 内で完結する。`QosOrch` は CONFIG_DB の WRED_PROFILE エントリを読んで直接 SAI API を呼び出す。APPL_DB への中継は行わない。

---

## 2. keyspace notification (SubscriberStateTable)

`SubscriberStateTable` は CONFIG_DB の keyspace notification を使う。

```
PSUBSCRIBE __keyspace@{config_db_id}__:WRED_PROFILE|*
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
// 1. PORT_QOS_MAP と QUEUE 以外のテーブルを先に処理 (wred_profile, scheduler 等の参照先)
for (const auto &it : m_consumerMap) {
    if (exec == port_qos_map_cfg_exec || exec == queue_exec) continue;
    exec->drain();
}
// 2. PORT_QOS_MAP を処理
port_qos_map_cfg_exec->drain();
// 3. 最後に QUEUE を処理 (参照先が揃った状態で実行)
queue_exec->drain();
```

**意図**: WRED_PROFILE / SCHEDULER が先に解決されてから QUEUE を処理することで `task_need_retry` の発生を最小化する。

### doTask ガード

```cpp
void QosOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return;  // 全ポート初期化待ち
    // ...
}
```

全ポートの初期化完了 (`PortInitDone`) まで WRED_PROFILE の処理を保留する。

---

## 4. handleWredProfileTable の動作フロー

```
Consumer::drain()
  → QosOrch::doTask(Consumer&)
    → m_qos_handler_map[CFG_WRED_PROFILE_TABLE_NAME](consumer, tuple)
      → QosOrch::handleWredProfileTable(consumer, tuple)   # qosorch.cpp:877
        → WredMapHandler wred_handler
        → wred_handler.processWorkItem(consumer, tuple)
          SET:
            → convertFieldValuesToAttributes()
              - ecn フィールド: ecn_map.at(value) → SAI_WRED_ATTR_ECN_MARK_MODE
              - wred_*_enable: convertBool() → SAI_WRED_ATTR_{GREEN/YELLOW/RED}_ENABLE
              - *_threshold: bytes 値 → SAI_WRED_ATTR_*_{MIN/MAX}_THRESHOLD
              - *_drop_probability: uint64 → SAI_WRED_ATTR_*_DROP_PROBABILITY
            → addQosItem():
              - SAI_WRED_ATTR_WEIGHT = 0 を先頭に注入 (無条件)
              - sai_wred_api->create_wred()
          DEL:
            → removeQosItem():
              - sai_wred_api->remove_wred()
```

| task_status | 条件 | 次の動作 |
|-------------|------|----------|
| `task_success` | SAI 呼び出し成功 | `m_toSync` から削除 |
| `task_invalid_entry` | key 不正 | `m_toSync` から削除 (silent drop) |
| `task_failed` | SAI エラー | `m_toSync` から削除, `return` (即終了) |
| `task_need_retry` | (現状 WRED_PROFILE 自体は retry しない) | `m_toSync` に残留 |

WRED_PROFILE 自体が未解決参照で待機することは通常なし（他テーブルから参照される側）。ただし QUEUE が WRED_PROFILE を参照する場合に QUEUE 側が `task_need_retry` を発行する。

---

## 5. SAI 書き込み経路

```
WredMapHandler::addQosItem()
  → sai_wred_api->create_wred(
        &sai_object, gSwitchId,
        attrs: [SAI_WRED_ATTR_WEIGHT=0,
                SAI_WRED_ATTR_{GREEN/YELLOW/RED}_ENABLE,
                SAI_WRED_ATTR_{GREEN/YELLOW/RED}_{MIN/MAX}_THRESHOLD,
                SAI_WRED_ATTR_{GREEN/YELLOW/RED}_DROP_PROBABILITY,
                SAI_WRED_ATTR_ECN_MARK_MODE])

WredMapHandler::modifyQosItem()
  → sai_wred_api->set_wred_attribute(sai_object, &attr)  # runtime 更新

WredMapHandler::removeQosItem()
  → sai_wred_api->remove_wred(sai_object)

# QUEUE への bind は QosOrch::applyWredProfileToQueue() が担当
QosOrch::applyWredProfileToQueue()
  → sai_queue_api->set_queue_attribute(
        SAI_QUEUE_ATTR_WRED_PROFILE_ID, sai_wred_profile)
```

SAI 呼び出し結果は `handleSaiStatus()` で `task_process_status` に変換される。

---

## 6. STATE_DB / APPL_DB 書き込み

WRED_PROFILE テーブル処理において:
- STATE_DB 書き込み: **なし**
- APPL_DB 書き込み: **なし** (CONFIG_DB → SAI の直接経路)

---

## 7. Consumer 登録コード証跡

`orchdaemon.cpp:367-384`:
```cpp
vector<string> qos_tables = {
    ...
    CFG_WRED_PROFILE_TABLE_NAME,   // L375: "WRED_PROFILE"
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);  // L384
```

`qosorch.cpp:1336`:
```cpp
m_qos_handler_map.insert(
    qos_handler_pair(CFG_WRED_PROFILE_TABLE_NAME,
                     &QosOrch::handleWredProfileTable));
```

`qosorch.cpp:877-881`:
```cpp
task_process_status QosOrch::handleWredProfileTable(
    Consumer& consumer, KeyOpFieldsValuesTuple &tuple)
{
    WredMapHandler wred_handler;
    return wred_handler.processWorkItem(consumer, tuple);
}
```

---

## 8. Producer/Consumer 対応まとめ

```
CONFIG_DB[WRED_PROFILE|*]
  ↓ SubscriberStateTable
  ↓ PSUBSCRIBE __keyspace@config_db_id__:WRED_PROFILE|*
orchagent (orchdaemon.cpp main loop)
  ↓ select() (1000 ms タイムアウト)
  ↓ Consumer::drain()
  ↓ QosOrch::doTask(Consumer&) — allPortsReady() チェック後
  ↓ handleWredProfileTable()
    ↓ WredMapHandler::convertFieldValuesToAttributes()
    ↓ WredMapHandler::addQosItem()
    ↓   → sai_wred_api->create_wred() / set_wred_attribute()
    ↓ (QUEUE bind は handleQueueTable() → applyWredProfileToQueue())
    ↓   → sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_WRED_PROFILE_ID)
ASIC (ASIC_DB 経由、sairedis が仲介)

NotificationConsumer: なし (WRED_PROFILE テーブルでは使用しない)
ProducerStateTable: なし (APPL_DB への中継なし)
```

## 9. 参考行番号

- `sonic-swss/orchagent/orchdaemon.cpp`
  - 375: `CFG_WRED_PROFILE_TABLE_NAME` を qos_tables に追加
  - 384: `gQosOrch = new QosOrch(m_configDb, qos_tables)`
  - 500: `m_orchList` への登録
- `sonic-swss/orchagent/qosorch.cpp`
  - 877-881: `QosOrch::handleWredProfileTable()`
  - 1313-1318: `QosOrch::QosOrch()` コンストラクタ
  - 1336: `CFG_WRED_PROFILE_TABLE_NAME` ハンドラ登録
  - 2231-2252: `QosOrch::doTask()` 実行順序制御
  - 585-762: `WredMapHandler::convertFieldValuesToAttributes()`
  - 784-860: `WredMapHandler::addQosItem()`
  - 768-782: `WredMapHandler::modifyQosItem()`
  - 864-874: `WredMapHandler::removeQosItem()`
  - 855: `sai_wred_api->create_wred()`
