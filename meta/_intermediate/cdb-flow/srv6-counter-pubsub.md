# FLEX_COUNTER_TABLE SRV6 — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/srv6-counter.md`
対象 CONFIG_DB テーブル: `FLEX_COUNTER_TABLE|SRV6`

調査日: 2026-05-17
Evidence:
- `sonic-swss/orchagent/flexcounterorch.cpp:39,64,96,102-138,145-410,337-340`
- `sonic-swss/orchagent/srv6orch.cpp:98-113,251-283,286-313`
- `sonic-swss/orchagent/orchdaemon.cpp:312-325,620-628`
- `sonic-swss/orchagent/orch.cpp:1186-1196`
- `sonic-swss-common/common/subscriberstatetable.cpp:17-43`

---

## 概要

`FLEX_COUNTER_TABLE|SRV6` (CONFIG_DB) は **orchagent 内の `FlexCounterOrch`** が単一スレッドで消費する。変更検出は **Redis keyspace notification (PSUBSCRIBE)** 経由の `SubscriberStateTable` 経路。`ConsumerStateTable` / `NotificationConsumer` は CONFIG_DB 側では**使用しない**。

| 購読者 | 購読方式 | Redis primitive | 対象テーブル |
|---|---|---|---|
| orchagent `FlexCounterOrch` (CONFIG_DB) | `SubscriberStateTable` | PSUBSCRIBE keyspace | `FLEX_COUNTER_TABLE`, `DEVICE_METADATA` |
| orchagent `Srv6Orch` (内部 1 秒タイマー) | `SelectableTimer` | - | `SRV6_FLEX_COUNTER_UPDATE_TIMER` (pending_counters 処理) |
| syncd `FlexCounter` (FLEX_COUNTER_DB) | `ConsumerTable` | LPOP+PUBLISH | `FLEX_COUNTER_GROUP_TABLE` (DB 5) ← 別資料スコープ |

---

## 購読者 G-1: orchagent `FlexCounterOrch`

### 生成 (orchdaemon.cpp:620-628)

```
vector<string> flex_counter_tables = {
    CFG_FLEX_COUNTER_TABLE_NAME,         // "FLEX_COUNTER_TABLE"
    CFG_DEVICE_METADATA_TABLE_NAME       // "DEVICE_METADATA"
};
auto* flexCounterOrch = new FlexCounterOrch(m_configDb, flex_counter_tables);
```

`m_configDb` は CONFIG_DB。`Orch::Orch(db, tableNames)` 経由で各 tableName に対して `Orch::addConsumer()` が呼ばれる。

### Orch::addConsumer の分岐 (orch.cpp:1186-1196)

```
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB
        || db->getDbId() == STATE_DB
        || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(
            new SubscriberStateTable(db, tableName, DEFAULT_POP_BATCH_SIZE, pri),
            this, tableName));
    }
    ...
}
```

CONFIG_DB なので **SubscriberStateTable 経路**。

### PSUBSCRIBE パターン (subscriberstatetable.cpp:20-24)

```cpp
m_keyspace = "__keyspace@" + to_string(db->getDbId()) + "__:" + tableName + "|*";
psubscribe(m_db, m_keyspace);
```

実際のパターン:

| テーブル | PSUBSCRIBE パターン |
|---|---|
| `FLEX_COUNTER_TABLE` | `__keyspace@{config_db_id}__:FLEX_COUNTER_TABLE|*` |
| `DEVICE_METADATA` | `__keyspace@{config_db_id}__:DEVICE_METADATA|*` |

`FLEX_COUNTER_TABLE|SRV6` への HSET が走ると、Redis が `channel = __keyspace@{config_db_id}__:FLEX_COUNTER_TABLE|SRV6`、`message = "hset"` を自動 publish する。

### 起動時スナップショット

`SubscriberStateTable` ctor (subscriberstatetable.cpp:26-42) は PSUBSCRIBE 直後に `m_table.getKeys()` で既存全エントリを HGETALL し `SET_COMMAND` として `m_buffer` に積む。つまり orchagent 起動時に `FLEX_COUNTER_TABLE|SRV6` が既に CONFIG_DB に存在すれば、PSUBSCRIBE 待ち不要で即座に `doTask` に流れる。

### SubscriberStateTable.pops() の動作

```
keyspace event 到着:
  channel = "__keyspace@{config_db_id}__:FLEX_COUNTER_TABLE|SRV6"
  message = "hset"
  → key = "SRV6"
  → op = SET_COMMAND
  → fvs = HGETALL("FLEX_COUNTER_TABLE|SRV6")  ← 別途取得
```

フィールド値は通知ペイロードでなく **HGETALL で別途取得**する。通知 → HGETALL の間に更新があれば最新値が読まれる（lost-update 耐性あり）。

### Warm restart 遅延

`FlexCounterOrch` ctor (flexcounterorch.cpp:127-137) は warm start 時のみ 60 秒の `SelectableTimer`(`FLEX_COUNTER_DELAY_SEC = 60`) を起動。`m_delayTimerExpired` が false の間、`doTask(Consumer&)` は即 return し `FLEX_COUNTER_TABLE|SRV6` の変更を処理しない (flexcounterorch.cpp:156-159)。コールド起動時は即時有効。

### doTask の SRV6 ブランチ (flexcounterorch.cpp:337-340)

```
if (gSrv6Orch && (key == SRV6_KEY))
{
    gSrv6Orch->setCountersState((value == "enable"));
}
```

`gSrv6Orch` が null の場合（orchdaemon 初期化未完了等）は silent drop。`SRV6_KEY = "SRV6"` (flexcounterorch.cpp:64)。

`FLEX_COUNTER_STATUS` フィールドの処理後、`setFlexCounterGroupOperation(SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP, value)` が呼ばれ FLEX_COUNTER_DB に enable/disable が伝達される。`POLL_INTERVAL` は `setFlexCounterGroupPollInterval(SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP, value)` 経由 (flexcounterorch.cpp:202)。

---

## 購読者 G-2: orchagent `Srv6Orch` 内部タイマー

### SRV6_FLEX_COUNTER_UPDATE_TIMER (srv6orch.cpp:26, 138-140)

```cpp
#define SRV6_FLEX_COUNTER_UPDATE_TIMER 1  // 秒
m_counter_update_timer = new SelectableTimer(timespec { .tv_sec = SRV6_FLEX_COUNTER_UPDATE_TIMER , .tv_nsec = 0 });
auto et = new ExecutableTimer(m_counter_update_timer, this, "SRV6_FLEX_COUNTER_UPDATE_TIMER");
Orch::addExecutor(et);
```

このタイマーは Redis PUBSUB ではなく `timerfd_create` ベースの `SelectableTimer`。`m_pending_counters` に積まれた SAI カウンタ OID を毎秒処理し、ASIC_DB `VIDTORID` の VID→RID 解決が確認できた OID を `m_counter_manager.setCounterIdList()` 経由で FLEX_COUNTER_DB に登録する (srv6orch.cpp:291-313)。`m_pending_counters` が空になるとタイマーが自動停止 (srv6orch.cpp:309-311)。

---

## 書き込み元 (Publisher 側)

CONFIG_DB への書き込みは **直接 Redis HSET**（`ConfigDBConnector`）で行われ、`ProducerStateTable` は通らない:

| 書き込み元 | 経路 |
|---|---|
| `counterpoll srv6 {enable\|disable\|interval}` | `counterpoll/main.py` → ConfigDBConnector.mod_entry → HSET |
| `config_db.json` 初期投入 | sonic-cfggen による一括 HSET |

HSET 完了で Redis が自動的に keyspace 通知を publish → orchagent `SubscriberStateTable` が拾う。

---

## FLEX_COUNTER_DB への波及

orchagent → syncd への伝達は CONFIG_DB ではなく **FLEX_COUNTER_DB** 経由:

```
setFlexCounterGroupOperation(SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP, "enable"):
  gTraditionalFlexCounter=true  → gFlexCounterGroupTable->set(group, {STATUS:enable, POLL_INTERVAL:...})
                                    (ProducerTable → LPOP+PUBLISH → syncd ConsumerTable)
  gTraditionalFlexCounter=false → notifySyncdCounterOperation() → SAI redis switch attr 直書き
```

`SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` は `flexcounterorch.cpp:96` の `flexCounterGroupMap` で `SRV6_KEY ("SRV6")` に紐付く。

---

## フィールド × 購読者 マトリクス

| フィールド | FlexCounterOrch | Srv6Orch (タイマー) |
|---|:---:|:---:|
| `FLEX_COUNTER_STATUS` | 解釈 → `setCountersState()` + `setFlexCounterGroupOperation()` | - |
| `POLL_INTERVAL` | 解釈 → `setFlexCounterGroupPollInterval()` | - |
| `FLEX_COUNTER_DELAY_STATUS` | 無視（Srv6Orch 側で未参照） | - |
| MySID 追加時の pending counter | - | 1 秒ごとに FLEX_COUNTER_DB へ登録 |

---

## データフロー図

```
admin (counterpoll srv6 enable)
  ↓ ConfigDBConnector.mod_entry()
CONFIG_DB[FLEX_COUNTER_TABLE|SRV6]
  ↓ HSET + keyspace PUBLISH
  ↓   channel: __keyspace@{config_db_id}__:FLEX_COUNTER_TABLE|SRV6
  ↓   message: "hset"
orchagent select() ループ
  ↓ SubscriberStateTable.pops() → HGETALL "FLEX_COUNTER_TABLE|SRV6"
FlexCounterOrch::doTask(Consumer&)
  ├─ flexCounterGroupMap["SRV6"] = SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP
  ├─ gSrv6Orch->setCountersState(true)
  │    └─ (全 MY_SID に) addMySidCounter() → COUNTERS_DB COUNTERS_SRV6_NAME_MAP
  │    └─ setMySidEntryCounter() → SAI set_my_sid_entry_attribute
  │    └─ m_pending_counters に積む → タイマーで FLEX_COUNTER_DB へ登録
  └─ setFlexCounterGroupOperation(SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP, "enable")
       └─ ProducerTable(gFlexCounterGroupTable).set() / SAI redis switch attr
FLEX_COUNTER_DB[FLEX_COUNTER_GROUP_TABLE|SRV6_STAT_COUNTER]
  ↓ syncd FlexCounter スレッドが受信
syncd (FlexCounter)
  ↓ 10 秒間隔で SAI get_counter_stats(SAI_COUNTER_STAT_PACKETS/BYTES)
COUNTERS_DB[COUNTERS:<oid>]   ← HSET

MySID 追加パス (FLEX_COUNTER_STATUS=enable 後に SRV6_MY_SIDS に SET):
  Srv6Orch::doTask(Consumer) → addMySidCounter() → m_pending_counters
    ↓ SRV6_FLEX_COUNTER_UPDATE_TIMER (1 秒間隔)
  Srv6Orch::doTask(SelectableTimer) → m_counter_manager.setCounterIdList()
    ↓ FLEX_COUNTER_DB SRV6_STAT_COUNTER:<oid>

NotificationConsumer: なし
ConsumerStateTable (CONFIG_DB 側): なし
TTL / expire: なし
```

---

## 競合 / レース

| 競合 | 影響 | 対策 |
|---|---|---|
| keyspace 通知 → HGETALL の間に更新 | 最新値が読まれる (lost-update なし) | 影響なし (SubscriberStateTable 仕様) |
| Warm restart 60 秒中の `enable` 書込み | `m_toSync` に蓄積されタイマー満了後に処理 | 設計通り |
| `gSrv6Orch == null` 時 | silent drop | orchdaemon 初期化順序が保証済み |
| SAI 非対応プラットフォームで enable | `setCountersState` が early-return | `m_mysid_counters_supported` ガード (srv6orch.cpp:255-259) |
| MySID 追加 → 1 秒未満で enable | タイマーが非同期に FLEX_COUNTER_DB 登録 | pending_counters キューで順序保証 |

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/orchagent/orchdaemon.cpp` | 620-628 | `FlexCounterOrch` の生成 (`FLEX_COUNTER_TABLE`, `DEVICE_METADATA`) |
| `sonic-swss/orchagent/orchdaemon.cpp` | 312-325 | `Srv6Orch` の生成とテーブル購読設定 |
| `sonic-swss/orchagent/orch.cpp` | 1186-1196 | `Orch::addConsumer` の DB 種別分岐 (CONFIG_DB → SubscriberStateTable) |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-43 | ctor — PSUBSCRIBE + 初回 getKeys スナップショット |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 44 | `FLEX_COUNTER_DELAY_SEC = 60` |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 64, 96 | `SRV6_KEY = "SRV6"`, flexCounterGroupMap エントリ |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 102-138 | ctor — warm restart timer 設定 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 145-167 | `doTask` — delay/allPortsReady ガード |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 337-340 | `SRV6_KEY` ブランチ → `gSrv6Orch->setCountersState()` |
| `sonic-swss/orchagent/srv6orch.cpp` | 26-27 | `SRV6_FLEX_COUNTER_UPDATE_TIMER = 1`, `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` |
| `sonic-swss/orchagent/srv6orch.cpp` | 138-141 | 1 秒タイマー初期化 |
| `sonic-swss/orchagent/srv6orch.cpp` | 251-283 | `setCountersState()` — enable/disable ループ |
| `sonic-swss/orchagent/srv6orch.cpp` | 286-313 | `doTask(SelectableTimer&)` — pending_counters → FLEX_COUNTER_DB |
