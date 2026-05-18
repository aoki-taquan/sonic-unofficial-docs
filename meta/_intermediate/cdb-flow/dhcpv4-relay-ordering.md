# DHCPV4_RELAY — Phase B ordering analysis

## 対象ページ
`docs/reference/config-db/dhcpv4-relay.md`

## 調査ソース
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp`
  - `initialize_config_listener()` L55-130: 購読テーブル一覧
  - `process_relay_notification()` L371-460: SET 時の server_vrf fallback
  - `process_dhcp_server_ipv4_notification()` L725-810: VLAN 存在チェック

## 検出した順序依存

### VLAN 先行必須
`process_dhcp_server_ipv4_notification()` は `vlan_tbl.hget(vlan, "vlanid", value)` が false を返す場合（VLAN 未存在）イベントを破棄する（L793-800）。DHCP_SERVER_IPV4 経由の relay 設定が silent drop される。

### VLAN_INTERFACE 先行推奨
`server_vrf` 未指定時に `vlan_intf_tbl->hget(vlan, VRF_NAME_FIELD, value)` で取得。VLAN_INTERFACE 未設定なら `"default"` VRF を採用（L421-431）。VLAN_INTERFACE_UPDATE イベントで後追い修正されるが起動時の一時的誤 VRF が発生。

### DEVICE_METADATA.has_sonic_dhcpv4_relay 先行必須
新 `sonic-dhcpv4-relay` が起動する条件。true でなければ旧 dhcrelay が使われ DHCPV4_RELAY を無視する。

### FEATURE.dhcp_server 先行確定
enabled/disabled により watch 対象テーブルが切り替わる（L468-600）。起動中に切り替わると一部イベントが欠落する可能性がある。

## DEL 順序依存
- DHCPV4_RELAY 参照中 VLAN を削除しようとすると `ctx.fail()` で拒否（vlan.py:243）
- DHCPV4_RELAY.server_vrf が残存する VRF は削除を拒否（config/main.py:1699-1706）
