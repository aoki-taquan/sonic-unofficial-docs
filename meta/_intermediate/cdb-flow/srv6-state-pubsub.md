# SRv6 カウンタ状態 (COUNTERS_DB) — Phase G 通信メカニズム スキャンノート

対象テーブル: `COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>` (COUNTERS_DB)
Producer: `Srv6Orch` (orchagent), `syncd` FlexCounter
スキャン範囲: `orchdaemon.cpp:312-324`, `orch.cpp:1186-1196`, `flexcounterorch.cpp:64,96,337-339`, `srv6orch.cpp:98-113,261-283,286-312`

---

## 検出した通信メカニズム

### 1. APPL_DB SRV6_MY_SID_TABLE / SRV6_SID_LIST_TABLE → Srv6Orch: ConsumerStateTable

`orchdaemon.cpp:312-324` で `Srv6Orch` は以下の `TableConnector` を受け取る:

```cpp
TableConnector srv6_sid_list_table(m_applDb, APP_SRV6_SID_LIST_TABLE_NAME);
TableConnector srv6_my_sid_table(m_applDb, APP_SRV6_MY_SID_TABLE_NAME);
TableConnector srv6_pic_context_table(m_applDb, APP_PIC_CONTEXT_TABLE_NAME);
TableConnector srv6_my_sid_cfg_table(m_configDb, CFG_SRV6_MY_SID_TABLE_NAME);
```

`Orch::addConsumer()` (`orch.cpp:1186-1195`) は DB の種類で通知方式を切り替える:
- APPL_DB (`m_applDb`, db_id=0): **`ConsumerStateTable`** — Redis LPOP ベースの SWSS ProducerStateTable 対応
- CONFIG_DB (`m_configDb`, db_id=4): **`SubscriberStateTable`** — keyspace notification (PSUBSCRIBE) ベース

| テーブル | DB | 方式 | チャンネル / パターン |
|---------|-----|------|-------------------|
| `SRV6_MY_SID_TABLE` | APPL_DB | `ConsumerStateTable` | `SRV6_MY_SID_TABLE_CHANNEL@0` |
| `SRV6_SID_LIST_TABLE` | APPL_DB | `ConsumerStateTable` | `SRV6_SID_LIST_TABLE_CHANNEL@0` |
| `PIC_CONTEXT_TABLE` | APPL_DB | `ConsumerStateTable` | `PIC_CONTEXT_TABLE_CHANNEL@0` |
| `SRV6_MY_SIDS` | CONFIG_DB | `SubscriberStateTable` | `__keyspace@4__:SRV6_MY_SIDS\|*` |

### 2. CONFIG_DB SRV6_MY_SIDS → Srv6Orch: SubscriberStateTable

`SRV6_MY_SIDS` は CONFIG_DB に属するため `SubscriberStateTable` 経路が選択される。
`SubscriberStateTable` は内部で Redis keyspace notification を PSUBSCRIBE し、キーの変更（`hset` / `del`）を検出する。
通知ペイロードには操作名のみが含まれ、フィールド値は通知後に `HGETALL` で取得される。
起動時スナップショット: `SubscriberStateTable` ctor は PSUBSCRIBE 直後に既存全エントリを `SET_COMMAND` として buffer に積む。

### 3. FLEX_COUNTER_TABLE|SRV6 enable/disable → Srv6Orch: コールバック経由

`FlexCounterOrch::doTask()` (`flexcounterorch.cpp:337-339`) は `FLEX_COUNTER_TABLE` の `SRV6_KEY = "SRV6"` を受け取ると直接 `gSrv6Orch->setCountersState()` を呼ぶ:

```cpp
if (gSrv6Orch && (key == SRV6_KEY))
    gSrv6Orch->setCountersState((value == "enable"));
```

`FlexCounterOrch` 自身は `FLEX_COUNTER_TABLE` を `SubscriberStateTable` で購読する。
`Srv6Orch` は `FLEX_COUNTER_TABLE` を直接購読しない（コールバック受動型）。

### 4. Srv6Orch → FLEX_COUNTER_DB → syncd: SelectableTimer 経由

`addMySidCounter()` は OID を `m_pending_counters` に積み、`m_counter_update_timer` (1 秒) を start する。
`doTask(SelectableTimer)` (`srv6orch.cpp:286-312`) は 1 秒後に起動し `m_counter_manager.setCounterIdList()` で
`FLEX_COUNTER_DB` の `SRV6_STAT_COUNTER:<oid>` に counter stats ID リストを書き込む。

syncd の FlexCounter は `FLEX_COUNTER_DB` を `SubscriberStateTable` で購読し、
`SRV6_STAT_COUNTER` グループの新規 OID 登録を検出すると `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` ms
周期で SAI からポーリングを開始し、`COUNTERS_DB` の `COUNTERS|<oid>` に `HSET` で書き込む。

### 5. syncd → COUNTERS_DB: SAI ポーリング (非 Redis pub/sub)

`COUNTERS_DB COUNTERS|<oid>` は Redis pub/sub ではなく syncd が SAI polling 結果を `HSET` で直接書き込む。
`COUNTERS_SRV6_NAME_MAP` も `Srv6Orch` が `Table::set()` / `Table::hdel()` で直接書き込む（ProducerStateTable ではない）。

---

## 通信メカニズムサマリ

| 区間 | 方式 | チャンネル / パターン |
|------|------|--------------------|
| fpmsyncd → APPL_DB `SRV6_MY_SID_TABLE` | `ProducerStateTable`（SET/DEL） | `SRV6_MY_SID_TABLE_CHANNEL@0` |
| APPL_DB → Srv6Orch | `ConsumerStateTable` (LPOP) | `SRV6_MY_SID_TABLE_CHANNEL@0` |
| CONFIG_DB `SRV6_MY_SIDS` → Srv6Orch | `SubscriberStateTable` (PSUBSCRIBE) | `__keyspace@4__:SRV6_MY_SIDS\|*` |
| `FLEX_COUNTER_TABLE\|SRV6` → Srv6Orch | FlexCounterOrch コールバック (`setCountersState`) | — |
| Srv6Orch → FLEX_COUNTER_DB | `FlexCounterManager::setCounterIdList` (1 秒タイマー後) | `SRV6_STAT_COUNTER:<oid>` |
| FLEX_COUNTER_DB → syncd | `SubscriberStateTable` (syncd 内部) | — |
| syncd → COUNTERS_DB | SAI ポーリング (`HSET`) | `COUNTERS\|<oid>` |
