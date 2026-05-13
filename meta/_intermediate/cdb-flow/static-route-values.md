# STATIC_ROUTE — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

VRF-aware 形式:
- `vrf_name` (key): `default` / `mgmt` / `Vrf...`
- `prefix` (key): IPv4/IPv6 CIDR
- `nexthop`: カンマ区切り IP 文字列。デフォルト `0.0.0.0`（interface route 向け）
- `ifname`: カンマ区切り interface 名文字列
- `advertise`: カンマ区切り boolean 文字列。デフォルト `false`
- `bfd`: カンマ区切り boolean 文字列（template 形式のみ）
- `distance`: カンマ区切り uint8 文字列 (0..255)。デフォルト `0`
- `nexthop-vrf`: カンマ区切り VRF 文字列
- `blackhole`: カンマ区切り boolean 文字列。デフォルト `false`

## Phase 2: per-value 挙動

### `advertise` 値別挙動
| 値 | 挙動 |
|----|------|
| `false` | BGP 広告なし（デフォルト）。`ROUTE_ADVERTISE_DISABLE_TAG` を付与。 |
| `true` | BGP に経路広告。`ROUTE_ADVERTISE_ENABLE_TAG` を付与。 |

### `bfd` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | `staticroutebfd` が BFD セッションを監視。全セッション down で APPL_DB から経路削除。bgpcfgd の StaticRouteMgr は処理をスキップ（staticroutebfd 側が担う）。 |
| `false` | BFD 監視なし（デフォルト）。bgpcfgd が通常処理。 |

### `blackhole` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | blackhole route（パケット破棄）。nexthop / ifname は不要。FRR に `blackhole` で展開。 |
| `false` | 通常経路（デフォルト）。nexthop が必要。 |

### `distance` 値別挙動
| 値 | 挙動 |
|----|------|
| `0` | デフォルト AD（FRR はデフォルト static AD = 1 を使用）。 |
| 1..255 | 指定の AD で FRR 経路テーブルに挿入。小さいほど優先。 |

## Phase 3: ソース確認

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py:40-46`: `blackhole` / `distance` / `nexthop-vrf` / `bfd` / `advertise` を data dict から読み出し。
- `managers_static_rt.py:46`: `data['advertise'] == "false"` なら `ROUTE_ADVERTISE_DISABLE_TAG`、else `ROUTE_ADVERTISE_ENABLE_TAG`。
- `managers_static_rt.py:49`: `bfd_enable[0].lower() == "true"` で bfd 判定。
- BFD 全断時: `StaticRouteMgr.skip_appl_del()` で CONFIG_DB に経路が残り bfd=true なら削除スキップ。

## enum 有無

- `advertise` / `bfd` / `blackhole`: enum なし（カンマ区切り boolean 文字列）
- `distance`: enum なし（数値文字列）
- `vrf_name`: enum なし（文字列パターン制約）
