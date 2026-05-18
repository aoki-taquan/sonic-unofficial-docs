# ROUTE_MAP_SET — Phase B 書込み順依存スキャンノート

対象テーブル: `ROUTE_MAP_SET`
Consumer: なし（frrcfgd・bgpcfgd・orchagent のいずれも非購読）
スキャン範囲:
- `sonic-route-map.yang:125-134, 269-273` — ROUTE_MAP_SET コンテナ定義と `call_route_map` leafref
- `sonic-bgp-common.yang:354-413` — BGP_NEIGHBOR_AF_LIST / BGP_PEER_GROUP_AF_LIST の `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` leafref
- `sonic-bgp-global.yang:373, 380, 502, 532` — BGP_GLOBALS_AF の route-map leafref
- `sonic-route-common.yang:60-66` — ROUTE_REDISTRIBUTE の `route_map` leafref

---

## 前提：ROUTE_MAP_SET は YANG leafref 整合性のためだけに存在する

`frrcfgd`・`bgpcfgd`・orchagent のいずれも `ROUTE_MAP_SET` テーブルを購読しない
（`frrcfgd.py` の `table_handler_list` および `tbl_to_key_map` に当テーブルが含まれないことを全行確認済み。
`bgpcfgd/main.py` の登録テーブル一覧にも不在）。

FRR 上の route-map 実体の作成は `ROUTE_MAP|<name>|<seq>` への書き込みが契機。
`ROUTE_MAP_SET` は YANG データモデル層で他テーブルからの leafref 参照先として機能する「名前空間登録」テーブル。

## 検出した順序依存

### 1. ROUTE_MAP_SET → 参照側テーブル（YANG strict mode のみ）

gNMI / NETCONF 等の YANG 検証が有効なパスでは、以下のテーブルのフィールドが
`ROUTE_MAP_SET_LIST/name` を leafref で参照しているため、**参照元エントリを書く前に `ROUTE_MAP_SET|<name>` が存在しなければ leafref 検証失敗**となる。

| 参照元テーブル | 参照フィールド | YANG ソース |
|---------------|---------------|-------------|
| `ROUTE_MAP` | `call_route_map` | `sonic-route-map.yang:269-273` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `default_rmap` | `sonic-bgp-common.yang:354-358` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_in` | `sonic-bgp-common.yang:385-392` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `route_map_out` | `sonic-bgp-common.yang:394-401` |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | `unsuppress_map_name` | `sonic-bgp-common.yang:408-413` |
| `BGP_GLOBALS_AF` | 各 route-map フィールド | `sonic-bgp-global.yang:373, 380, 502, 532` |
| `ROUTE_REDISTRIBUTE` | `route_map` | `sonic-route-common.yang:60-66` |

**書込み順**: `ROUTE_MAP_SET|<name>` → 参照元テーブルのフィールド設定

### 2. sonic-db-cli 直接書込みでは YANG 検証はバイパスされる

`sonic-db-cli CONFIG_DB HSET 'ROUTE_MAP_SET|ALLOW' name ALLOW` のような直接 Redis 操作は
YANG 検証をバイパスするため、`ROUTE_MAP_SET` エントリが存在しなくても参照元テーブルに書き込める。
この場合、FRR への反映は `ROUTE_MAP|<name>|<seq>` テーブルのみで決まり、`ROUTE_MAP_SET` の
存在有無は FRR 動作に影響しない。

**`sonic-db-cli` 運用では `ROUTE_MAP_SET` → 参照元テーブルの順序制約は実質なし。**

### 3. DEL 時の順序

`ROUTE_MAP_SET|<name>` を削除する場合、YANG strict mode では参照元テーブルが当該名前を
leafref で参照している間は削除できない（`must` / `when` 制約が適用されるかは実装依存）。
`sonic-db-cli` 直接操作では leafref 検証なしに削除可能だが、FRR 側の route-map は
`ROUTE_MAP` テーブルへの DEL イベントが届かない限り残り続ける。

## サマリ

| # | 依存関係 | 方向 | 有効なパス | 影響 |
|---|----------|------|-----------|------|
| 1 | `ROUTE_MAP_SET` → `ROUTE_MAP.call_route_map` | 先行必須 | gNMI/NETCONF | leafref 検証失敗 |
| 2 | `ROUTE_MAP_SET` → `BGP_NEIGHBOR_AF/BGP_PEER_GROUP_AF` の route-map フィールド | 先行必須 | gNMI/NETCONF | leafref 検証失敗 |
| 3 | `ROUTE_MAP_SET` → `BGP_GLOBALS_AF` の route-map フィールド | 先行必須 | gNMI/NETCONF | leafref 検証失敗 |
| 4 | `ROUTE_MAP_SET` → `ROUTE_REDISTRIBUTE.route_map` | 先行必須 | gNMI/NETCONF | leafref 検証失敗 |
| — | sonic-db-cli 直接投入 | 順序不問 | 直接 Redis | YANG 検証なし |
