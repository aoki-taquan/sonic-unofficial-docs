# DHCPV4_RELAY — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-18
調査者: Claude (batch368)
調査対象: `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp`

## 判明した順序依存

1. **VLAN / VLAN_INTERFACE 先行必須**: `process_relay_notification()` が DHCPV4_RELAY SET 処理時に `VLAN_INTERFACE` を同期読み込みして `server_vrf` fallback を決定する。VLAN_INTERFACE 未登録だと `vrf = "default"` ソケットが作られる。
2. **VLAN_MEMBER 先行必須**: ポートが VLAN_MEMBER に登録されていないと relay 対象外と判定される。
3. **DEVICE_METADATA 先行推奨**: `is_dualTor` フラグが設定されていないと DualToR 環境で Link Selection 強制 enable が動作しない。
4. **FEATURE|dhcp_server との排他**: `state=enabled` になると DHCPV4_RELAY watch が停止し `vlans_copy` がクリアされる。DHCPV4_RELAY 書込みは FEATURE SET 前に完了させること。

## コード証拠

- `dhcp4relay_mgr.cpp:57-86`: handle_swss_notification() — Subscribe テーブル一覧
- `dhcp4relay_mgr.cpp:135-157`: feature_dhcp_server_enabled フラグによる watch 切替え
- `dhcp4relay_mgr.cpp:371-459`: process_relay_notification() — VLAN_INTERFACE 同期読み
- `dhcp4relay_mgr.cpp:479-541`: process_feature_notification() — vlans_copy クリア
- `dhcp4relay_mgr.cpp:619-663`: process_vlan_member_notification()
- `dhcp4relay_mgr.cpp:822-861`: process_vlan_notification()
