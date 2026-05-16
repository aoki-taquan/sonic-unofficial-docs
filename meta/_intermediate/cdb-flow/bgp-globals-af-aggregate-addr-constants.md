# bgp-globals-af-aggregate-addr — Phase E ハードコード定数調査

対象ハンドラ: `frrcfgd.py` (`hdl_af_aggregate`, `af_aggregate_key_map`, `MatchPrefix.normalize_ip_prefix`, `bgp_table_handler_common` の `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐)

## 抽出した定数

### FRR コマンド literal (`af_aggregate_key_map` / `__format__`)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| aggregate-address コマンド雛形 | `'{no:no-prefix}aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}'` | vtysh `address-family <afi> <safi>` 配下に投入する FRR コマンド文字列 | `frrcfgd.py:1982-1983` |
| `aggr-as-set` 展開 | `'as-set'` | `as_set=true` のときに付与されるキーワード | `frrcfgd.py:815` |
| `aggr-summary-only` 展開 | `'summary-only'` | `summary_only=true` のときに付与されるキーワード | `frrcfgd.py:816` |
| `aggr-policy` 展開 | `'route-map %s'` | `policy` フィールドが非空のとき prefix される文字列 | `frrcfgd.py:928-930` |
| vtysh prefix L1 | `'configure terminal'` | コマンド投入時の先頭行 | `frrcfgd.py:3179` |
| vtysh prefix L2 | `'router bgp {} vrf {}'` | BGP インスタンス選択 (`local_asn` と `vrf` を埋め込み) | `frrcfgd.py:3180` |
| vtysh prefix L3 | `'address-family {} {}'` | `afi`/`safi` を埋め込んで AF コンテキストに入る | `frrcfgd.py:3181` |
| 登録テーブル名 | `'BGP_GLOBALS_AF_AGGREGATE_ADDR'` | `bgp_table_handler_common` の dispatch / table_subscribe 対象 | `frrcfgd.py:98, 2118, 2139, 2317` |

### prefix 正規化定数 (`MatchPrefix`)

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `MatchPrefix.IPV4_MAXLEN` | `32` | `/` が無い IPv4 prefix に補う host mask 長 | `frrcfgd.py:1606` |
| `MatchPrefix.IPV6_MAXLEN` | `128` | `/` が無い IPv6 prefix に補う host mask 長 | `frrcfgd.py:1607` |
| `af` 判定リテラル | `'ipv4'` / `'ipv6'` | key の `<afi_safi>` を `_` で分割した左側を小文字比較し `socket.AF_INET` / `AF_INET6` を選択 | `frrcfgd.py:2261, 3171-3172` |
| 正規化フォーマット | `'%s/%d'` | `inet_ntop()` の結果と `mask_len` を連結 | `frrcfgd.py:1614, 1621` |

### ハンドラ内ガード値

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `hdl_af_aggregate` 最小引数数 | `5` | `len(args) < 5` で `None` 返却 (キーマップが期待する 6 個目以降のスロットが揃っていないと dispatch をスキップ) | `frrcfgd.py:1314` |
| boolean 真値リテラル | `'true'` | `data[attr].data == 'true'` 比較で `as_set` / `summary_only` を内部 `AggregateAddr` に反映 | `frrcfgd.py:3191` |
| 内部状態属性名 | `as_set`, `summary_only` | `AggregateAddr` インスタンス属性。初期値 `False` | `frrcfgd.py:1704-1705, 3190` |

### 経路スイッチ

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `DEVICE_METADATA.frr_mgmt_framework_config` 条件 | `True` | 本テーブルが有効化される前提 (false の場合は bgpcfgd テンプレ経路で `BGP_AGGREGATE_ADDRESS` 側が動く) | (本ページ既述、`device_metadata` 経由) |

## スキャン証跡

- `frrcfgd.py` L98 (handler registration), L800-830 (`__format__` boolean リテラル表), L920-944 (`aggr-policy`), L1313-1328 (`hdl_af_aggregate`), L1600-1640 (`MatchPrefix.normalize_ip_prefix` / `IPV4_MAXLEN` / `IPV6_MAXLEN`), L1700-1710 (`AggregateAddr` 初期値), L1982-1983 (key_map), L2118 (table → key_map dispatch), L2139, L2256-2270 (init reload), L2317 (table_subscribe), L3169-3197 (runtime handler) を確認。
- 抽出件数: コマンド literal 8 件 + prefix 正規化 4 件 + ガード値 3 件 + 経路スイッチ 1 件 = 16 件。
