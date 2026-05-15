# VLAN_INTERFACE — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/vlan-interface.md`
調査日: 2026-05-15
Evidence:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgr.h`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`
- `sonic-swss-common/common/table.h`

---

## 概要

`VLAN_INTERFACE` テーブルは 2 系統の購読経路を持つ。

| 購読者 | 購読先 DB | 方式 | Redis primitive |
|--------|----------|------|-----------------|
| `intfmgrd` (IntfMgr) | CONFIG_DB | **SubscriberStateTable** | PSUBSCRIBE (keyspace notification) |
| `orchagent` (IntfsOrch) | APPL_DB | **ConsumerStateTable** | PUBLISH/SUBSCRIBE (channel ベース) |

`NotificationConsumer` は使用しない。TTL/keyevent expire 通知も使用しない。

---

## 通信シーケンス (intfmgrd)

### 1. 初期化 — `intfmgrd` 起動 (intfmgrd.cpp:28-51)

```
intfmgrd 起動 (main)
  └─ DBConnector cfgDb("CONFIG_DB", 0)
  └─ DBConnector appDb("APPL_DB", 0)
  └─ DBConnector stateDb("STATE_DB", 0)
  └─ vector<string> cfg_intf_tables = {
         CFG_INTF_TABLE_NAME,
         CFG_LAG_INTF_TABLE_NAME,
         CFG_VLAN_INTF_TABLE_NAME,          ← "VLAN_INTERFACE"
         CFG_LOOPBACK_INTERFACE_TABLE_NAME,
         CFG_VLAN_SUB_INTF_TABLE_NAME,
         CFG_VOQ_INBAND_INTERFACE_TABLE_NAME
     }
  └─ IntfMgr intfmgr(&cfgDb, &appDb, &stateDb, cfg_intf_tables)
  └─ swss::Select s
  └─ s.addSelectables(intfmgr.getSelectables())   ← Consumer を登録
```

### 2. Consumer 登録 — Orch 基底クラス (orch.cpp:97-101, 1186-1195)

`IntfMgr` は `Orch(cfgDb, tableNames)` を継承する。`Orch` ctor は各テーブルについて `addConsumer()` を呼ぶ。

```cpp
// orch.cpp:1186-1195
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB ...)
        addExecutor(new Consumer(
            new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    else
        addExecutor(new Consumer(
            new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

- CONFIG_DB (db_id=4) に対しては **SubscriberStateTable** が選択される。
- `CFG_VLAN_INTF_TABLE_NAME` ("VLAN_INTERFACE") も同一パスで登録される。

### 3. SubscriberStateTable 初期化 (subscriberstatetable.cpp:17-24)

```
SubscriberStateTable ctor
  └─ m_keyspace = "__keyspace@4__:VLAN_INTERFACE|*"
  └─ psubscribe(m_db, "__keyspace@4__:VLAN_INTERFACE|*")
       └─ Redis PSUBSCRIBE "__keyspace@4__:VLAN_INTERFACE|*"
```

- keyspace pattern: `__keyspace@{db_id}__:VLAN_INTERFACE|*`
- `psubscribe()` が Redis に `PSUBSCRIBE` コマンドを送信する

### 4. CONFIG_DB への書き込み (Producer 側)

CONFIG_DB への書き込み (CLI / minigraph / sonic-cfggen) は直接 `HSET` を使う。
keyspace notification (`notify-keyspace-events = "KEA"`) が CONFIG_DB で有効化されているため、
`HSET VLAN_INTERFACE|Vlan100 field value` → Redis が自動的に
`PUBLISH __keyspace@4__:VLAN_INTERFACE|Vlan100 hset` を発行する。

### 5. SubscriberStateTable::pops (subscriberstatetable.cpp:95-165)

```
readData()
  └─ redisGetReply() で pmessage を受信
  └─ m_keyspace_event_buffer に蓄積

pops(vkco)
  for msg in m_keyspace_event_buffer:
    key = extract_key_from_keyspace_event(msg.channel)  ← "VLAN_INTERFACE|Vlan100" の "Vlan100"
    op  = msg.data  ← "hset" → SET_COMMAND, "del" → DEL_COMMAND
    m_table.get(key, fieldValues)   ← CONFIG_DB HGETALL("VLAN_INTERFACE|Vlan100")
    vkco.emplace_back(key, op, fieldValues)
  m_keyspace_event_buffer.clear()
```

### 6. Select ループ (intfmgrd.cpp:54-73)

```
while (true)
  ret = s.select(&sel, SELECT_TIMEOUT=1000ms)
  ├─ ERROR   → SWSS_LOG_NOTICE("Error: %s!") ; continue
  ├─ TIMEOUT → intfmgr.doTask()              ← 遅延タスク再実行
  └─ データあり
       → (Executor*)sel → c->execute()
            └─ Consumer::execute()
                 └─ pops(vkco)
                 └─ addToSync(vkco)
                 └─ intfmgr.doTask(consumer)
                      └─ doIntfGeneralTask / doIntfAddrTask / doPortTableTask
```

### 7. intfmgrd → APPL_DB (ProducerStateTable)

`IntfMgr` は 1 つの `ProducerStateTable` を持つ:

```cpp
// intfmgr.h:31
ProducerStateTable m_appIntfTableProducer;
// intfmgr.cpp:42
m_appIntfTableProducer(appDb, APP_INTF_TABLE_NAME)  // APP_INTF_TABLE = "INTF_TABLE"
```

書き込み時:

```
m_appIntfTableProducer.set(alias, fvVector)
  └─ EVALSHA <luaSet> 3 INTF_TABLE_CHANNEL@0 INTF_TABLE_KEY_SET _INTF_TABLE|alias
       Lua 内:
         SADD INTF_TABLE_KEY_SET "alias"
         HSET _INTF_TABLE|alias field1 val1 ...
         (added > 0) PUBLISH INTF_TABLE_CHANNEL@0 "G"

m_appIntfTableProducer.del(alias)
  └─ EVALSHA <luaDel> 2 INTF_TABLE_CHANNEL@0 INTF_TABLE_DEL_SET
       Lua 内:
         SADD INTF_TABLE_DEL_SET "alias"
         PUBLISH INTF_TABLE_CHANNEL@0 "G"
```

追加 SubscriberStateTable (STATE_DB 監視):

```cpp
// intfmgr.cpp:45-53
new SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME, ...)   ← PORT 状態変化
new SubscriberStateTable(stateDb, STATE_LAG_TABLE_NAME, ...)    ← LAG 状態変化
```

STATE_DB の `STATE_VLAN_TABLE` は `m_stateVlanTable` (通常の `Table`) として READ のみ。

---

## 通信シーケンス (orchagent / IntfsOrch)

orchdaemon.cpp:296:
```cpp
gIntfsOrch = new IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, vrf_orch, m_chassisAppDb);
```

`IntfsOrch` は `Orch(db, tableName, pri)` 経由で `addConsumer()` を呼ぶ。
`m_applDb` は APPL_DB (db_id=0) → `ConsumerStateTable` が選択される。

```
orchagent 起動
  └─ ConsumerStateTable(appDb, "INTF_TABLE", gBatchSize)
       └─ WATCH INTF_TABLE_KEY_SET
       └─ SCARD INTF_TABLE_KEY_SET      ← 起動時スナップショット
       └─ SUBSCRIBE "INTF_TABLE_CHANNEL@0"
  ← intfmgrd ProducerStateTable.set/del → PUBLISH INTF_TABLE_CHANNEL@0 "G"
  └─ orchagent IntfsOrch::doTask(consumer)
       └─ setIntf() / removeIntf()
       └─ sai_router_interface_api->create_router_interface(...)
       └─ sai_route_api->create_route(...)
```

chassis (VOQ) 構成では追加で:
```cpp
// intfsorch.cpp:102-108
Orch::addExecutor(new Consumer(
    new SubscriberStateTable(chassisAppDb, CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME, ..., 0),
    this, CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME));
```

---

## STATE_DB 書き込み (intfmgrd)

`IntfMgr` が STATE_DB `STATE_INTERFACE_TABLE` に書き込む (TTL なし通常 hset):

| 操作 | コード | 内容 |
|------|--------|------|
| L3 IF 設定完了 | intfmgr.cpp:1054 | `m_stateIntfTable.hset(alias, "vrf", vrf_name)` |
| IP アドレス追加完了 | intfmgr.cpp:1138 | `m_stateIntfTable.hset(alias+"\|"+pfx, "state", "ok")` |
| IP アドレス削除 | intfmgr.cpp:1162 | `m_stateIntfTable.del(...)` |
| IF 属性削除 | intfmgr.cpp:1089 | `m_stateIntfTable.del(alias)` |

**hSetWithTTL は使用されない。**

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| CONFIG_DB → intfmgrd 通知種別 | Redis PSUBSCRIBE (keyspace notification) |
| keyspace pattern | `__keyspace@4__:VLAN_INTERFACE\|*` |
| keyspace events 設定 | `notify-keyspace-events = "KEA"` (全 Key コマンド + Expire) |
| intfmgrd → APPL_DB 通知種別 | Redis PUBLISH/SUBSCRIBE (channel ベース) |
| Publish チャンネル | `INTF_TABLE_CHANNEL@0` |
| PUBLISH ペイロード | 固定文字列 `"G"` |
| APPL_DB → orchagent 通知種別 | Redis PUBLISH/SUBSCRIBE (ConsumerStateTable) |
| SWSS abstraction | `swss::SubscriberStateTable` + `swss::Select` (1000ms タイムアウトポーリング) |
| ConsumerStateTable 内部 | `SCARD`/`SPOP` + Lua アトミックスクリプト |
| NotificationConsumer | **不使用** |
| TTL / keyevent expire | **不使用** (keyspace notification は有効だが TTL は未設定) |
| 起動時スナップショット | `ConsumerStateTable` ctor が `SCARD INTF_TABLE_KEY_SET` でキュー長を初期化 |
| batch サイズ | `gBatchSize` (デフォルト 128) |
| タイムアウト | 1000ms (SELECT_TIMEOUT、intfmgrd.cpp:17) |
| TIMEOUT 時の動作 | `intfmgr.doTask()` で保留タスクを再実行 (VRF/PORT 未準備時の retry) |
| warm-restart 対応 | `WarmStart::isWarmStart()` 判定で `buildIntfReplayList()` が既存 STATE_DB をスキャン |

---

## 全体フロー図

```
CONFIG_DB[VLAN_INTERFACE|*]
  ↓ SubscriberStateTable (PSUBSCRIBE __keyspace@4__:VLAN_INTERFACE|*)
intfmgrd::doIntfGeneralTask / doIntfAddrTask
  ↓ ProducerStateTable::set/del
  ↓ EVALSHA → SADD INTF_TABLE_KEY_SET + HSET _INTF_TABLE:key + PUBLISH INTF_TABLE_CHANNEL@0 "G"
APPL_DB[INTF_TABLE|*]
  ↓ ConsumerStateTable (SUBSCRIBE INTF_TABLE_CHANNEL@0)
  ↓ EVALSHA consumer_state_table_pops.lua → SPOP KEY_SET + HGETALL
orchagent::IntfsOrch::doTask
  ↓ sai_router_intf_api->create_router_interface (SAI)
  ↓ sai_route_api->create_route (connected route)

STATE_DB[STATE_INTERFACE_TABLE|*]
  ← intfmgrd::hset (vrf, state=ok) [TTLなし]
  → SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME) → intfmgrd::doPortTableTask

(chassis/VOQ のみ)
CHASSIS_APP_DB[SYSTEM_INTERFACE_TABLE|*]
  ↓ SubscriberStateTable → IntfsOrch::doTask (VOQ パス)
```

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/cfgmgr/intfmgrd.cpp` | 17 | `SELECT_TIMEOUT = 1000` (ms) |
| `sonic-swss/cfgmgr/intfmgrd.cpp` | 28-35 | `cfg_intf_tables` 定義 (`CFG_VLAN_INTF_TABLE_NAME` 含む) |
| `sonic-swss/cfgmgr/intfmgrd.cpp` | 54-73 | `swss::Select` ループ本体 |
| `sonic-swss/cfgmgr/intfmgr.cpp` | 31-53 | `IntfMgr` ctor — SubscriberStateTable / ProducerStateTable 初期化 |
| `sonic-swss/cfgmgr/intfmgr.h` | 31 | `ProducerStateTable m_appIntfTableProducer` |
| `sonic-swss/orchagent/orch.cpp` | 97-101 | `Orch(cfgDb, tableNames)` ctor |
| `sonic-swss/orchagent/orch.cpp` | 1186-1195 | `Orch::addConsumer()` — CONFIG_DB→SubscriberStateTable, APPL_DB→ConsumerStateTable |
| `sonic-swss/orchagent/orchdaemon.cpp` | 296 | `IntfsOrch` 生成 (`APP_INTF_TABLE_NAME`) |
| `sonic-swss/orchagent/intfsorch.cpp` | 61-110 | `IntfsOrch` ctor — chassis VOQ SubscriberStateTable |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-24 | ctor — PSUBSCRIBE 初期化 |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 45-165 | `readData()` / `pops()` |
| `sonic-swss-common/common/producerstatetable.cpp` | 129-168 | `set()` — EVALSHA (SADD + HSET + PUBLISH) |
| `sonic-swss-common/common/consumerstatetable.cpp` | 14-34 | ctor — WATCH/SCARD/SUBSCRIBE |
