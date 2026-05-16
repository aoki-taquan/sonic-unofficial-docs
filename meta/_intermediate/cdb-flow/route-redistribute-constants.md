# ROUTE_REDISTRIBUTE — Phase E: ハードコード定数調査

## 調査対象ファイル

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.j2`

---

## ハードコード定数一覧

### key 構造 (frrcfgd.py L3150)

CONFIG_DB テーブルキーは `ROUTE_REDISTRIBUTE|<vrf>` 配下に `<src_proto>|<dst_proto>|<af>` の 3 フィールド構成。
frrcfgd は `key.split('|')` で `src_proto, dst_proto, af` の 3 値を取り出す。

### src_protocol enum 定数

frrcfgd が受け付ける `src_proto` の値。YANG enum および Jinja2 テンプレートと照合。

| 値 | FRR redistribute 対象 | 備考 | evidence |
|----|----------------------|------|---------|
| `connected` | 直接接続経路 | Jinja2 `redistribute_connected` (frrcfgd.py L1833) | frrcfgd.py L1833 |
| `static` | 静的経路 | bgpcfgd `enable_redistribution_command` で `redistribute static route-map STATIC_ROUTE_FILTER` 生成 | managers_static_rt.py L233 |
| `ospf` | OSPFv2 経路 | IPv4 の場合にそのまま `redistribute ospf` | frrcfgd.py L3151 |
| `ospf3` | OSPFv3 経路 (CONFIG_DB 値) | af=ipv6 のとき `ospf6` に変換して FRR へ渡す | frrcfgd.py L3151-3152 |
| `kernel` | カーネル経路 | FRR redistribute kernel | bgpd.conf.db.addr_family.j2 L69 |
| `bgp` | BGP 経路 | dst_protocol としても使用 | frrcfgd.py L3156 |

### dst_protocol enum 定数

frrcfgd L3156 に明示的なバリデーションがあり、`bgp` のみ許容。

| 値 | 許可 | evidence |
|----|------|---------|
| `bgp` | 許可 | frrcfgd.py L3156 |
| それ以外 | `log_err` で拒否・continue | frrcfgd.py L3157 |

### address_family enum 定数

key の第 3 フィールド `af` は次の 2 値。

| 値 | FRR address-family | evidence |
|----|-------------------|---------|
| `ipv4` | `address-family ipv4 unicast` | frrcfgd.py L3163 |
| `ipv6` | `address-family ipv6 unicast` | frrcfgd.py L3163 |

### ip_type ハードコード定数

`ip_type = 'unicast'` が frrcfgd.py L3153 でハードコードされており、`multicast` 等は選択不可。

| 定数 | 値 | evidence |
|------|-----|---------|
| `ip_type` | `"unicast"` | frrcfgd.py L3153 |

### ospf3→ospf6 変換ルール

af=`ipv6` かつ src_proto=`ospf3` の場合に FRR コマンド生成前に `ospf6` へ書き換える。
CONFIG_DB には `ospf3` と書くが、FRR vtysh には `ospf6` として送られる。

```python
# frrcfgd.py L3151-3152
if af == 'ipv6' and src_proto == 'ospf3':
    src_proto = 'ospf6'
```

### bgpcfgd static redistribution ハードコード定数 (managers_static_rt.py)

bgpcfgd は STATIC_ROUTE 追加/削除時に以下の FRR コマンドをハードコードで生成する。

| 定数 | 値 | evidence |
|------|-----|---------|
| route-map 名 | `"STATIC_ROUTE_FILTER"` | managers_static_rt.py L224,233,248,251 |
| route-map アクション | `permit` | managers_static_rt.py L224 |
| route-map シーケンス番号 | `10` | managers_static_rt.py L224 |
| address-family ループ | `["ipv4", "ipv6"]` | managers_static_rt.py L231,246 |

---

## 特記事項

1. **dst_protocol は `bgp` 固定** — frrcfgd は `bgp` 以外の dst_proto を `log_err` で拒否する。将来的に OSPF 間 redistribution などは別テーブルで扱う設計。
2. **ip_type は `unicast` 固定** — `multicast` SAFI は ROUTE_REDISTRIBUTE では扱わない。
3. **ospf3 は CONFIG_DB 上の論理名** — FRR に渡す際は af=ipv6 のときのみ `ospf6` へ変換される。af=ipv4 での `ospf3` は変換されないが、OSPFv3 は IPv6 専用なので実運用では発生しない。
4. **bgpcfgd の static redistribution** は STATIC_ROUTE テーブルの更新をトリガーに自動生成されるため、ROUTE_REDISTRIBUTE テーブルとは独立して動作する。

## evidence

- frrcfgd.py L97: `'ROUTE_REDISTRIBUTE': ['bgpd']` — daemon ルーティング
- frrcfgd.py L1833: `redistribute_connected` フィールド
- frrcfgd.py L1979-1980: `route_redist_key_map` 定義
- frrcfgd.py L3149-3168: ROUTE_REDISTRIBUTE ハンドラ本体
- managers_static_rt.py L221-252: `enable_redistribution_command` / `disable_redistribution_command`
- bgpd.conf.db.addr_family.j2 L64-76: redistribute Jinja2 ブロック
