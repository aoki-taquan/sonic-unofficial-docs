# port 例外条件エビデンス

## 調査ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port.yang`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/cfgmgr/portmgr.cpp`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `lanes` は mandatory (chassis 以外)、length 1..128。
- `speed` は mandatory、range 1..1600000 (Kbps)。
- `mtu` range: 68..9216。
- `fec` pattern: `rs|fc|none|auto`。
- `autoneg` / `pfc_asym` pattern: `on|off`。
- `adv_speeds`: `all` と他値の混在は `must "(count(adv_speeds[text()='all']) = 0) or (count(adv_speeds) = 1)"` で reject。
- `adv_interface_types`: 同様の `must` 制約。

### consumer (portsorch / portmgr) 例外動作
- 非サポート speed: `portsorch` が SAI でサポート speed リストと照合; 不一致は SWSS_LOG_ERROR + 処理中断 (portsorch.cpp:3137-3151)
- MTU 設定失敗: `Failed to set MTU %u to port pid` → SWSS_LOG_ERROR (portsorch.cpp:2321)
- FEC モード不正: `Failed to set fec override` / `Failed to set FEC mode` → SWSS_LOG_ERROR (portsorch.cpp:2375,2397)
- AutoNeg 設定失敗: `Failed to set AutoNeg %u to port %s` → SWSS_LOG_ERROR (portsorch.cpp:3702)
- `autoneg` 非サポート: `autoneg is not supported (cap=%d)` → SWSS_LOG_ERROR (portsorch.cpp:4819)
- Auto FEC 非サポート: `Auto FEC mode is not supported` → SWSS_LOG_ERROR (portsorch.cpp:5319)
- ハードウェアレーン取得失敗: `Failed to get hardware lane list pid:` → SWSS_LOG_ERROR (portsorch.cpp:1215)
- portmgr MTU netdev 設定失敗: `Setting mtu to alias:%s netdev failed` → SWSS_LOG_WARN + `return false` (portmgr.cpp:43,54)
- portmgr admin_status netdev 設定失敗: `Setting admin_status to alias:%s netdev failed` → SWSS_LOG_WARN + `return false` (portmgr.cpp:76)
