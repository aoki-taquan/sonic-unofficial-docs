# DHCP_RELAY フィールド値分析

## leaf-list / string フィールド

### `dhcpv6_servers` (leaf-list of ipv6-address, ordered-by user)
- 1 件以上 → dhcp6relay が VLAN ごとの upstream サーバ設定に登録
- 0 件（空 leaf-list） → その VLAN のリレーは無効（config_interface.cpp: servers.empty() → skip）
- 順序は設定順（ordered-by user）を維持して dhcp6relay がスキャン

### `rfc6939_support` (string pattern "false|true")
- `"true"` (デフォルト) → dhcp6relay が RFC 6939 Client Link-Layer Address Option (option 79) を追加
- `"false"` → option 79 を付与しない（config_interface.cpp:169: `is_option_79 = false`）

### `interface_id` (string pattern "false|true")
- `"true"` → Interface-ID オプション (OPTION_INTERFACE_ID) をリレーメッセージに挿入
- `"false"` / 未設定 → 非 DualToR 環境ではデフォルト off。DualToR 環境（dual_tor_sock が存在する場合）はデフォルト on（config_interface.cpp:118-122）

## cross-cutting
- `name` キーに対応する VLAN_INTERFACE に IPv6 アドレスが設定されていない場合、その VLAN エントリはスキップ（config_interface.cpp:133-138）
- DHCP_RELAY (DHCPv6) と DHCPV4_RELAY / VLAN.dhcp_servers は独立して機能する（排他ではない）
