# DHCP_RELAY — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| sonic-dhcp-relay / dhcp6relay config_interface.cpp | DHCPv6 relay 設定の読み込み | sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp:22,135,146,177 |
| sonic-utilities / config/vlan.py | VLAN 削除時の依存チェック | sonic-utilities/config/vlan.py:134,149 |
| sonic-utilities / show dhcp_relay plugins | 表示 | sonic-buildimage/dockers/docker-dhcp-relay/cli/show/plugins/show_dhcp_relay.py:720 |

## 例外条件

### dhcp6relay: VLAN_INTERFACE に存在しない VLAN のスキップ
- config_interface.cpp:135 — DHCP_RELAY に登録された VLAN が VLAN_INTERFACE テーブルに存在しない場合、`LOG_WARNING: "%s doesn't exist in VLAN_INTERFACE table, skip it"` を出力してその VLAN をスキップ。他の VLAN は処理継続。

### dhcp6relay: IPv6 アドレス未設定 VLAN のスキップ
- config_interface.cpp:146 — VLAN に IPv6 アドレスが設定されていない場合、`LOG_WARNING: "%s doesn't have IPv6 address configured, skip it"` を出力してスキップ。

### dhcp6relay: サーバ未設定 VLAN のスキップ
- config_interface.cpp:177 — DHCP_RELAY エントリにサーバアドレスが 1 件も見つからない場合、`LOG_WARNING: "No servers found for VLAN %s, skipping configuration."` を出力。

### dhcp6relay: interface-id デフォルト
- config_interface.cpp:117-121 — `dhcpv6_option|interface_id` フィールド不在時は Dual-ToR でなければ `false`、Dual-ToR 環境では `true` をデフォルトとして使用。明示設定で上書き可能。
