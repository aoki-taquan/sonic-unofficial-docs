# PREFIX_SET — Phase C 暗黙参照テーブルスキャンノート

対象テーブル: `PREFIX_SET`
スキャン対象:
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-routing-policy-sets.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## PREFIX_SET が参照するテーブル（参照元）

### 1. PREFIX (PREFIX_LIST / PREFIX_NOSEQ_LIST) — leafref（必須）

- `sonic-routing-policy-sets.yang:43-44`: `PREFIX/PREFIX_LIST/set_name` は `../../../PREFIX_SET/PREFIX_SET_LIST/name` を leafref。
- `sonic-routing-policy-sets.yang:44` (PREFIX_NOSEQ_LIST): 同様。
- PREFIX_SET が先に存在しないと YANG バリデーションでロード拒否。

## PREFIX_SET を参照するテーブル（被参照 / 逆参照）

### 2. ROUTE_MAP — leafref (match_prefix_set, match_ipv6_prefix_set, match_next_hop_set)

- `sonic-route-map.yang:163-165`: `ROUTE_MAP.match_prefix_set` が `PREFIX_SET.PREFIX_SET_LIST.name` を leafref。
- `sonic-route-map.yang:171-173`: `ROUTE_MAP.match_ipv6_prefix_set` が同上 leafref（frrcfgd の `route_map_key_map` に未実装エントリ → dead field）。
- `sonic-route-map.yang:185-186`: `ROUTE_MAP.match_next_hop_set` が同上 leafref。
- frrcfgd は `match_prefix_set` / `match_next_hop_set` 処理時に `prefix_set_list` から AF（IPv4/IPv6）を動的参照（`frrcfgd.py:2669-2676`）。PREFIX_SET 未作成時は AF 不明で FRR コマンド未発行（silent drop）。

### 3. BGP_NEIGHBOR_AF / BGP_PEER_GROUP_AF — leafref (prefix_list_in, prefix_list_out)

- `sonic-bgp-common.yang:481-483`: `prefix_list_in` が `PREFIX_SET.PREFIX_SET_LIST.name` を leafref。
- `sonic-bgp-common.yang:488-490`: `prefix_list_out` が同上 leafref。
- frrcfgd: `frrcfgd.py:1918-1919` で `neighbor {} prefix-list {} in/out` コマンドとして FRR に発行。
- BGP ネイバー設定で prefix filter として直接参照される経路（ROUTE_MAP を介さない）。

---

## 参照方向サマリ

| 参照先テーブル / リソース | 参照方向 | 参照フィールド | 条件・備考 |
|--------------------------|---------|--------------|-----------|
| `PREFIX` (`PREFIX_LIST` / `PREFIX_NOSEQ_LIST`) | leafref ターゲット（被参照） | `set_name` | PREFIX_SET 先行必須。未作成時 YANG ロード拒否 |
| `ROUTE_MAP` | 逆参照（ROUTE_MAP が PREFIX_SET を leafref） | `match_prefix_set`, `match_next_hop_set` | PREFIX_SET 未作成時 frrcfgd が AF 解決失敗 → FRR コマンド未発行 |
| `ROUTE_MAP` | 逆参照（YANG のみ） | `match_ipv6_prefix_set` | frrcfgd 未実装 → dead field |
| `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` | 逆参照（BGP neighbor が PREFIX_SET を leafref） | `prefix_list_in`, `prefix_list_out` | `neighbor {} prefix-list {} in/out` として FRR に発行 |

## 証跡

- `sonic-routing-policy-sets.yang:43-44` — PREFIX_LIST.set_name leafref
- `sonic-route-map.yang:163-186` — ROUTE_MAP leafref 定義
- `sonic-bgp-common.yang:481-490` — BGP_NEIGHBOR/PEER_GROUP_AF の prefix_list_in/out leafref
- `frrcfgd.py:2669-2676` — ROUTE_MAP 処理時の prefix_set_list 参照
- `frrcfgd.py:1918-1919` — prefix_list_in/out FRR コマンドテンプレート
