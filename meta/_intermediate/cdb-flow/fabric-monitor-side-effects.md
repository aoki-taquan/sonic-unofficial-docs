# FABRIC_MONITOR — Phase F side-effects 調査メモ

調査日: 2026-05-19
対象ファイル:
- `sonic-swss/cfgmgr/fabricmgr.cpp`
- `sonic-swss/orchagent/fabricportsorch.cpp`

## fabricmgr.cpp の書込み経路

`FabricMgr::doTask()` (fabricmgr.cpp:23-105) は CONFIG_DB の `FABRIC_MONITOR_DATA` テーブル変化を
受け取り、各フィールドを `writeConfigToAppDb()` に渡す。

`writeConfigToAppDb()` (fabricmgr.cpp:107-124) は:
- `key == "FABRIC_MONITOR_DATA"` → `m_appFabricMonitorTable.set(key, fvs)` = APPL_DB `FABRIC_MONITOR_DATA_TABLE`
- それ以外 → `m_appFabricPortTable.set(key, fvs)` = APPL_DB `APP_FABRIC_MONITOR_PORT_TABLE`

フィールド単位で逐次 SET しているため、複数フィールドを一括更新した場合も
1フィールドずつ別の `set()` 呼び出しになる（中間状態あり）。

## fabricportsorch.cpp の STATE_DB 書込み

### updateFabricDebugCounters() (L430-970)

各ファブリックポートに対して以下を書き込む:
- `POLL_WITH_ERRORS` (L939)
- `POLL_WITH_NO_ERRORS` (L940)
- `POLL_WITH_FEC_ERRORS` (L941)
- `POLL_WITH_NOFEC_ERRORS` (L942)
- `CONFIG_ISOLATED` (L943)
- `ISOLATED` (L944)
- `PRM_ISOLATED` (L945)
- `RX_CELLS` (L949)
- `CRC_ERRORS` (L954)
- `CODE_ERRORS` (L959)
- `AUTO_ISOLATED` (L884 or L893)
- `PORT_DOWN_COUNT_handled` (L756)
- `SKIP_CRC_ERR_ON_LNKUP_CNT` (L774)
- `SKIP_FEC_ERR_ON_LNKUP_CNT` (L825)

テーブル: STATE_DB `FABRIC_PORT_TABLE` (`APP_FABRIC_PORT_TABLE_NAME`)

### updateFabricCapacity() (L1050-1232)

STATE_DB `FABRIC_CAPACITY_TABLE` の `FABRIC_CAPACITY_DATA` エントリを更新 (L1225-1231):
- `fabric_capacity`
- `missing_capacity`
- `operating_links`
- `number_of_links`
- `warning_threshold`
- `last_event`
- `last_event_time`

### monState=enable 時のタイマー副作用

`doFabricPortTask()` (L1549-) は `checkFabricPortMonState()` を確認してから処理。
`m_debugTimer->start()` は init 時 (L127-132) か `doTask()` (L1582-1585) での動的起動。

## ASIC_DB

`isolateFabricLink()` (L984-1007) が `sai_port_api->set_port_attribute(SAI_PORT_ATTR_FABRIC_ISOLATE)` を
呼ぶが、syncd 経由なので fabricportsorch は ASIC_DB を直接書かない。

## COUNTERS_DB

読み取りのみ (L500-529)。FlexCounter 経由で syncd が書く別経路。
