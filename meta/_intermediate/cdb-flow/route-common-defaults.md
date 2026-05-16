# route-common-defaults — Phase A 調査メモ

対象テーブル: `ROUTE_REDISTRIBUTE`  
ファイル: `docs/reference/config-db/route-common.md`  
日付: 2026-05-14

## ソース調査結果

### YANG 定義
`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-common.yang` (ref: 9ea932ec)

```
ROUTE_REDISTRIBUTE|<vrf_name>|<src_protocol>|<dst_protocol>|<addr_family>

フィールド:
- vrf_name      : string (key) — "default" or VRF leafref
- src_protocol  : string (key)
- dst_protocol  : string (key)
- addr_family   : string (key)
- route_map     : leaf-list (max-elements 1) — optional
- metric        : uint32 — optional
```

### HLD 定義
`SONiC/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md` §3.2.1.11

```
src_protocol = "connected" / "static" / "ospf" / "ospf3"
dst_protocol = "bgp"
addr_family  = "ipv4" / "ipv6"
route_map    = 1*64VCHAR  (optional)
metric       = 1*10DIGIT  (optional)
```

### frrcfgd.py ハンドラ
`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (ref: 9ea932ec)

`route_redist_key_map` (L1979):
```python
[(['protocol', '++metric', '+route_map'],
  '{no:no-prefix}redistribute {} {:redist-metric} {:redist-route-map}',
  hdl_route_redist_set)]
```

- `++metric` = optional, defaults to absent (no metric in FRR command)
- `+route_map` = optional, defaults to absent (no route-map in FRR command)

`hdl_route_redist_set` (L1330): `OP_DELETE` 時はまず `no redistribute <proto>` を発行してリセット。

`redist-metric` フォーマット (L916): `metric` フィールドが空文字なら空文字列を返す → FRR コマンドに metric 句なし。
`redist-route-map` フォーマット (L913): `route_map` フィールドが空文字なら空文字列を返す → FRR コマンドに route-map 句なし。

### デフォルト値まとめ

| フィールド | 型 | 既定値 | コード由来 |
|-----------|-----|--------|-----------|
| `vrf_name` | string (key) | — | YANG key (必須) |
| `src_protocol` | string (key) | — | YANG key (必須) |
| `dst_protocol` | string (key) | — | YANG key (必須) |
| `addr_family` | string (key) | — | YANG key (必須) |
| `route_map` | leaf-list string | 省略可 (absent) | YANG optional, frrcfgd L1979 `+route_map` |
| `metric` | uint32 | 省略可 (absent) | YANG optional, frrcfgd L1979 `++metric` |

### テスト設定例 (sample_config_db.json)
```json
"ROUTE_REDISTRIBUTE": {
    "default|connected|bgp|ipv4": {}
}
```
→ `metric` も `route_map` も省略可能（フィールドなしで有効）。

### 制約
- `dst_protocol` は現状 `bgp` のみ (frrcfgd L3156: `if dst_protocol != 'bgp': skip`)
- `route_map` は最大 1 エントリ (YANG max-elements 1)
- IPv6 で `src_protocol=ospf3` の場合 FRR 内部では `ospf6` に変換 (frrcfgd L3151)
