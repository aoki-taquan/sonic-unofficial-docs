# app-counter — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/app-counter.md`
対象 CONFIG_DB テーブル:
- `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP`
- `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE`
- `FLOW_COUNTER_ROUTE_PATTERN`

調査日: 2026-05-15
Evidence:
- `sonic-swss/orchagent/flexcounterorch.cpp:70-100,102-138,145-410`
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp:21-26,28-48,55-97,99-`
- `sonic-swss/orchagent/copporch.cpp:189,198`
- `sonic-swss/orchagent/orchdaemon.cpp:251-254,620-628,1308`
- `sonic-swss/orchagent/orch.cpp:1186-1196`
- `sonic-swss/orchagent/saihelper.cpp:117-118,324-325,868-885,918-962`
- `sonic-swss-common/common/subscriberstatetable.cpp:17-40,95-`

---

## 概要

`FLEX_COUNTER_TABLE` (CONFIG_DB) と `FLOW_COUNTER_ROUTE_PATTERN` (CONFIG_DB) は **orchagent の単一プロセス** で消費される。両方とも `Orch` 基底クラス経由の **SubscriberStateTable** すなわち **Redis keyspace PSUBSCRIBE** によって変更通知が拾われる。書き込み側 (FLEX_COUNTER_DB への per-OID エントリ生成) は **ProducerTable** = 直接 Redis HSET ベース。

| 購読者 | 購読方式 | Redis primitive | 対象テーブル |
|---|---|---|---|
| orchagent `FlexCounterOrch` (CONFIG_DB) | `SubscriberStateTable` | PSUBSCRIBE keyspace | `FLEX_COUNTER_TABLE`, `DEVICE_METADATA` |
| orchagent `FlowCounterRouteOrch` (CONFIG_DB) | `SubscriberStateTable` | PSUBSCRIBE keyspace | `FLOW_COUNTER_ROUTE_PATTERN` |
| orchagent `FlowCounterRouteOrch` (内部 1s タイマ) | `SelectableTimer` | - | (FLEX_COUNTER_UPD_TIMER) |
| syncd `FlexCounter` (FLEX_COUNTER_DB) | `ConsumerTable` (経路は別資料) | LPOP+PUBLISH | `FLEX_COUNTER_TABLE`, `FLEX_COUNTER_GROUP_TABLE` (DB 5) |

`ConsumerStateTable` / `NotificationConsumer` は CONFIG_DB 側で **不使用**。書き込み元 (CLI `config flowcnt-route`, `counterpoll`, sonic-cfggen) は CONFIG_DB に対し直接 `HSET` を発行するだけ。

---

## 購読者 G-1: orchagent `FlexCounterOrch`

### 生成 (orchdaemon.cpp:620-628)

```
vector<string> flex_counter_tables = {
    CFG_FLEX_COUNTER_TABLE_NAME,         // "FLEX_COUNTER_TABLE"
    CFG_DEVICE_METADATA_TABLE_NAME       // "DEVICE_METADATA"
};
new FlexCounterOrch(m_configDb, flex_counter_tables);
```

`m_configDb` は CONFIG_DB (dbId=4) DBConnector。`Orch::Orch(db, tableNames)` 経由で各 tableName に対して `Orch::addConsumer()` が呼ばれる:

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
    else
    {
        addExecutor(new Consumer(
            new ConsumerStateTable(db, tableName, gBatchSize, pri),
            this, tableName));
    }
}
```

CONFIG_DB なので **SubscriberStateTable 経路**。

### PSUBSCRIBE パターン (subscriberstatetable.cpp:17-24)

```
m_keyspace = "__keyspace@" + dbId + "__:" + tableName + "|*";
psubscribe(m_db, m_keyspace);
```

実際のパターン:

| テーブル | PSUBSCRIBE パターン |
|---|---|
| `FLEX_COUNTER_TABLE` | `__keyspace@4__:FLEX_COUNTER_TABLE|*` |
| `DEVICE_METADATA` | `__keyspace@4__:DEVICE_METADATA|*` |
| `FLOW_COUNTER_ROUTE_PATTERN` | `__keyspace@4__:FLOW_COUNTER_ROUTE_PATTERN|*` |

(dbId=4 は CONFIG_DB)

### 起動時スナップショット

`SubscriberStateTable` ctor は psubscribe 直後に `m_table.getKeys()` で既存全エントリを HGETALL し、`SET_COMMAND` として `m_buffer` に積む (subscriberstatetable.cpp:26-44)。つまり orchagent 起動時に存在する `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` 等のエントリは **PSUBSCRIBE 待ちなしで即時 doTask に流れる**。

### Warm restart 遅延

`FlexCounterOrch` ctor は warm start 時のみ 60 秒の `SelectableTimer` を起動 (`FLEX_COUNTER_DELAY_SEC = 60`, flexcounterorch.cpp:44, 127-133)。`m_delayTimerExpired` が false の間、`doTask(Consumer&)` は即 return し、CONFIG_DB 変更を受信しても処理しない (flexcounterorch.cpp:156-159)。コールド起動時はすぐに有効。

### doTask の処理 (flexcounterorch.cpp:145-410)

```
doTask(Consumer& consumer)
  └─ consumer.getTableName() == "DEVICE_METADATA" → handleDeviceMetadataTable() → return
  └─ !m_delayTimerExpired → return                ← warm restart 中
  └─ !gPortsOrch->allPortsReady()    → return    ← Port 未準備
  └─ !gFabricPortsOrch->allPortsReady() → return ← fabric 未準備
  for each (key, op, fvs) in consumer.m_toSync:
    if !flexCounterGroupMap.count(key): warn + erase + continue
    if op == SET_COMMAND:
      for (field, value) in fvs:
        if field == POLL_INTERVAL_FIELD:
          setFlexCounterGroupPollInterval(flexCounterGroupMap[key], value)
        elif field == FLEX_COUNTER_STATUS_FIELD:
          if key == FLOW_CNT_TRAP_KEY:
            value=="enable" → gCoppOrch->generateHostIfTrapCounterIdList()
            value=="disable" → gCoppOrch->clearHostIfTrapCounterIdList()
          if key == FLOW_CNT_ROUTE_KEY && getRouteFlowCounterSupported():
            value=="enable" → gFlowCounterRouteOrch->generateRouteFlowStats()
            value=="disable" → gFlowCounterRouteOrch->clearRouteFlowStats()
          setFlexCounterGroupOperation(flexCounterGroupMap[key], value)
    erase iterator
```

`flexCounterGroupMap` は string → group constant のテーブル (flexcounterorch.cpp:65-99):

| CONFIG_DB key | 内部 group constant |
|---|---|
| `FLOW_CNT_TRAP` (FLOW_CNT_TRAP_KEY) | `HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP` |
| `FLOW_CNT_ROUTE` (FLOW_CNT_ROUTE_KEY) | `ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP` |

未知 key (例: typo) は warn ログのみで黙って捨てられる (flexcounterorch.cpp:183-188)。

### SubscriberStateTable.pops() (subscriberstatetable.cpp:95-)

```
keyspace event 到着:
  pattern = "__keyspace@4__:FLEX_COUNTER_TABLE|*"
  channel = redis op name  ("hset" / "del" / "expired" 等)
  message = "FLEX_COUNTER_TABLE|FLOW_CNT_TRAP" (フルキー)
  key     = "FLOW_CNT_TRAP"
  if op == "del":
    op = DEL_COMMAND, fvs = {}
  else:
    op = SET_COMMAND
    fvs = HGETALL("FLEX_COUNTER_TABLE|FLOW_CNT_TRAP")
```

CONFIG_DB → keyspace 通知 → orchagent 内 `Select` がイベント検出 → `SubscriberStateTable::pops()` が HGETALL → `Consumer::execute()` → `FlexCounterOrch::doTask()`。フィールド値は通知ペイロードでなく **HGETALL で別途取得**するため、通知→HGETALL の間に追加更新があれば最新値が読まれる (lost-update 耐性あり)。

---

## 購読者 G-2: orchagent `FlowCounterRouteOrch`

### 生成 (orchdaemon.cpp:251-254)

```
vector<string> route_pattern_tables = {
    CFG_FLOW_COUNTER_ROUTE_PATTERN_TABLE_NAME    // "FLOW_COUNTER_ROUTE_PATTERN"
};
gFlowCounterRouteOrch = new FlowCounterRouteOrch(m_configDb, route_pattern_tables);
```

`Orch::addConsumer` 経由で同じく **SubscriberStateTable**。PSUBSCRIBE パターン: `__keyspace@4__:FLOW_COUNTER_ROUTE_PATTERN|*`。

### 内部 1 秒タイマー (flowcounterrouteorch.cpp:21,43-46)

```
#define FLEX_COUNTER_UPD_INTERVAL 1
if (mRouteFlowCounterSupported) {
    auto intervT = timespec{ .tv_sec = 1, .tv_nsec = 0 };
    mFlexCounterUpdTimer = new SelectableTimer(intervT);
    Orch::addExecutor(new ExecutableTimer(mFlexCounterUpdTimer, this, "FLEX_COUNTER_UPD_TIMER"));
}
```

このタイマーは Redis PUBSUB ではない (`SelectableTimer` は `timerfd_create` ベース)。orchagent 内の同一 `Select` ループに addExecutor され、毎秒 `doTask(SelectableTimer&)` を起動して `mPendingAddToFlexCntr` キューを処理し、SAI route entry → VID → RID 解決ができた route を `mRouteFlowCounterMgr.setCounterIdList()` 経由で FLEX_COUNTER_DB に書き込む。SAI 未対応時 (`mRouteFlowCounterSupported = false`) はそもそも生成されない。

### doTask(Consumer&) (flowcounterrouteorch.cpp:55-97)

```
if (!gRouteOrch || !mRouteFlowCounterSupported) return;
for each (key, op, fvs) in consumer.m_toSync:
  if op == SET_COMMAND:
    maxMatchCount = ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT   // 30
    for (field, value) in fvs:
      if field == "max_match_count":
        maxMatchCount = stoul(value); if 0 → 30 (warn)
    addRoutePattern(key, maxMatchCount)
  elif op == DEL_COMMAND:
    removeRoutePattern(key)
```

key は `<prefix>` または `<vrf>|<prefix>` (テーブル名分離子 `|` の後ろ全部)。

---

## 書き込み元 (Publisher 側)

CONFIG_DB に対する書き込み元は **すべて直接 Redis HSET ベース**。`ProducerStateTable` ではない:

| 書き込み元 | 書き込み手段 |
|---|---|
| `counterpoll flowcnt-trap enable/disable/interval` | `swsssdk.ConfigDBConnector.mod_entry()` → Redis HSET (sonic-utilities/counterpoll/main.py:19, 該当 group) |
| `counterpoll flowcnt-route enable/disable/interval` | 同上 |
| `config flowcnt-route pattern add/del` | `swsssdk.ConfigDBConnector.set_entry()` → Redis HSET / DEL (sonic-utilities/config/flow_counters.py) |
| `sonic-cfggen` / `config_db.json` | sonic-cfggen による一括 HSET |

HSET が走ると Redis サーバが自動的に keyspace 通知 `__keyspace@4__:<key>` を `notify-keyspace-events` 設定 (`KEA` 等) に従って publish する。これを orchagent の `SubscriberStateTable` が拾う。

---

## FLEX_COUNTER_DB への波及 (Producer 側参考)

orchagent → syncd への伝達は CONFIG_DB ではなく **FLEX_COUNTER_DB (DB 5)** 経由。FlexCounterOrch が `setFlexCounterGroupOperation` / `setFlexCounterGroupPollInterval` を呼ぶと:

```
operateFlexCounterGroupDatabase(group, poll_interval, ..., operation, is_gearbox):
  gFlexCounterGroupTable->set(group, {FLEX_COUNTER_STATUS:operation,
                                       POLL_INTERVAL:poll_interval, ...})
                          ← ProducerTable (saihelper.cpp:117,324,884)
```

`gFlexCounterGroupTable` / `gFlexCounterTable` はいずれも `ProducerTable` (FLEX_COUNTER_DB 上)。`ProducerTable` は LPUSH + PUBLISH モデルで syncd 側 `ConsumerTable` が pop する。ただし新 redis-sai 経路では `notifySyncdCounterOperation` 経由で SAI redis switch attr (`SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP`) 直書きルートが優先され、`gTraditionalFlexCounter` フラグでのみ ProducerTable が使われる (saihelper.cpp:918-962)。**詳細は別資料 (flex-counter-db pubsub) のスコープ**。

---

## フィールド × 購読者 マトリクス

| テーブル/フィールド | FlexCounterOrch | FlowCounterRouteOrch | copporch (副作用呼び出し) | FlowCounterRouteOrch timer |
|---|:---:|:---:|:---:|:---:|
| `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` `FLEX_COUNTER_STATUS` | 解釈 | - | 呼ばれる (`generateHostIfTrapCounterIdList`) | - |
| `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` `POLL_INTERVAL` | 解釈 → setFlexCounterGroupPollInterval | - | - | - |
| `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` `FLEX_COUNTER_STATUS` | 解釈 | 呼ばれる (`generateRouteFlowStats` / `clearRouteFlowStats`) | - | - |
| `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` `POLL_INTERVAL` | 解釈 → setFlexCounterGroupPollInterval | - | - | - |
| `FLOW_COUNTER_ROUTE_PATTERN|<key>` `max_match_count` | - | 解釈 → addRoutePattern | - | 毎秒 pending route を flex counter 化 |

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis PSUBSCRIBE (keyspace notification) |
| PSUBSCRIBE パターン | `__keyspace@4__:FLEX_COUNTER_TABLE\|*` / `__keyspace@4__:FLOW_COUNTER_ROUTE_PATTERN\|*` |
| keyspace イベント名 | `hset` / `del` 等の Redis 操作名 |
| フィールド値取得 | 通知後に HGETALL で別途取得 |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` (Orch::addConsumer 経由) |
| ConsumerStateTable | **不使用** (CONFIG_DB は ProducerStateTable 経路を持たないため) |
| NotificationConsumer | **不使用** |
| keyspace expire / TTL | **不使用** |
| 起動時スナップショット | `SubscriberStateTable` ctor が getKeys()+get() で既存全エントリを SET_COMMAND として buffer 充填 |
| Warm restart 遅延 | FlexCounterOrch のみ 60 秒 (`FLEX_COUNTER_DELAY_SEC`)、その間 doTask は no-op |
| 内部タイマー | `FlowCounterRouteOrch` の `FLEX_COUNTER_UPD_TIMER` = 1 秒 (`FLEX_COUNTER_UPD_INTERVAL`) |
| Polling interval ハードコード | `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS = 10000` (copporch.cpp:189), `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS = 10000` (flowcounterrouteorch.cpp:26) |
| 優先度 (pri) | デフォルト 0 (orchdaemon の生成時に pri 指定なし) |
| batch サイズ | `TableConsumable::DEFAULT_POP_BATCH_SIZE` (swsscommon デフォルト 128) |
| 同期実行 | 全 orchagent doTask は単一 thread (`Select` ループ) |
| Producer 側 | `ProducerTable`(gFlexCounterGroupTable, gFlexCounterTable) または SAI redis switch attr 直書き (`notifySyncdCounterOperation`)。CLI からの CONFIG_DB 書き込みは ConfigDBConnector の HSET (ProducerStateTable ではない) |

---

## シーケンス図 (テキスト形式)

```
admin
  │
  │  counterpoll flowcnt-trap enable
  │
  ▼
sonic-utilities (counterpoll/main.py)
  │
  │  ConfigDBConnector.mod_entry("FLEX_COUNTER_TABLE", "FLOW_CNT_TRAP",
  │                              {"FLEX_COUNTER_STATUS": "enable"})
  │
  ▼
Redis CONFIG_DB (db 4)
  │  HSET "FLEX_COUNTER_TABLE|FLOW_CNT_TRAP" FLEX_COUNTER_STATUS enable
  │
  │  keyspace PUBLISH
  │    channel: "__keyspace@4__:FLEX_COUNTER_TABLE|FLOW_CNT_TRAP"
  │    message: "hset"
  │
  ▼
orchagent Select ループ
  │
  ├─► SubscriberStateTable("FLEX_COUNTER_TABLE").pops()
  │     └─ HGETALL "FLEX_COUNTER_TABLE|FLOW_CNT_TRAP"
  │     └─ (key="FLOW_CNT_TRAP", op=SET, fvs={FLEX_COUNTER_STATUS:enable})
  │
  ▼
FlexCounterOrch::doTask(Consumer&)
  ├─ flexCounterGroupMap["FLOW_CNT_TRAP"] = HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP
  ├─ gCoppOrch->generateHostIfTrapCounterIdList()
  │     └─ bindTrapCounter() → SAI create_counter + set_hostif_trap_attribute
  │     └─ m_trap_counter_manager.setCounterIdList(...)  → FLEX_COUNTER_DB へ
  └─ setFlexCounterGroupOperation(HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP, "enable")
        └─ ProducerTable(gFlexCounterGroupTable).set() OR SAI redis switch attr
        ▼
   syncd FlexCounter スレッド
        └─ 10 秒間隔で SAI get_counter_stats(SAI_COUNTER_STAT_PACKETS/BYTES)
        └─ COUNTERS_DB HSET "COUNTERS:<oid>" packets/bytes
```

---

## 競合 / レース

| 競合 | 影響 | 対策 |
|---|---|---|
| keyspace 通知 → HGETALL の間に更新 | 最新値が読まれる (lost-update なし) | 影響なし (SubscriberStateTable 仕様による) |
| 同一 key への高頻度更新 | keyspace 通知が多数届くが doTask は最新 HGETALL を読むだけ | 自然冪等 |
| FLEX_COUNTER_TABLE と FLOW_COUNTER_ROUTE_PATTERN を同時に enable+pattern 追加 | 別 Consumer のためそれぞれ独立処理。Pattern 追加は 1 秒タイマー経由で flex counter 化 | 数秒の遅延あり (UPD_INTERVAL=1s + Bulker 遅延) |
| Warm restart 60 秒中の CONFIG_DB 変更 | doTask は no-op で捨てる…のではなく `m_toSync` に蓄積されたまま (consumer.m_toSync は erase されない)。タイマー満了後に処理される | 設計通り |
| SAI route counter 未対応 platform で FLOW_CNT_ROUTE を enable | `m_route_flow_counter_enabled` は変わらず `generateRouteFlowStats` も呼ばれない (`gFlowCounterRouteOrch->getRouteFlowCounterSupported()` ガード, flexcounterorch.cpp:324) | サイレントに無視 |

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/orchagent/orchdaemon.cpp` | 251-254 | `FlowCounterRouteOrch` の生成 (`FLOW_COUNTER_ROUTE_PATTERN`) |
| `sonic-swss/orchagent/orchdaemon.cpp` | 620-628 | `FlexCounterOrch` の生成 (`FLEX_COUNTER_TABLE`, `DEVICE_METADATA`) |
| `sonic-swss/orchagent/orch.cpp` | 1186-1196 | `Orch::addConsumer` の DB 種別分岐 (CONFIG_DB → SubscriberStateTable) |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-44 | ctor — PSUBSCRIBE + 初回 getKeys スナップショット |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 95-165 | `pops()` — keyspace イベント → HGETALL |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 44 | `FLEX_COUNTER_DELAY_SEC = 60` |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 65-99 | `flexCounterGroupMap` (CONFIG_DB key → flex counter group constant) |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 102-138 | ctor — DEVICE_METADATA read + warm restart timer |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 145-410 | `doTask(Consumer&)` — POLL_INTERVAL / FLEX_COUNTER_STATUS 分岐 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 311-323 | `FLOW_CNT_TRAP` 分岐 → CoppOrch 呼び出し |
| `sonic-swss/orchagent/flexcounterorch.cpp` | 324-336 | `FLOW_CNT_ROUTE` 分岐 → FlowCounterRouteOrch 呼び出し (SAI 能力ガード付) |
| `sonic-swss/orchagent/copporch.cpp` | 189, 198 | `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS = 10000`, `m_trap_counter_manager` 初期化 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | 21-26 | `FLEX_COUNTER_UPD_INTERVAL = 1`, `ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT = 30`, `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS` 利用 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | 28-48 | ctor — SAI 能力チェック + 1 秒タイマー登録 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | 55-97 | `doTask(Consumer&)` — pattern 追加/削除 |
| `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` | 99- | `doTask(SelectableTimer&)` — pending → setCounterIdList |
| `sonic-swss/orchagent/saihelper.cpp` | 117-118, 324-325 | `gFlexCounterTable` / `gFlexCounterGroupTable` (`ProducerTable`) 初期化 |
| `sonic-swss/orchagent/saihelper.cpp` | 868-885 | `operateFlexCounterGroupDatabase` — ProducerTable.set() で FLEX_COUNTER_DB に書く |
| `sonic-swss/orchagent/saihelper.cpp` | 918-962 | `setFlexCounterGroupOperation` / `setFlexCounterGroupPollInterval` — SAI redis 直書き or ProducerTable 分岐 |
