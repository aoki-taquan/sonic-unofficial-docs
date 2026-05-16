# bgp-globals-af — Phase E ハードコード定数調査

対象ハンドラ: `frrcfgd.py` (`bgp_af_handler`, `global_af_key_map`, `bgp_table_handler_common` の `BGP_GLOBALS_AF` 分岐)

## 抽出した定数

### FRR コマンド literal (`global_af_key_map`)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `distance bgp` コマンド雛形 | `{no:no-prefix}distance bgp {} {} {}` | `ebgp_route_distance` / `ibgp_route_distance` / `local_route_distance` の 3 フィールド揃い時に `address-family` 配下へ投入 | `frrcfgd.py:1824-1826` |
| `rd vpn export` コマンド | `{no:no-prefix}rd vpn export {}` | `rd_vpn_export` フィールドを VPN RD として設定 | `frrcfgd.py:1827` |
| `rt vpn export` コマンド | `{no:no-prefix}rt vpn export {}` | `rt_vpn_export` フィールドを VPN RT として設定 | `frrcfgd.py:1828` |
| `rt vpn import` コマンド | `{no:no-prefix}rt vpn import {}` | `rt_vpn_import` フィールドを VPN RT として設定 | `frrcfgd.py:1829` |
| `rt vpn both` コマンド | `{no:no-prefix}rt vpn both {}` | `rt_vpn_both` フィールドを VPN RT として設定 | `frrcfgd.py:1830` |
| `export vpn` コマンド | `{no:no-prefix}export vpn` | `export_vpn=true` で VPN export を有効化 | `frrcfgd.py:1831` |
| `import vpn` コマンド | `{no:no-prefix}import vpn` | `import_vpn=true` で VPN import を有効化 | `frrcfgd.py:1832` |
| `redistribute connected` コマンド | `{no:no-prefix}redistribute connected` | `redistribute_connected=true` で connected route を redistribute | `frrcfgd.py:1833` |
| `redistribute static route-map` コマンド | `{no:no-prefix}redistribute static route-map {}` | `redistribute_static_rmap` フィールドで static route を route-map 付き redistribute | `frrcfgd.py:1834` |
| `route-map vpn export` コマンド | `{no:no-prefix}route-map vpn export {}` | `rmap_vpn_export` フィールドで VPN export route-map を設定 | `frrcfgd.py:1835` |
| `route-map vpn import` コマンド | `{no:no-prefix}route-map vpn import {}` | `rmap_vpn_import` フィールドで VPN import route-map を設定 | `frrcfgd.py:1836` |
| `maximum-paths` コマンド | `{no:no-prefix}maximum-paths {}` | `max_ebgp_paths` フィールドで eBGP multipath 上限設定 | `frrcfgd.py:1837` |
| `maximum-paths ibgp` コマンド | `{no:no-prefix}maximum-paths ibgp {} {:match-clust-len}` | `max_ibgp_paths` + `ibgp_equal_cluster_length` で iBGP multipath 設定 | `frrcfgd.py:1838-1839` |
| `match-clust-len` 展開 | `equal-cluster-length` | `ibgp_equal_cluster_length=true` のとき付与されるキーワード | `frrcfgd.py:813` |
| `table-map` コマンド | `{no:no-prefix}table-map {}` | `route_download_filter` フィールドで FIB download フィルタを設定 | `frrcfgd.py:1840` |
| `bgp dampening` コマンド雛形 | `{no:no-prefix}bgp dampening {} {} {} {}` | `route_flap_dampen` 系 4 フィールドを用いて dampening 設定 | `frrcfgd.py:1841-1845` |
| `advertise-all-vni` コマンド | `{no:no-prefix}advertise-all-vni` | `advertise-all-vni=true` で全 VNI 広告を有効化 (l2vpn_evpn AF) | `frrcfgd.py:1846` |
| `advertise-svi-ip` コマンド | `{no:no-prefix}advertise-svi-ip` | `advertise-svi-ip=true` で SVI IP を VTEP 広告 | `frrcfgd.py:1847` |
| `advertise-default-gw` コマンド | `{no:no-prefix}advertise-default-gw` | `advertise-default-gw=true` でデフォルト GW を広告 | `frrcfgd.py:1848` |
| `advertise ipv4 unicast` コマンド | `{no:no-prefix}advertise ipv4 unicast` | `advertise-ipv4-unicast=true` で IPv4 unicast 広告 | `frrcfgd.py:1849` |
| `advertise ipv6 unicast` コマンド | `{no:no-prefix}advertise ipv6 unicast` | `advertise-ipv6-unicast=true` で IPv6 unicast 広告 | `frrcfgd.py:1850` |
| `default-originate ipv4` コマンド | `{no:no-prefix}default-originate ipv4` | `default-originate-ipv4=true` で IPv4 default route を originate | `frrcfgd.py:1851` |
| `default-originate ipv6` コマンド | `{no:no-prefix}default-originate ipv6` | `default-originate-ipv6=true` で IPv6 default route を originate | `frrcfgd.py:1852` |
| `autort` コマンド | `{no:no-prefix}autort {}` | `autort` フィールドで RFC8365 互換 RT 自動生成 (hdl_enum_conversion で `_` → `-` 変換) | `frrcfgd.py:1853` |
| `flooding` コマンド | `{no:no-prefix}flooding {}` | `flooding` フィールドで BUM flooding モードを設定 | `frrcfgd.py:1854` |
| `dup-addr-detection` コマンド | `{no:no-prefix}dup-addr-detection` | `dad-enabled=true` で DAD を有効化 | `frrcfgd.py:1855` |
| `dup-addr-detection max-moves` コマンド | `{no:no-prefix}dup-addr-detection max-moves {} time {}` | `dad-max-moves` + `dad-time` で DAD 上限を設定 | `frrcfgd.py:1856-1857` |
| `dup-addr-detection freeze` コマンド | `{no:no-prefix}dup-addr-detection freeze {}` | `dad-freeze` フィールドで DAD freeze 時間を設定 | `frrcfgd.py:1858` |
| `rd` コマンド | `{no:no-prefix}rd {}` | `route-distinguisher` フィールドで RD を設定 | `frrcfgd.py:1859` |
| `route-target import` コマンド | `{no:no-prefix}route-target import {}` | `import-rts` フィールドで RT import を設定 | `frrcfgd.py:1860` |
| `route-target export` コマンド | `{no:no-prefix}route-target export {}` | `export-rts` フィールドで RT export を設定 | `frrcfgd.py:1861` |
| `import vrf` コマンド | `{no:no-prefix}import vrf {}` | `import_vrf` フィールドで VRF import 元を設定 | `frrcfgd.py:1862` |
| `import vrf route-map` コマンド | `{no:no-prefix}import vrf route-map {}` | `import_vrf_route_map` フィールドで VRF import route-map を設定 | `frrcfgd.py:1863` |

### vtysh コマンドプレフィクス定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| vtysh prefix L1 | `configure terminal` | コマンド投入時の先頭行 | `frrcfgd.py:2776` |
| vtysh prefix L2 | `router bgp {} vrf {}` | BGP インスタンス選択 (`local_asn` と `vrf` を埋め込み) | `frrcfgd.py:2777` |
| vtysh prefix L3 | `address-family {} {}` | `af`/`ip_type` を埋め込んで AF コンテキストに入る | `frrcfgd.py:2778` |

### address-family 文字列定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| af/ip_type 分割文字 | `_` | key の `<afi_safi>` 文字列 (`ipv4_unicast` 等) を `split('_')` して af と ip_type を取得 | `frrcfgd.py:2772` |
| 小文字正規化 | `.lower()` | key を小文字化してから split (`IPV4_UNICAST` などの混在を吸収) | `frrcfgd.py:2772` |
| cache key フォーマット | `BGP_GLOBALS_AF&&{}|{}` | `vrf` と `key.lower()` を埋め込んだ一時キャッシュキー | `frrcfgd.py:2774` |

### dampening / distance 暗黙デフォルト (FRR 側)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| FRR `DEFAULT_HALF_LIFE` | `15` (分) | `route_flap_dampen=true` のみ設定時に FRR が使う dampening half-life | FRR `bgpd/bgp_damp.h` |
| FRR `DEFAULT_REUSE` | `750` | dampening reuse threshold の FRR 既定値 | FRR `bgpd/bgp_damp.h` |
| FRR `DEFAULT_SUPPRESS` | `2000` | dampening suppress threshold の FRR 既定値 | FRR `bgpd/bgp_damp.h` |
| FRR eBGP distance | `20` | `distance bgp` 未設定時の FRR eBGP administrative distance | FRR `bgpd` 初期値 |
| FRR iBGP distance | `200` | `distance bgp` 未設定時の FRR iBGP administrative distance | FRR `bgpd` 初期値 |
| FRR local distance | `200` | `distance bgp` 未設定時の FRR local administrative distance | FRR `bgpd` 初期値 |

### hdl_enum_conversion 変換ルール

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| enum 変換文字 | `_` → `-` | `autort` フィールド値の `_` を `-` に置換して FRR コマンドに渡す (`rfc8365_compatible` → `rfc8365-compatible`) | `frrcfgd.py:1393` |
| 対象フィールド | `autort` | `hdl_enum_conversion` を使う `global_af_key_map` 内唯一のフィールド | `frrcfgd.py:1853` |

### comb_attr_list (bgp_af_handler)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| 組み合わせ制約 A | `{ebgp_route_distance, ibgp_route_distance, local_route_distance}` | 3 フィールドが揃わないと `distance bgp` を発行しない | `frrcfgd.py:3939` |
| 組み合わせ制約 B | `{route_flap_dampen_reuse_threshold, route_flap_dampen_suppress_threshold, route_flap_dampen_max_suppress}` | 3 フィールドが揃わないと dampening 引数を発行しない | `frrcfgd.py:3940` |

## スキャン証跡

- `frrcfgd.py` L82 (handler registration), L813 (`match-clust-len`), L1389-1396 (`hdl_enum_conversion`), L1824-1864 (`global_af_key_map` 全行), L2107 (table→key_map dispatch), L2136-2140 (vrf_tables), L2297 (bgp_af_handler 登録), L2771-2782 (`BGP_GLOBALS_AF` runtime 分岐), L3938-3941 (`bgp_af_handler` 定義) を確認。
- 抽出件数: FRR コマンド literal 31 件 + vtysh prefix 3 件 + AF 文字列 3 件 + FRR デフォルト値 6 件 + enum 変換 2 件 + comb_attr_list 2 件 = 計 47 件。
