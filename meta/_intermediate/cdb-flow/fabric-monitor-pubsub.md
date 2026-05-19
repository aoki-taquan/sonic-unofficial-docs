# fabric-monitor Phase G (pubsub) 調査メモ

## 調査対象
- `sonic-swss/cfgmgr/fabricmgrd.cpp`
- `sonic-swss/cfgmgr/fabricmgr.cpp`
- `sonic-swss/orchagent/fabricportsorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 通信方式サマリ

### fabricmgrd (CONFIG_DB → APPL_DB)
- `Orch` 基底クラスが `SubscriberStateTable` で CONFIG_DB の `FABRIC_MONITOR|FABRIC_MONITOR_DATA` / `FABRIC_MONITOR|<port>` を購読
- `fabricmgrd.cpp:27-30`: `CFG_FABRIC_MONITOR_DATA_TABLE_NAME`, `CFG_FABRIC_MONITOR_PORT_TABLE_NAME` を tableNames に登録
- `fabricmgrd.cpp:40-65`: `swss::Select` ループ (`SELECT_TIMEOUT=1000ms`)。TIMEOUT 時は `fabricmgr.doTask()` も呼ぶ
- 変化検知後 `FabricMgr::doTask()` が `m_appFabricMonitorTable.set()` (`ProducerStateTable`) で APPL_DB `FABRIC_MONITOR_TABLE|FABRIC_MONITOR_DATA` へ書き込み

### FabricPortsOrch (APPL_DB → orchagent)
- `orchdaemon.cpp:606-607`: `APP_FABRIC_MONITOR_PORT_TABLE_NAME` (`FABRIC_PORT_TABLE`) と `APP_FABRIC_MONITOR_DATA_TABLE_NAME` (`FABRIC_MONITOR_TABLE`) を `FabricPortsOrch` の購読テーブルとして登録
- `fabricportsorch.cpp:1549-1561`: `doTask(Consumer &consumer)` が `APP_FABRIC_MONITOR_PORT_TABLE_NAME` を処理
- ただし `FABRIC_MONITOR_DATA` の閾値値はポーリングタイマー発火時に `m_applMonitorConstTable->get()` (`Table::hgetall`) で直接読み取り (`fabricportsorch.cpp:444`)

### STATE_DB / COUNTERS_DB アクセス
- `m_stateTable`: STATE_DB `FABRIC_PORT_TABLE` を `Table::get` で読み取り / `Table::hset` で書き込み
- `m_fabricCapacityTable`: STATE_DB `FABRIC_CAPACITY_TABLE` を `Table::set` で書き込み
- `m_fabricCounterTable`: COUNTERS_DB `COUNTERS_TABLE` から SAI ポート統計を `Table::get` で読み取り

## keyspace 通知の有無
なし。Orch フレームワークの SubscriberStateTable / Select ループのみ使用。

## 設定反映レイテンシ
- CONFIG_DB → APPL_DB: fabricmgrd の Select ループ（最大 1 秒）
- APPL_DB 閾値値 → orchagent: 次の FABRIC_DEBUG_POLL タイマー（最大 12 秒）
- PORT テーブル変化 → orchagent: ConsumerStateTable 通知で即時 (doTask 呼び出し)
