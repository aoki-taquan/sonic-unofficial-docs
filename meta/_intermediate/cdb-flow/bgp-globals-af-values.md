# BGP_GLOBALS_AF 値依存挙動分析

## enum フィールド

### autort (`BGP_GLOBALS_AF`)
- YANG: `sonic-bgp-global.yang` line 451 — `enum rfc8365-compatible`
- frrcfgd: `hdl_enum_conversion` → `autort rfc8365-compatible` (replace `_` with `-`)
- 参照: `frrcfgd.py:1853` `'{no:no-prefix}autort {}'`

### advertise-all-vni (boolean)
- `frrcfgd.py:1846` `['true','false']` → `advertise-all-vni` / `no advertise-all-vni`

### afi_safi (key field)
- `ipv4_unicast`, `ipv6_unicast`, `l2vpn_evpn` 等がテンプレ展開時 address-family ブロックを選択
- l2vpn_evpn + `advertise-all-vni=true` → FRR `advertise-all-vni` コマンド追加

## boolean フィールド (route_flap_dampen, ibgp_equal_cluster_length 等)
- すべて frrcfgd の generic boolean 処理で FRR コマンド on/off

## まとめ
- enum 有り: `autort` (1値), `afi_safi` (key, 挙動分岐)
- advertise-all-vni は boolean だが l2vpn_evpn AF 限定で意味を持つ
