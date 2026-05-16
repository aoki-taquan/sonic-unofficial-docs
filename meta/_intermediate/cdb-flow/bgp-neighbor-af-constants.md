# BGP_NEIGHBOR_AF — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## ハードコード定数一覧

### FRR コマンド literal（`nbr_af_key_map` 由来）

`frrcfgd.py:1895-1925` に定義された `nbr_af_key_map` が CONFIG_DB フィールドを FRR `vtysh` コマンド文字列へ変換する際、以下のキーワードがコード中にハードコードされている。

| 定数 / キーワード | FRR コマンド断片 | 対応 DB フィールド | ソース行 |
|---|---|---|---|
| `route-map {} in` | `neighbor <X> route-map <name> in` | `route_map_in` | `frrcfgd.py:1903` |
| `route-map {} out` | `neighbor <X> route-map <name> out` | `route_map_out` | `frrcfgd.py:1904` |
| `prefix-list {} in` | `neighbor <X> prefix-list <name> in` | `prefix_list_in` | `frrcfgd.py:1918` |
| `prefix-list {} out` | `neighbor <X> prefix-list <name> out` | `prefix_list_out` | `frrcfgd.py:1919` |
| `maximum-prefix {} {} {:restart}` | `neighbor <X> maximum-prefix <limit> [<threshold>] [restart <interval>]` | `max_prefix_limit` + 複合 | `frrcfgd.py:1902` |
| `weight {}` | `neighbor <X> weight <value>` | `weight` | `frrcfgd.py:1908` |
| `soft-reconfiguration inbound` | `neighbor <X> soft-reconfiguration inbound` | `soft_reconfiguration_in` | `frrcfgd.py:1905` |
| `unsuppress-map {}` | `neighbor <X> unsuppress-map <name>` | `unsuppress_map_name` | `frrcfgd.py:1906` |
| `default-originate route-map {}` | `neighbor <X> default-originate route-map <name>` | `default_rmap` | `frrcfgd.py:1900` |
| `capability orf prefix-list {}` | `neighbor <X> capability orf prefix-list <send\|receive\|both>` | `cap_orf` | `frrcfgd.py:1923` |

### address-family 文字列（ハンドラ分岐由来）

`frrcfgd.py:2865-2871` — `BGP_NEIGHBOR_AF` ハンドラが `key.split('|')` で `<nbr>|<afi_safi>` を分解し、`af_type.lower().split('_')` で `(af, ip_type)` に変換。その結果を `'address-family {} {}'.format(af, ip_type)` でリテラル合成して vtysh へ渡す。

| CONFIG_DB key 末尾 | FRR `address-family` 文字列 |
|---|---|
| `ipv4_unicast` | `address-family ipv4 unicast` |
| `ipv6_unicast` | `address-family ipv6 unicast` |
| `l2vpn_evpn` | `address-family l2vpn evpn` |

これらの文字列はコード中に定数変数として切り出されておらず、`'address-family {} {}'.format(af, ip_type)` という式そのものがハードコードされた変換規則である。

### `inbound` キーワード（soft-reconfiguration）

`soft_reconfiguration_in` フィールドの値が `true` のとき、FRR コマンド `neighbor <X> soft-reconfiguration inbound` の末尾キーワード `inbound` はコード中にリテラルとして埋め込まれる（`frrcfgd.py:1905`）。YANG / DB の値ではなくコードが決定する。

### `in` / `out` 方向指定

`route-map` / `prefix-list` の方向キーワード `in` / `out` は DB フィールド名（`route_map_in` / `route_map_out`）から類推されるが、実際には `frrcfgd.py:1903-1904, 1918-1919` のコマンドテンプレート文字列にリテラルとして記載されており、DB から動的に読み取られない。

---

## 特記事項

1. **`maximum-prefix` の複合引数** — `max_prefix_limit`・`max_prefix_warning_threshold`（省略時 75%）・`max_prefix_restart_interval`・`max_prefix_warning_only` の組み合わせが `nbr_af_key_map:1901-1902` の `++` / `+` プレフィックスルールで動的に決定される。FRR コマンド末尾の `{:restart}` フォーマット指定はコード内ハードコード。
2. **`route-map` / `prefix-list` 名は文字列参照** — CONFIG_DB / YANG では参照先の存在を強制しない。FRR 側で未定義名が渡されると bgpd が参照解決失敗するが、エラーはサイレント（vtysh は通る）。
3. **`unsuppress-map` / `default-originate route-map`** — FRR の `unsuppress-map` と `default-originate route-map` キーワードはコマンドテンプレートにハードコードされ、DB フィールド名（`unsuppress_map_name` / `default_rmap`）と異なる。
