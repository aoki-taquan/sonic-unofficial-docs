# bgp-peer-group-af — Phase E ハードコード定数調査

対象ハンドラ: `frrcfgd.py` (`nbr_af_key_map` / `bgp_table_handler_common` の `BGP_PEER_GROUP_AF` 分岐)

## 抽出した定数

### FRR コマンド literal (`nbr_af_key_map` — `BGP_PEER_GROUP_AF` と `BGP_NEIGHBOR_AF` で共用)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `allowas-in` コマンド | `{no:no-prefix}neighbor {} allowas-in {:allow-as-in}` | `allow_as_in=true` + `allow_as_count` / `allow_as_origin` の複合条件で投入 | `frrcfgd.py:1895` |
| `activate` コマンド (ipv4) | `{no:no-prefix}neighbor {} activate` | `admin_status\|ipv4` キーに対して AF を有効/無効化 | `frrcfgd.py:1896` |
| `activate` コマンド (ipv6) | `{no:no-prefix}neighbor {} activate` | `admin_status\|ipv6` キーに対して AF を有効/無効化 | `frrcfgd.py:1897` |
| `activate` コマンド (l2vpn) | `{no:no-prefix}neighbor {} activate` | `admin_status\|l2vpn` キーに対して AF を有効/無効化 | `frrcfgd.py:1898` |
| `default-originate` コマンド | `{no:no-prefix}neighbor {} default-originate {:default-rmap}` | `send_default_route=true` 時、`default_rmap` があれば `route-map <name>` を付与 | `frrcfgd.py:1899` |
| `default-originate route-map` コマンド | `{no:no-prefix}neighbor {} default-originate route-map {}` | `default_rmap` 単独フィールドで route-map 名を適用 | `frrcfgd.py:1900` |
| `maximum-prefix` コマンド | `{no:no-prefix}neighbor {} maximum-prefix {} {} {:restart}` | `max_prefix_limit` + `max_prefix_warning_threshold` + `max_prefix_restart_interval` / `max_prefix_warning_only` の複合投入 | `frrcfgd.py:1901-1902` |
| `route-map {} in` コマンド | `{no:no-prefix}neighbor {} route-map {} in` | `route_map_in` フィールドで inbound route-map を適用 | `frrcfgd.py:1903` |
| `route-map {} out` コマンド | `{no:no-prefix}neighbor {} route-map {} out` | `route_map_out` フィールドで outbound route-map を適用 | `frrcfgd.py:1904` |
| `soft-reconfiguration inbound` コマンド | `{no:no-prefix}neighbor {} soft-reconfiguration inbound` | `soft_reconfiguration_in=true` で soft-reconfiguration を有効化 | `frrcfgd.py:1905` |
| `unsuppress-map` コマンド | `{no:no-prefix}neighbor {} unsuppress-map {}` | `unsuppress_map_name` フィールドで unsuppress-map を適用 | `frrcfgd.py:1906` |
| `route-reflector-client` コマンド | `{no:no-prefix}neighbor {} route-reflector-client` | `rrclient=true` で RR クライアントとして設定 | `frrcfgd.py:1907` |
| `weight` コマンド | `{no:no-prefix}neighbor {} weight {}` | `weight` フィールドで weight を設定 | `frrcfgd.py:1908` |
| `as-override` コマンド | `{no:no-prefix}neighbor {} as-override` | `as_override=true` で AS override を有効化 | `frrcfgd.py:1909` |
| `send-community` コマンド | `{no:no-prefix}neighbor {} send-community {}` | `send_community` フィールドで community 送出種別を設定 (`hdl_send_com` で展開) | `frrcfgd.py:1910` |
| `addpath` コマンド | `{no:no-prefix}neighbor {} {:tx-add-paths}` | `tx_add_paths` フィールド値を `tx-add-paths` 書式変換して投入 | `frrcfgd.py:1911` |
| `attribute-unchanged` コマンド | `{no:no-prefix}neighbor {} attribute-unchanged {:uchg-as-path} {:uchg-med} {:uchg-nh}` | `unchanged_as_path` / `unchanged_med` / `unchanged_nexthop` の複合条件で attribute-unchanged を設定 | `frrcfgd.py:1912-1913` |
| `filter-list {} in` コマンド | `{no:no-prefix}neighbor {} filter-list {} in` | `filter_list_in` フィールドで inbound AS-path filter-list を適用 | `frrcfgd.py:1914` |
| `filter-list {} out` コマンド | `{no:no-prefix}neighbor {} filter-list {} out` | `filter_list_out` フィールドで outbound AS-path filter-list を適用 | `frrcfgd.py:1915` |
| `next-hop-self` コマンド | `{no:no-prefix}neighbor {} next-hop-self` | `nhself=true` で next-hop-self を有効化 | `frrcfgd.py:1916` |
| `next-hop-self force` コマンド | `{no:no-prefix}neighbor {} next-hop-self force` | `nexthop_self_force=true` で next-hop-self force を有効化 | `frrcfgd.py:1917` |
| `prefix-list {} in` コマンド | `{no:no-prefix}neighbor {} prefix-list {} in` | `prefix_list_in` フィールドで inbound prefix-list を適用 | `frrcfgd.py:1918` |
| `prefix-list {} out` コマンド | `{no:no-prefix}neighbor {} prefix-list {} out` | `prefix_list_out` フィールドで outbound prefix-list を適用 | `frrcfgd.py:1919` |
| `remove-private-AS` コマンド | `{no:no-prefix}neighbor {} remove-private-AS {:rm-as-all} {:rm-as-repl}` | `remove_private_as_enabled` + `remove_private_as_all` + `replace_private_as` の複合条件で投入 | `frrcfgd.py:1920-1922` |
| `capability orf prefix-list` コマンド | `{no:no-prefix}neighbor {} capability orf prefix-list {}` | `cap_orf` フィールドで ORF capability を設定 (`hdl_capa_orf_pfxlist` で展開) | `frrcfgd.py:1923` |
| `route-server-client` コマンド | `{no:no-prefix}neighbor {} route-server-client` | `route_server_client=true` で route-server-client を有効化 | `frrcfgd.py:1924` |

### vtysh コマンドプレフィクス定数 (BGP_PEER_GROUP_AF runtime 分岐)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| vtysh prefix L1 | `configure terminal` | コマンド投入時の先頭行 | `frrcfgd.py:2869` |
| vtysh prefix L2 | `router bgp {} vrf {}` | `local_asn` と `vrf` を埋め込んで BGP インスタンスを選択 | `frrcfgd.py:2870` |
| vtysh prefix L3 | `address-family {} {}` | `af` / `ip_type` を埋め込んで AF コンテキストに入る | `frrcfgd.py:2871` |

### address-family 文字列定数 (key parse)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| key 分割文字 | `\|` | `key.split('\|')` で `<peer_group_name>` と `<afi_safi>` を分離 | `frrcfgd.py:2866` |
| af/ip_type 分割文字 | `_` | `af_type.lower().split('_')` で af と ip_type を分離 (`ipv4_unicast` → `ipv4`, `unicast`) | `frrcfgd.py:2867` |
| 小文字正規化 | `.lower()` | `af_type` を小文字化してから split (大文字混在を吸収) | `frrcfgd.py:2867` |
| tbl_key キー | `admin_status` | `admin_status\|<af>` のディスパッチキーとして使用。address-family (ipv4/ipv6/l2vpn) を tbl_key に格納し key_map の `\|` サフィックス照合に利用 | `frrcfgd.py:2665-2668` |

### `maximum-prefix` 複合条件定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| アンカーフィールド | `max_prefix_limit` | `++` オプション連鎖のアンカー。このフィールドが存在しない場合、後続の `max_prefix_warning_threshold` / `max_prefix_restart_interval` / `max_prefix_warning_only` も投入されない | `frrcfgd.py:1901` |
| オプションフィールド 1 | `max_prefix_warning_threshold` | `++` (optional) で連鎖。不在時は threshold 引数なしで発行 | `frrcfgd.py:1901` |
| オプションフィールド 2 | `max_prefix_restart_interval` | `+` でアンカー化。`max_prefix_warning_only` と排他的に使用 | `frrcfgd.py:1902` |
| オプションフィールド 3 | `max_prefix_warning_only` | `&` で `max_prefix_restart_interval` とグループ化。`warning-only` キーワードを生成 | `frrcfgd.py:1902` |

### `hdl_send_com` 展開定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| reset コマンド | `no neighbor <pg> send-community all` | SET 開始時に既存の全 send-community 設定をリセット | `frrcfgd.py:hdl_send_com` |
| `none` 値 | 追加コマンドなし (reset のみ) | `send_community=none` の場合はリセット後に再設定コマンドを発行しない | `frrcfgd.py:hdl_send_com` |

## スキャン証跡

- `frrcfgd.py` L1895-1925 (`nbr_af_key_map` 全行)、L2112 (`BGP_PEER_GROUP_AF` → `nbr_af_key_map` ディスパッチ)、L2305 (handler 登録)、L2665-2668 (tbl_key / admin_status ディスパッチ)、L2865-2873 (`BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` runtime 分岐) を確認。
- 抽出件数: FRR コマンド literal 26 件 + vtysh prefix 3 件 + AF 文字列 4 件 + maximum-prefix 複合条件 4 件 + hdl_send_com 2 件 = 計 39 件。
