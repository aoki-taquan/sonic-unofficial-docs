# FABRIC_MONITOR — Phase F (side-effects) 調査メモ

## 調査対象

- `sonic-swss/cfgmgr/fabricmgr.cpp`
- `sonic-swss/orchagent/fabricportsorch.cpp`

## 結論サマリ

### APPL_DB

`fabricmgrd` の `FabricMgr::doTask()` が CONFIG_DB の変化を受け `APP_FABRIC_MONITOR_DATA_TABLE|FABRIC_MONITOR_DATA` に書き込む。
フィールドは 1 件ずつ逐次 `writeConfigToAppDb()` 経由で転送される（fabricmgr.cpp:50-116）。

### STATE_DB

`FabricPortsOrch` のポーリング処理がポート状態・カウンタを `FABRIC_PORT_TABLE` と `FABRIC_CAPACITY_DATA` に書き込む。
`monState=disable` 時は APPL_DB イベント処理が全スキップされ STATE_DB 書込みも停止する（fabricportsorch.cpp:1396-1399）。

### COUNTERS_DB

FABRIC_MONITOR 変更による COUNTERS_DB への直接書込みは発生しない。
FlexCounter グループはコンストラクタ時に登録済み。

### ASIC_DB

FABRIC_MONITOR は SAI attribute を直接セットしない。
監視処理はカウンタ読取（FlexCounter 経由）に閉じる。
