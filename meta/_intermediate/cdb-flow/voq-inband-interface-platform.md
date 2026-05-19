# VOQ_INBAND_INTERFACE — Phase H (platform) 調査ノート

調査日: 2026-05-19
調査対象:
- `sonic-swss/orchagent/main.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 主要知見

### switch_type ゲート

`intfmgrd` は `CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` を常に購読するが、設定が実際に意味を持つのは `switch_type == "voq"` の環境のみ。

- `intfmgr.cpp:72-75`: `cfgDeviceMetaDataTable.hget("localhost", "switch_type", swtype)` で `mySwitchType` を初期化
- `intfmgr.cpp:1195`: `table_name == CFG_VOQ_INBAND_INTERFACE_TABLE_NAME && op == SET_COMMAND` の分岐は switch_type チェックを明示しないが、VOQ_INBAND_INTERFACE のエントリは VOQ 環境でのみ minigraph.py が生成するため実質 VOQ 専用
- `intfmgr.cpp:103`: `if(mySwitchType == "voq")` → IPv6 `metric 256` 付与。他 switch_type では metric 付与なし
- fabric switch では `FabricOrchDaemon` が使われ IntfsOrch は起動しない

### SAI 前提 (main.cpp:694-736)

`gMySwitchType == "voq"` かつ `getSystemPortConfigList()` 成功時のみ:
- `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_VOQ` を `sai_create_switch()` に投入
- `SAI_SWITCH_ATTR_SWITCH_ID = gVoqMySwitchId` (DEVICE_METADATA.switch_id から取得)
- `SAI_SWITCH_ATTR_MAX_SYSTEM_CORES = gVoqMaxCores` (DEVICE_METADATA.max_cores から取得)
- `SAI_SWITCH_ATTR_SYSTEM_PORT_CONFIG_LIST` に SYSTEM_PORT 由来リスト
- SYSTEM_PORT が 0 件の場合は `exit(EXIT_FAILURE)` (main.cpp:719)

### multi-asic vs standalone VOQ

- `isChassisAppDbPresent()` が true → `gMultiAsicVoq = true`、CHASSIS_APP_DB 接続 (main.cpp:725-736)
- 失敗時は `SWSS_LOG_NOTICE("CHASSIS_APP_DB not available, operating in standalone VOQ mode")` でスタンドアロン動作
- VOQ_INBAND_INTERFACE 処理ロジック自体への直接影響なし。間接的に LAG/System Port の chassis 同期有無が変わる

### portsorch setVoqInbandIntf (portsorch.cpp:11110-11137)

- `getPort(alias, port)` 失敗 → `SWSS_LOG_ERROR("Port/Vlan configured for inband intf %s is not ready!")` → false 返却
- `type == "port" && !port.m_hif_id` → `SWSS_LOG_ERROR("Host interface is not available for port %s")` → false 返却
- 両エラーとも ASIC 種別依存でなく、ポート初期化完了タイミング依存

## 結論

`VOQ_INBAND_INTERFACE` は SAI `SAI_SWITCH_TYPE_VOQ` をサポートする ASIC ハードウェアと
`switch_type == "voq"` CONFIG が揃った環境専用の機能。通常スイッチ・fabric switch では
テーブル自体は CONFIG_DB に存在できるが orchagent が処理しない。
