# fabric-monitor pubsub 調査メモ (Phase G)

調査日: 2026-05-19
対象ソース: sonic-swss cfgmgr/fabricmgrd.cpp, cfgmgr/fabricmgr.h, cfgmgr/fabricmgr.cpp,
            orchagent/orchdaemon.cpp, orchagent/fabricportsorch.cpp, orchagent/fabricportsorch.h
            sonic-swss-common common/schema.h, common/dbconnector.h

## CONFIG_DB → fabricmgrd 購読方式

fabricmgrd の主ループ (fabricmgrd.cpp:27-64) は:

1. CONFIG_DB (DB=4) に接続 (`DBConnector cfgDb("CONFIG_DB", 0)`)
2. `FabricMgr` コンストラクタで `Orch(cfgDb, tableNames)` を呼び出す
   - `tableNames` = `{CFG_FABRIC_MONITOR_DATA_TABLE_NAME, CFG_FABRIC_MONITOR_PORT_TABLE_NAME}`
   - = `{"FABRIC_MONITOR", "FABRIC_PORT"}` (schema.h:405-406)
3. `Orch::Orch(DBConnector*, vector<string>)` が各テーブルに対して
   `addConsumer(db, tableName)` → `Consumer(new SubscriberStateTable(...))` を生成
4. 主ループで `s.select(&sel, SELECT_TIMEOUT=1000ms)` でブロック
   - イベント受信時: `Executor::execute()` → `FabricMgr::doTask(Consumer&)`
   - タイムアウト時: `fabricmgr.doTask()` (pending flush)

購読パターン (SubscriberStateTable 内部):
- `__keyspace@4__:FABRIC_MONITOR|*` (PSUBSCRIBE)
- `__keyspace@4__:FABRIC_PORT|*` (PSUBSCRIBE)

## fabricmgrd → APPL_DB 書き込み方式

- `APP_FABRIC_MONITOR_DATA_TABLE_NAME` = "FABRIC_MONITOR_TABLE" (APPL_DB / DB=0)
  → `m_appFabricMonitorTable` は通常の `Table`（非ストリーミング）
  → `m_appFabricMonitorTable.set(key, fvs)` で hset + 直接書き込み (fabricmgr.cpp:114)
- `APP_FABRIC_MONITOR_PORT_TABLE_NAME` = "FABRIC_PORT_TABLE" (APPL_DB / DB=0)
  → `m_appFabricPortTable` は `ProducerStateTable`
  → `m_appFabricPortTable.set(key, fvs)` で RPUSH + PUBLISH (fabricmgr.cpp:119)

APPL_DB 書き込み時のチャネル PUBLISH:
- `FABRIC_PORT_TABLE_CHANNEL@0` (ProducerStateTable 経由)
- `FABRIC_MONITOR_TABLE` は通常 Table のため PUBLISH なし（LPOP/RPUSH 不使用）

## APPL_DB → FabricPortsOrch 購読方式

orchdaemon.cpp:603-607 にて `FabricPortsOrch` を以下のテーブルで初期化:
```cpp
vector<table_name_with_pri_t> fabric_port_tables = {
   { APP_FABRIC_MONITOR_PORT_TABLE_NAME, fabric_portsorch_base_pri },  // "FABRIC_PORT_TABLE"
   { APP_FABRIC_MONITOR_DATA_TABLE_NAME, fabric_portsorch_base_pri }   // "FABRIC_MONITOR_TABLE"
};
gFabricPortsOrch = new FabricPortsOrch(m_applDb, fabric_port_tables, ...);
```

`FabricPortsOrch` は `Orch` 派生なので `addConsumer(applDb, tableName)` →
`Consumer(new SubscriberStateTable(applDb, tableName, ...))` が生成される。

購読パターン (SubscriberStateTable 内部):
- `__keyspace@0__:FABRIC_PORT_TABLE|*` (PSUBSCRIBE)
- `__keyspace@0__:FABRIC_MONITOR_TABLE|*` (PSUBSCRIBE)

orchdaemon 主ループ SELECT_TIMEOUT = 1000ms (orchdaemon.cpp:23,959)

## `m_appFabricMonitorTable` が通常 Table の理由

fabricmgr.h:23: `Table m_appFabricMonitorTable;` — ProducerStateTable ではない。
FABRIC_MONITOR_DATA は FabricPortsOrch がポーリング (`hgetall`) で読むため、
keyspace notify 経由の Consumer イベントが不要。実質ポーリングドリブン。

ただし `SubscriberStateTable` は keyspace notification を購読しているため、
`hset` による直接書き込みでも Redis keyspace event が発火し
`__keyspace@0__:FABRIC_MONITOR_TABLE|*` の PSUBSCRIBE に通知される。
よって Consumer 側の doTask は呼ばれるが、FabricPortsOrch は `hgetall` で
最新値を読み直す（ポーリング + イベント駆動の二重構造）。
