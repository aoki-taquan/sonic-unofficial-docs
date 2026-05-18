# orchagent-state — Phase D 調査証跡 (failure behavior)

調査日: 2026-05-18
調査対象: sonic-swss orchagent/main.cpp, orchagent/orchdaemon.cpp, orchagent/portsorch.cpp, orchagent/fdborch.cpp, orchagent/vrforch.cpp, orchagent/macsecpost.cpp, sonic-swss-common/common/warm_restart.cpp

## 概要

orchagent が STATE_DB へ書き込む 5 テーブル（WARM_RESTART_TABLE / PORT_TABLE / FDB_TABLE / VRF_OBJECT_TABLE / FIPS_MACSEC_POST_TABLE）の失敗挙動を調査した。

## テーブル別失敗パターン

### WARM_RESTART_TABLE

- `warmRestoreValidation()` (orchdaemon.cpp:1186-1204): pending task があっても `RESTORED` を書き込んで返す。ts.empty() チェックは呼び出し元が無視している
- `checkWarmStart()` (warm_restart.cpp:113-125): restore_count の stoul 変換失敗 → std::exception → abort
- DB 接続失敗 → 例外伝播 → orchagent 停止

### PORT_TABLE

- `getPortSupportedSpeeds()` (portsorch.cpp:3102-3155):
  - SAI_STATUS_BUFFER_OVERFLOW → SWSS_LOG_ERROR → supported_speeds が空文字で書き込まれる
  - SAI_STATUS_NOT_SUPPORTED / NOT_IMPLEMENTED → SWSS_LOG_WARN → 空文字で書き込まれる
  - SUCCESS → 正常書き込み
- `initPortCapFec()` (portsorch.cpp:3275-3322):
  - FEC 取得非サポート → SWSS_LOG_INFO → supported_fecs **フィールドを書かない**（フィールド自体が存在しない）
  - 不明な FEC モード → SWSS_LOG_ERROR + continue（そのモードをスキップ）
- host_tx_ready 取得失敗 (portsorch.cpp:6717): SWSS_LOG_ERROR、前回値保持

### FDB_TABLE

- `allPortsReady() == false` (fdborch.cpp:711, 927): 即 return → m_toSync に保留 → PortInitDone 後に暗黙 retry
- SAI create/remove 失敗 (fdborch.cpp:1515, 1540, 1709): parseHandleSaiStatusFailure → task_need_retry → it++ (retry) or task_failed → erase
- bridge port ID 解決失敗 (fdborch.cpp:309, 700): SWSS_LOG_ERROR → スキップ（erase）

### VRF_OBJECT_TABLE

- create_virtual_router 失敗 (vrforch.cpp:97-103): handleSaiCreateStatus → task_need_retry (retry) or task_failed (erase)
  - どちらの場合も VRF_OBJECT_TABLE には書き込まれない
- set_virtual_router_attribute 失敗 (vrforch.cpp:132-138): 同上
- remove 時 VRF 未登録 (vrforch.cpp:165): SWSS_LOG_ERROR + return false → STATE_DB del() は実行されない

### FIPS_MACSEC_POST_TABLE

- SAI MACsec POST 非サポート判定 (main.cpp:919-930): SAI_STATUS_SUCCESS 以外 → SWSS_LOG_ERROR → post_state="disabled" 書き込み
- MACsec POST コールバック FAIL (macsecorch.cpp:710, 791): setMacsecPostState("fail") → post_state="fail"
- `setMacsecPostState()` 例外: Table::set() 例外 → orchagent 停止

## key findings

1. PORT_TABLE: SAI 非サポート時は `supported_fecs` を**書かない**が `supported_speeds` は空文字で書く（挙動が非対称）
2. FDB_TABLE: allPortsReady() ガードによる保留は implicit retry（タスク erase されない）
3. VRF_OBJECT_TABLE: SAI 失敗時にエントリが書き込まれないため、vrfmgrd の削除同期にも影響する可能性がある
4. WARM_RESTART_TABLE: warmRestoreValidation() は pending task があっても RESTORED を書き込むが、呼び出し元は戻り値を用いた制御を行う箇所がある
