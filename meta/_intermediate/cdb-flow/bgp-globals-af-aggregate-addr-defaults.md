# BGP_GLOBALS_AF_AGGREGATE_ADDR — Phase A: コード由来の暗黙デフォルト調査

## 対象ファイル

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/templates/bgpd/bgpd.conf.db.addr_family.j2`

## フィールド列挙（YANG より）

| フィールド | YANG type | YANG default 宣言 |
|-----------|-----------|-------------------|
| `as_set` | boolean | なし |
| `summary_only` | boolean | なし |
| `policy` | leafref → ROUTE_MAP_SET.name | なし |

YANG `sonic-bgp-global.yang` の `BGP_GLOBALS_AF_AGGREGATE_ADDR_LIST` 内 3 フィールドいずれも `default` 文なし。

## コード由来の暗黙デフォルト

### `as_set`

**YANG デフォルト**: 未宣言

**frrcfgd.py 実行時デフォルト**:
- `AggregateAddr.__init__()` (L1703-1705) で `self.as_set = False` に初期化。
- L3190-3192: フィールドが存在しないか `"true"` でない場合は `setattr` されず → `False` のまま。
- `CommandArgument.__format__` の `bool_format` (L815): `'aggr-as-set': 'as-set'`。
  値が `"false"` または空 → FRR コマンドに `as-set` キーワード**なし**。
- **暗黙デフォルト: `false`（FRR コマンドに `as-set` 未追加）**

**書き込み時 vs 実行時**: フィールドを省略した場合もキャッシュ `aggr_obj.as_set = False` に落ちるため一貫している。

### `summary_only`

**YANG デフォルト**: 未宣言

**frrcfgd.py 実行時デフォルト**:
- `AggregateAddr.__init__()` で `self.summary_only = False` に初期化（L1705）。
- `af_aggregate_key_map` (L1982): `'++summary_only'`（`++` = optional フィールド）。
  フィールドが欠如していると `cmd_data` に空文字列 `''` が渡る。
- `bool_format['aggr-summary-only'] = 'summary-only'`（L816）。
  値 `"false"` または空 → FRR コマンドに `summary-only` キーワード**なし**。
- **暗黙デフォルト: `false`（FRR コマンドに `summary-only` 未追加）**

### `policy`

**YANG デフォルト**: 未宣言

**frrcfgd.py 実行時デフォルト**:
- `af_aggregate_key_map` (L1982): `'+policy'`（`+` = optional フィールド）。
  フィールドが欠如していると `cmd_data` に空文字列 `''` が渡る。
- `aggr-policy` format (L928-930): 値が空 → `'route-map '` プレフィックス付加なし、空文字列のまま。
- FRR コマンドに `route-map` 指定**なし**。
- **暗黙デフォルト: 空（route-map 未指定）**

## `++` vs `+` の意味（frrcfgd.py L674-688）

- `++<field>`: optional かつ `opt_idx_list` に追加。欠如時はコマンド末尾で `''` 補完。
- `+<field>`: optional。欠如時も `''` で補完するが、`opt_idx_list` 対象外のため削除判定が若干異なる。
- `<field>`（プレフィックスなし）: mandatory。欠如するとコマンド実行をスキップ。

`ip_prefix` は mandatory、`as_set`/`summary_only` は `++`（optional + opt_idx_list）、`policy` は `+`（optional のみ）。

## Jinja2 テンプレート経路（bgpcfgd テンプレパス）との乖離

`bgpd.conf.db.addr_family.j2` (L48-61) の aggregate-address 生成:

```jinja2
{% if 'as_set' in af_ag_val and af_ag_val['as_set'] == 'true' %}
{% set af_ag_ns.ag_end = 'as-set ' %}
{% endif %}
{% if 'summary_only' in af_ag_val and af_ag_val['summary_only'] == 'true' %}
{% set af_ag_ns.ag_end = af_ag_ns.ag_end + 'summary-only' %}
{% endif %}
  aggregate-address {{af_ag_key[2]}} {{af_ag_ns.ag_end}}
```

**Discrepancy 発見**: Jinja2 テンプレート経路は `policy` フィールドを**完全に無視**している。
`frrcfgd.py` 経路（frr-mgmt-framework）は `policy` を `route-map <name>` として反映するが、
テンプレート経路（bgpcfgd）は `BGP_GLOBALS_AF_AGGREGATE_ADDR` の `policy` を読まない。

ただし通常、`BGP_GLOBALS_AF_AGGREGATE_ADDR` は frr-mgmt-framework 経路でのみ使用され、
bgpcfgd テンプレート経路は `BGP_AGGREGATE_ADDRESS` テーブルを使う設計のため、
実運用では両経路が同じエントリを参照することは想定外。

## 初期化ロード時のデフォルト（起動時）

`BGPConfigDaemon.__init__` (L2256-2268):
```python
self.af_aggr_list = {}
af_aggr_table = self.config_db.get_table('BGP_GLOBALS_AF_AGGREGATE_ADDR')
for key, entry in af_aggr_table.items():
    ...
    aggr_obj = AggregateAddr()
    for k, v in entry.items():
        if v == 'true':
            setattr(aggr_obj, k, True)
    self.af_aggr_list.setdefault(vrf, {})[norm_ip_pfx] = aggr_obj
```

- CONFIG_DB に `as_set`/`summary_only` フィールドが存在しない場合は `AggregateAddr()` の初期値 `False` が使われる。
- `policy` は内部キャッシュ(`af_aggr_list`)に格納されない（`AggregateAddr` クラスに属性なし）。
  FRR コマンド生成は `run_command` 経由で data から直接取得するため、内部キャッシュとは別管理。

## まとめ

| フィールド | YANG default | 実装 fallback | frrcfgd FRR 出力 | Jinja2 テンプレ |
|-----------|-------------|--------------|----------------|---------------|
| `as_set` | なし | `False` (AggregateAddr.__init__) | キーワードなし | `as-set`（`true`時のみ）、policy なし |
| `summary_only` | なし | `False` (AggregateAddr.__init__) | キーワードなし | `summary-only`（`true`時のみ）、policy なし |
| `policy` | なし | 空文字列 (`+` optional) | `route-map <name>`（値あり時） | **無視** ← Discrepancy |
