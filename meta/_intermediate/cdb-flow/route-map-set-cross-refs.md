# ROUTE_MAP_SET — Phase C 暗黙参照テーブル スキャンノート

対象テーブル: `ROUTE_MAP_SET`
スキャン範囲: `sonic-route-map.yang`, `sonic-bgp-common.yang`, `sonic-bgp-global.yang`, `sonic-route-common.yang`, `frrcfgd.py`

---

## ROUTE_MAP_SET 自身の参照先

なし。ROUTE_MAP_SET は `name` (key) のみを持つ名前レジストリで、他テーブルを leafref で参照するフィールドは一切存在しない。

---

## ROUTE_MAP_SET を参照するテーブル（被参照側）

YANG leafref `path "/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name"` を含む箇所を全ファイルスキャン。

### sonic-route-map.yang

| テーブル | 参照フィールド | 行 |
|---------|--------------|-----|
| `ROUTE_MAP` | `call_route_map` | L269-273 |

### sonic-bgp-common.yang

| テーブル | 参照フィールド | 行 |
|---------|--------------|-----|
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `default_rmap` | L354-358 |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_in` | L385-392 |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_out` | L394-401 |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `unsuppress_map_name` | L408-413 |

### sonic-bgp-global.yang

| テーブル | 参照フィールド | 行 |
|---------|--------------|-----|
| `BGP_GLOBALS_AF` | `import_vrf_route_map` | L371-374 |
| `BGP_GLOBALS_AF` | `route_download_filter` | L378-382 |
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` | `policy` | L500-505 |
| `BGP_GLOBALS_AF_NETWORK` | `policy` | L530-534 |

### sonic-route-common.yang

| テーブル | 参照フィールド | 行 |
|---------|--------------|-----|
| `ROUTE_REDISTRIBUTE` | `route_map` (leaf-list) | L60-66 |

---

## frrcfgd 実装上の参照

- `frrcfgd.py` は `ROUTE_MAP_SET` を直接購読しない（`table_handler_list` に含まれない）。
- `ROUTE_MAP.call_route_map` は `route_map_key_map` L1942 に `'call_route_map': 'call {:enable-only}'` として定義されており、frrcfgd が FRR に `call <name>` コマンドを発行する。
- `BGP_NEIGHBOR_AF` の `route_map_in` / `route_map_out` は frrcfgd の `bgp_table_handler_common` が `neighbor <peer> route-map <name> in/out` に変換する。
- `BGP_GLOBALS_AF` の `route_download_filter` は frrcfgd が FRR bgpd に `table-map <name>` として発行する。
- これらはすべて ROUTE_MAP_SET の name を FRR に文字列として渡すだけであり、ROUTE_MAP_SET エントリの存在を frrcfgd が実行時にチェックするコードは存在しない。

---

## サマリ

| 参照先テーブル / リソース | 参照方向 | 参照フィールド | 条件・備考 |
|--------------------------|---------|--------------|-----------|
| — | — | — | ROUTE_MAP_SET 自身は他テーブルを参照しない（name レジストリのみ） |
| `ROUTE_MAP` | 被参照（逆参照）| `call_route_map` | YANG leafref。frrcfgd は FRR に `call <name>` を発行。FRR 側で call 先未定義時は素通り |
| `BGP_NEIGHBOR_AF` | 被参照（逆参照）| `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` | YANG leafref。frrcfgd が `neighbor {} route-map {} in/out` に変換 |
| `BGP_PEER_GROUP_AF` | 被参照（逆参照）| `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` | YANG leafref。sonic-bgp-common.yang を BGP_NEIGHBOR_AF と共有 |
| `BGP_GLOBALS_AF` | 被参照（逆参照）| `import_vrf_route_map`, `route_download_filter` | YANG leafref。frrcfgd が `vrf import` / `table-map` に変換 |
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` | 被参照（逆参照）| `policy` | YANG leafref。BGP aggregate-address に route-map を適用 |
| `BGP_GLOBALS_AF_NETWORK` | 被参照（逆参照）| `policy` | YANG leafref。BGP network コマンドに route-map を適用 |
| `ROUTE_REDISTRIBUTE` | 被参照（逆参照）| `route_map` (leaf-list) | YANG leafref。frrcfgd が redistribute コマンドに route-map を付与 |
