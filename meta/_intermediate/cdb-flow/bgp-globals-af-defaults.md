# BGP_GLOBALS_AF — Phase A: コード由来の暗黙デフォルト

## 調査対象ファイル

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (3985 行)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.j2`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.evpn.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang`
- `sonic-frr/bgpd/bgp_damp.h` (FRR 実装デフォルト定数)

---

## per-field デフォルト一覧

### `max_ebgp_paths`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default (書き込み時) | `1` | `sonic-bgp-global.yang` L345 |
| 実行時 fallback (DB に key なし) | `1` — YANG default が CONFIG_DB に自動適用 | 同上 |
| FRR 実装 (コマンドなし時) | `1` — FRR 初期値 `maximum-paths 1` 相当 | FRR `bgpd/bgpd.c` |
| 乖離 | なし。YANG default = FRR 実装デフォルト = 1 | — |

### `max_ibgp_paths`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | `1` | `sonic-bgp-global.yang` L353 |
| 実行時 fallback | `1` | 同上 |
| FRR 実装 | `maximum-paths ibgp 1` | FRR |
| 乖離 | なし | — |

### `ibgp_equal_cluster_length`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional boolean) | `sonic-bgp-global.yang` L406 |
| 実行時 fallback (DB に key なし) | コマンド省略 → FRR デフォルト: cluster-list 長さ比較**なし** | `frrcfgd.py` global_af_key_map L1839 |
| frrcfgd 処理 | `+ibgp_equal_cluster_length` は optional (+) → 未設定なら `maximum-paths ibgp <n>` のみ発行、`equal-cluster-length` suffix なし | L1839 / L813 |
| 乖離 | なし (省略 = 機能無効) | — |

### `import_vrf`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional) | `sonic-bgp-global.yang` L356 |
| 実行時 fallback | 省略 → VRF import 無効 | frrcfgd key_map L1862 |
| 乖離 | なし | — |

### `import_vrf_route_map`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし | L371 |
| 実行時 fallback | 省略 → route-map フィルタなし | L1863 |
| 乖離 | なし | — |

### `route_download_filter`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし | L378 |
| 実行時 fallback | 省略 → `table-map` コマンドなし → FIB に全 prefix download | L1840 |
| 乖離 | なし | — |

### `ebgp_route_distance` / `ibgp_route_distance` / `local_route_distance`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (3 フィールドともオプション) | L385-404 |
| 実行時 fallback (一部のみ設定) | **3 フィールドが揃わない場合 frrcfgd は `distance bgp` コマンドを発行しない** — comb_attr_list 制約により、不揃いの場合は全フィールドを data から pop して処理スキップ | `frrcfgd.py` L3939 `bgp_af_handler`, L3886-3888 |
| FRR 実装デフォルト (コマンドなし) | eBGP=20、iBGP=200、local=200 (FRR ハードコード初期値) | FRR `bgpd/bgpd.c bgp_distance_reset()` |
| **書き込み vs 実行時の乖離** | 3 フィールド中 1〜2 個だけ CONFIG_DB に書き込んでも FRR には反映されない。3 つ全て設定して初めて有効 | frrcfgd.py L3939 comb_attr_list |
| Jinja2 テンプレート (init_cfg) | 同様に 3 フィールド揃いチェック L19-21 | `bgpd.conf.db.addr_family.j2` |

### `route_flap_dampen`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional boolean) | L412 |
| YANG must 制約 | `afi_safi = 'ipv4_unicast'` 限定。他の AFI は YANG 検証段階で拒否 | L413 |
| 実行時 fallback | 省略 → dampening 無効 (FRR デフォルト) | frrcfgd L1841 `['true','false']` |

### `route_flap_dampen_half_life`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional uint8 1..45) | L418 |
| frrcfgd 処理 | `+route_flap_dampen_half_life` — optional。`route_flap_dampen=true` 時に DB 未設定なら dampening コマンドの引数が空 → FRR 側デフォルト使用 | frrcfgd L1842 |
| FRR 実装デフォルト | **15 分** (`DEFAULT_HALF_LIFE 15` × 60 秒 = 900s) | `sonic-frr/bgpd/bgp_damp.h` L123 |
| **乖離** | DB に `route_flap_dampen=true` のみ設定した場合、frrcfgd は `bgp dampening` を引数なしで発行 → FRR がデフォルト値 (half_life=15min, reuse=750, suppress=2000, max_suppress=60min) を適用。ドキュメントには YANG range 1..45 しか書かれていないが、暗黙 FRR デフォルト値が存在する | — |

### `route_flap_dampen_reuse_threshold` / `route_flap_dampen_suppress_threshold` / `route_flap_dampen_max_suppress`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (全 optional) | L426-448 |
| **comb_attr_list 制約** | `bgp_af_handler` の `comb_attr_list` 第 2 要素: `{'route_flap_dampen_reuse_threshold', 'route_flap_dampen_suppress_threshold', 'route_flap_dampen_max_suppress'}` — 3 フィールドが揃わない場合、3 つとも data から pop → FRR コマンドに引数なし | `frrcfgd.py` L3939-3940 |
| FRR 実装デフォルト (引数なし時) | reuse=**750**、suppress=**2000**、max_suppress=**4 × half_life** | `bgp_damp.h` L124-L125 (DEFAULT_REUSE, DEFAULT_SUPPRESS)、`bgp_damp.c` L514 |
| **書き込み vs 実行時の乖離** | 3 つ全て揃えないとまとめて無視される。例: `reuse_threshold` だけ設定しても反映されない。FRR には引数なしの `bgp dampening` が届き、FRR デフォルト値が使われる | — |
| Jinja2 テンプレート | 4 フィールドの連鎖 if: half_life → reuse → suppress → max_suppress の順に存在チェック。1 つでも欠けると以降の引数が省略される (L104-115) | `bgpd.conf.db.addr_family.j2` L104-116 |

### `autort`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional enum, 唯一値 `rfc8365-compatible`) | L450 |
| 実行時 fallback | 省略 → FRR `autort` コマンドなし → route-target 自動生成無効 | L1853 |
| frrcfgd 変換 | `hdl_enum_conversion` が `_` → `-` 変換。`rfc8365_compatible` → `rfc8365-compatible` | L1393 |
| 乖離 | なし。省略 = 無効 | — |

### `advertise-all-vni`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional boolean) | L457 |
| 実行時 fallback | 省略 → `advertise-all-vni` コマンドなし → VNI 広告なし | L1846 / evpn.j2 L1 |
| 乖離 | なし。省略 = 無効 (l2vpn_evpn AF で必要なら明示設定必須) | — |

### `advertise-svi-ip`

| 区分 | 値 | ソース |
|------|----|--------|
| YANG default | なし (optional boolean) | L462 |
| 実行時 fallback | 省略 → コマンドなし → SVI IP 広告無効 | L1847 / evpn.j2 L4 |
| 乖離 | なし | — |

---

## global_af_key_map に含まれる追加フィールド (YANG 未記載、ドキュメント未掲載)

以下のフィールドは `global_af_key_map` (frrcfgd L1824-1864) に存在するが、YANG に定義がない、
または現在のドキュメントテーブルに掲載されていない:

| フィールド | FRR コマンド |
|-----------|-------------|
| `rd_vpn_export` | `rd vpn export` |
| `rt_vpn_export` | `rt vpn export` |
| `rt_vpn_import` | `rt vpn import` |
| `rt_vpn_both` | `rt vpn both` |
| `export_vpn` | `export vpn` |
| `import_vpn` | `import vpn` |
| `redistribute_connected` | `redistribute connected` |
| `redistribute_static_rmap` | `redistribute static route-map` |
| `rmap_vpn_export` | `route-map vpn export` |
| `rmap_vpn_import` | `route-map vpn import` |
| `advertise-default-gw` | `advertise-default-gw` |
| `advertise-ipv4-unicast` | `advertise ipv4 unicast` |
| `advertise-ipv6-unicast` | `advertise ipv6 unicast` |
| `default-originate-ipv4` | `default-originate ipv4` |
| `default-originate-ipv6` | `default-originate ipv6` |
| `flooding` | `flooding` |
| `dad-enabled` | `dup-addr-detection` |
| `dad-max-moves` / `dad-time` | `dup-addr-detection max-moves {} time {}` |
| `dad-freeze` | `dup-addr-detection freeze` |
| `route-distinguisher` | `rd` |
| `import-rts` | `route-target import` |
| `export-rts` | `route-target export` |

これらは全て optional で未設定 fallback = FRR コマンドなし (機能無効)。

---

## 書き込み時 default vs 実行時 fallback の乖離まとめ

| フィールド | 乖離の種類 | 説明 |
|-----------|-----------|------|
| `ebgp_route_distance` / `ibgp_route_distance` / `local_route_distance` | **部分設定無視** | 3 フィールドが揃わないと frrcfgd がコマンドを生成しない。FRR は自身のデフォルト (eBGP=20, iBGP=200, local=200) を維持する |
| `route_flap_dampen_reuse_threshold` / `_suppress_threshold` / `_max_suppress` | **部分設定無視** | 3 フィールドが揃わないと frrcfgd が引数なしで `bgp dampening` を発行 → FRR デフォルト (reuse=750, suppress=2000, max_suppress=4×half_life) が使われる |
| `route_flap_dampen_half_life` | **暗黙 FRR デフォルト** | 設定しても他 3 フィールドが不揃いなら無視。`route_flap_dampen=true` のみの場合 FRR が half_life=15min を適用 |
| `max_ebgp_paths` / `max_ibgp_paths` | 乖離なし | YANG default=1 = FRR デフォルト |
| boolean 系 (`advertise-all-vni`, `advertise-svi-ip`, etc.) | 乖離なし | 省略 = 機能無効 |
