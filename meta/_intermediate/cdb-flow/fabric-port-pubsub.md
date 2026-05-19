# FABRIC_PORT — Phase G Redis 通知メカニズム調査

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/fabric-port.md`

## 購読パス

### CONFIG_DB → fabricmgrd

`fabricmgrd` は `swss::Orch` 基底クラスを継承する `FabricMgr` を通じて CONFIG_DB を購読する。

- `fabricmgrd.cpp:27-35`: `cfg_fabric_tables = { CFG_FABRIC_MONITOR_DATA_TABLE_NAME, CFG_FABRIC_MONITOR_PORT_TABLE_NAME }` = `{ "FABRIC_MONITOR", "FABRIC_PORT" }`
- `FabricMgr(cfgDb, appDb, cfg_fabric_tables)` → `Orch(cfgDb, tableNames)` → 各テーブルに対して `ConsumerStateTable` を生成
- `ConsumerStateTable` コンストラクタ (`consumerstatetable.cpp:27`) が `SUBSCRIBE FABRIC_PORT_CHANNEL@4` を実行
- 主ループ (`fabricmgrd.cpp:46-65`): `s.select(&sel, SELECT_TIMEOUT=1000)` で 1 秒タイムアウトのポーリング

### fabricmgrd → APPL_DB

- `fabricmgr.h:22`: `ProducerStateTable m_appFabricPortTable` — APPL_DB `FABRIC_PORT_TABLE` への書き込み手段
- `FabricMgr::writeConfigToAppDb()` (`fabricmgr.cpp:107-124`): key が `"FABRIC_MONITOR_DATA"` なら `m_appFabricMonitorTable.set()`、それ以外（`FABRIC_PORT` エントリ）なら `m_appFabricPortTable.set()`
- `ProducerStateTable::set()` は Lua script 経由で Redis HSET + `PUBLISH FABRIC_PORT_TABLE_CHANNEL@0`

### APPL_DB → FabricPortsOrch

- `orchdaemon.cpp:603-609`: `{ APP_FABRIC_MONITOR_PORT_TABLE_NAME, fabric_portsorch_base_pri }` = `{ "FABRIC_PORT_TABLE", priority }` で `FabricPortsOrch` を初期化
- `FabricPortsOrch(appl_db, fabric_port_tables)` → `Orch(appl_db, tableNames)` → `ConsumerStateTable` → `SUBSCRIBE FABRIC_PORT_TABLE_CHANNEL@0`
- `orchdaemon.cpp:23`: `#define SELECT_TIMEOUT 1000` ms

### FabricPortsOrch のタイマー

コンストラクタ (`fabricportsorch.cpp:87-133`) でタイマー 2 本を登録:

```cpp
m_timer = new SelectableTimer(timespec { .tv_sec = FABRIC_POLLING_INTERVAL_DEFAULT=30, .tv_nsec = 0 });
m_debugTimer = new SelectableTimer(timespec { .tv_sec = FABRIC_DEBUG_POLLING_INTERVAL_DEFAULT=12, .tv_nsec = 0 });
```

タイマー名:
- `FABRIC_POLL` → `updateFabricPortState()` + (初回のみ `getFabricPortList()` リトライ)
- `FABRIC_DEBUG_POLL` → `updateFabricDebugCounters()` + `updateFabricCapacity()` + `updateFabricRate()`

`m_debugTimer` は起動時に `checkFabricPortMonState()` が true を返す場合のみ `start()` される。
`monState=disable` 状態では debugTimer は停止したまま。

## チャネル命名規則

`swss::TableBase::getChannelName(int tag)` (`table.h:94-96`):
- CONFIG_DB (db 4): `FABRIC_PORT_CHANNEL@4`
- APPL_DB (db 0): `FABRIC_PORT_TABLE_CHANNEL@0`

## DEL 操作の挙動

`FabricMgr::doTask()` (`fabricmgr.cpp:37`) は `op == SET_COMMAND` の場合のみ処理。
DEL は `m_toSync.erase(it)` で消費のみ（APPL_DB への DEL 転送はしない）。

`FabricPortsOrch::doFabricPortTask()` も DEL は `m_toSync.erase(it)` で消費のみ
（`fabricportsorch.cpp:1549-1553`: DEL は silent skip）。

## 起動時スナップショット

ConsumerStateTable は起動時にキーセット (`FABRIC_PORT_KEY_SET`) に残っている pending エントリを
`SCARD` で確認し、`pops()` で処理する（`consumerstatetable.cpp:18-21, 36-`）。

fabricmgrd 起動時は CONFIG_DB の既存エントリを ConsumerStateTable 経由で一括取得して
`FabricMgr::doTask()` で処理する。orchagent 側も同様に APPL_DB の既存エントリを処理する。

## ソース参照

- `sonic-swss/cfgmgr/fabricmgrd.cpp`
- `sonic-swss/cfgmgr/fabricmgr.cpp`
- `sonic-swss/cfgmgr/fabricmgr.h`
- `sonic-swss/orchagent/fabricportsorch.cpp:80-133,1549-1558`
- `sonic-swss/orchagent/orchdaemon.cpp:23,26,603-609`
- `sonic-swss-common/common/consumerstatetable.cpp:14-35`
- `sonic-swss-common/common/producerstatetable.cpp:147,184`
- `sonic-swss-common/common/table.h:85-96`
