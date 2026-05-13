# DHCPV4_RELAY フィールド値分析

## mode-status フィールド

### `link_selection` (mode-status: enable/disable)
- `enable` → dhcp4relay が RFC 3527 Link Selection Sub-option をリレーパケットに付与（dhcp4relay.cpp:521）
- `disable` (デフォルト) → Link Selection なし。ただし DualToR 環境（is_dualTor = true）では `link_selection_opt` が `enable` 相当に自動セット（dhcp4relay.cpp:265）

### `server_id_override` (mode-status: enable/disable)
- `enable` → RFC 5107 Server-ID Override sub-option を付与（dhcp4relay.cpp:530）
- `disable` (デフォルト) → Server-ID Override なし
- YANG must: `server_vrf` 設定時は `link_selection = enable` かつ `server_id_override = enable` が必須

### `vrf_selection` (mode-status: enable/disable)
- `enable` → RFC 6607 VRF Selection sub-option を付与（dhcp4relay.cpp:540）。`server_vrf` 必須（YANG must）
- `disable` (デフォルト) → VRF Selection なし

## string フィールド

### `server_vrf` (leafref: VRF.name)
- 設定あり → dhcp4relay がサーバ側 VRF を指定してパケット転送
- YANG must: `link_selection = enable` かつ `server_id_override = enable` かつ `vrf_selection = enable` が必須

### `source_interface`
- 設定あり → リレーパケットの giaddr / source IP をその IF の IP に設定
- 未設定 → 出力 IF の IP を giaddr として使用（IP なし IF の場合 giaddr = 0.0.0.0 → サーバが応答しない恐れ）

### `dhcpv4_servers` (leaf-list, min 1)
- 1 件以上 → 正常動作。dhcp4relay_mgr が サーバリストを設定
- 0 件 → YANG min-elements 違反で reject

## cross-cutting
- DEVICE_METADATA.has_sonic_dhcpv4_relay = false のとき、このテーブルは sonic-dhcpv4-relay に読まれない（旧来 dhcrelay が VLAN.dhcp_servers を使う）
- DualToR 構成では link_selection が自動 enable になるため、明示的な enable 設定は冗長だが問題なし
