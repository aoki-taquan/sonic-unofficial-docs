# fabric-monitor — side-effects (Phase F) 調査証跡

調査日: 2026-05-19
対象ページ: docs/reference/config-db/fabric-monitor.md

## 要約

`FABRIC_MONITOR` (CONFIG_DB) への書込みは `cfgmgr/fabricmgr.cpp` を経由し、APPL_DB、STATE_DB、COUNTERS_DB、FLEX_COUNTER_DB に副次的に伝播する。

## 主要証拠

### cfgmgr → APPL_DB (fabricmgr.cpp)

- `fabricmgr.cpp:107-119`: `FabricMgr::writeConfigToAppDb()` が CONFIG_DB 変更をそのまま APPL_DB に転送
  - `key == "FABRIC_MONITOR_DATA"` → `APPL_DB FABRIC_MONITOR_TABLE|FABRIC_MONITOR_DATA`
  - その他 (ポートキー) → `APPL_DB FABRIC_PORT_TABLE|<port_key>`

### orchagent → STATE_DB (fabricportsorch.cpp)

- `fabricportsorch.cpp:94-96`: STATE_DB に `FABRIC_PORT_TABLE` と `FABRIC_CAPACITY_TABLE` テーブルを開設
- `fabricportsorch.cpp:414`: `m_stateTable->set(key, values)` でポート初期状態を書込み
- `fabricportsorch.cpp:884-954`: 各種ポート状態フィールド (`AUTO_ISOLATED`, `CONFIG_ISOLATED`, `ISOLATED`, `POLL_WITH_ERRORS` 等) を `updateStateDbTable()` で STATE_DB に反映
- `fabricportsorch.cpp:1225-1231`: `FABRIC_CAPACITY_TABLE|FABRIC_CAPACITY_DATA` に容量データを書込み

### orchagent → COUNTERS_DB (fabricportsorch.cpp)

- `fabricportsorch.cpp:99-100`: COUNTERS_DB の `COUNTERS_FABRIC_PORT_NAME_MAP` と `COUNTERS_FABRIC_QUEUE_NAME_MAP` テーブルを開設
- `fabricportsorch.cpp:255`: `m_portNamePortCounterTable->set("", portNamePortCounterMap)` でポート名→OID マップを書込み
- `fabricportsorch.cpp:320`: `m_portNameQueueCounterTable->set("", portNameQueueMap)` でキュー名→OID マップを書込み

### orchagent → FLEX_COUNTER_DB (fabricportsorch.cpp)

- `fabricportsorch.cpp:83-88`: コンストラクタで `port_stat_manager` (グループ: `FABRIC_PORT_STAT_COUNTER`) と `queue_stat_manager` (グループ: `FABRIC_QUEUE_STAT_COUNTER`) を初期化
- `fabricportsorch.cpp:253`: `port_stat_manager.setCounterIdList(port, CounterType::PORT, counter_stats)` で per-port カウンタ ID リストを FLEX_COUNTER_DB に書込み
- `fabricportsorch.cpp:318`: `queue_stat_manager.setCounterIdList(...)` で per-queue カウンタ ID リストを書込み
- `fabricportsorch.cpp:1630`: `switch_drop_counter_manager->setCounterIdList(gSwitchId, ...)` でスイッチデバッグカウンタを書込み

### スキーマ定数 (schema.h / fabricportsorch.h)

- `schema.h:40`: `APP_FABRIC_PORT_TABLE_NAME = "FABRIC_PORT_TABLE"`
- `schema.h:548-549`: `APP_FABRIC_MONITOR_DATA_TABLE_NAME = "FABRIC_MONITOR_TABLE"`, `APP_FABRIC_MONITOR_PORT_TABLE_NAME = "FABRIC_PORT_TABLE"`
- `fabricportsorch.h:15`: `STATE_FABRIC_CAPACITY_TABLE_NAME = "FABRIC_CAPACITY_TABLE"`
- `fabricportsorch.cpp:25-28`: `FABRIC_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP = "FABRIC_PORT_STAT_COUNTER"`, `FABRIC_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP = "FABRIC_QUEUE_STAT_COUNTER"`
