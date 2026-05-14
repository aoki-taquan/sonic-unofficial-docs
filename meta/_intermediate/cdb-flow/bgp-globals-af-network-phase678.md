# BGP_GLOBALS_AF_NETWORK — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples / db_migrator.py / init_cfg.json.j2 に BGP_GLOBALS_AF_NETWORK への代入なし。REST/gNMI (sonic-mgmt-common) または CLI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### frrcfgd (sonic-frr-mgmt-framework) — bgp_table_handler_common

```python
# sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2319
('BGP_GLOBALS_AF_NETWORK', self.bgp_table_handler_common),
```

frrcfgd の `BgpdClientMgr` が BGP_GLOBALS_AF_NETWORK を **常時** 購読する。frrcfgd が有効な環境（sonic-frr-mgmt-framework がインストールされている場合）のみ動作。

### frrcfgd TABLE_DAEMON マッピング

```python
# frrcfgd.py:99
'BGP_GLOBALS_AF_NETWORK': ['bgpd'],
```

変更は bgpd デーモンにのみ配送される。

### frrcfgd テンプレート

```jinja2
{# bgpd.conf.db.addr_family.j2:32 #}
{% if BGP_GLOBALS_AF_NETWORK is defined and BGP_GLOBALS_AF_NETWORK|length > 0 %}
{% for af_nw_key, af_nw_val in BGP_GLOBALS_AF_NETWORK.items() %}
```

設定ファイル再生成時に BGP_GLOBALS_AF_NETWORK エントリが全展開される。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### frrcfgd — bgp_table_handler_common 経由 FRR push

`BGP_GLOBALS_AF_NETWORK` は `af_network_key_map` (L2119) で定義された key マッピングにより FRR `network` コマンドへ変換される。

```python
# frrcfgd.py:2119
'BGP_GLOBALS_AF_NETWORK': af_network_key_map,
```

boolean フィールドのみ（enum なし）の処理分岐:

| フィールド | FRR コマンド変換 |
|-----------|----------------|
| `policy=true` | `network <prefix> route-map <policy>` |
| `backdoor=true` | `network <prefix> backdoor` |
| フィールドなし | `network <prefix>` |

### VRF スコープ処理

```python
# frrcfgd.py:2139
vrf_tables = {'BGP_GLOBALS_AF_NETWORK', ...}
```

`BGP_GLOBALS_AF_NETWORK` は VRF スコープテーブルとして扱われる。キーに VRF 名が含まれる場合、当該 VRF の bgpd コンテキストでコマンドが発行される。VRF が存在しない場合は early return（VRF 解決待ち）。

### del_handler — network コマンド削除

SET の逆操作として `no network <prefix>` を FRR に push。`del_table=True` の場合はエントリ全削除。

<!-- /handler-branching -->
