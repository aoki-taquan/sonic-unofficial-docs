# BGP_GLOBALS_AF_AGGREGATE_ADDR — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples / db_migrator.py / init_cfg.json.j2 に BGP_GLOBALS_AF_AGGREGATE_ADDR への代入なし。REST/gNMI (sonic-mgmt-common) または CLI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### frrcfgd (sonic-frr-mgmt-framework) — bgp_table_handler_common

```python
# sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2318
('BGP_GLOBALS_AF_AGGREGATE_ADDR', self.bgp_table_handler_common),
```

frrcfgd の `BgpdClientMgr` が BGP_GLOBALS_AF_AGGREGATE_ADDR を **常時** 購読する。frrcfgd が有効な環境（sonic-frr-mgmt-framework がインストールされている場合）のみ動作。

### frrcfgd TABLE_DAEMON マッピング

```python
# frrcfgd.py:98
'BGP_GLOBALS_AF_AGGREGATE_ADDR': ['bgpd'],
```

変更は bgpd デーモンにのみ配送される。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### frrcfgd — bgp_table_handler_common 経由 FRR push

`BGP_GLOBALS_AF_AGGREGATE_ADDR` は `af_aggregate_key_map` (L2118) で定義された key マッピングにより FRR `aggregate-address` コマンドへ変換される。

```python
# frrcfgd.py:2118
'BGP_GLOBALS_AF_AGGREGATE_ADDR': af_aggregate_key_map,
```

boolean フィールドのみ（enum なし）の処理分岐:

| フィールド | FRR コマンド変換 |
|-----------|----------------|
| `as_set=true` | `aggregate-address <prefix> as-set` |
| `summary_only=true` | `aggregate-address <prefix> summary-only` |
| `as_set=false` | オプションなし |
| `summary_only=false` | オプションなし |

### VRF スコープ処理

```python
# frrcfgd.py:2139
vrf_tables = {'BGP_GLOBALS_AF_AGGREGATE_ADDR', ...}
```

`BGP_GLOBALS_AF_AGGREGATE_ADDR` は VRF スコープテーブルとして扱われる。キーに VRF 名が含まれる場合、当該 VRF の bgpd コンテキストでコマンドが発行される。VRF が存在しない場合 early return（VRF 解決待ち）。

<!-- /handler-branching -->
