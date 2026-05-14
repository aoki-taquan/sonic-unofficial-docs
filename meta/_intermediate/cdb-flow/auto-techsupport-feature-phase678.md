# AUTO_TECHSUPPORT_FEATURE — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### init_cfg.json.j2 — FEATURE エントリ一括生成

```jinja2
{# sonic-buildimage/files/build_templates/init_cfg.json.j2:141 #}
"AUTO_TECHSUPPORT_FEATURE": {
{%- for feature, _, _, _ in features %}
    "{{feature}}": {
{%- if enable_auto_tech_support == "y" %}
        "state" : "enabled", {% else %}
        "state" : "disabled", {% endif %}
        "rate_limit_interval" : "600",
        "available_mem_threshold": "10.0"
    }{%if not loop.last %},{% endif -%}
{% endfor %}
},
```

`features` リスト（bgp, database, pmon, swss, syncd, lldp, snmp, dhcp_relay 等）の各フィーチャーに対して、`enable_auto_tech_support` フラグに基づき `state` が自動派生代入される。`rate_limit_interval=600` / `available_mem_threshold=10.0` は固定値。

### sonic_package_manager — パッケージ追加時の自動代入

```python
# sonic-utilities/sonic_package_manager/service_creator/feature.py:186
def_cfg = DEFAULT_AUTO_TS_FEATURE_CONFIG.copy()
(auto_ts_add_cfg, auto_ts_state) = self.infer_auto_ts_capability(init_cfg_conn)
def_cfg['state'] = auto_ts_state
if not auto_ts_add_cfg:
    return False
conn.set_entry(AUTO_TS_FEATURE, new_name, new_cfg)
```

新しいパッケージ（フィーチャー）がインストールされると `AUTO_TECHSUPPORT|GLOBAL` の `state` を参照して新エントリを `AUTO_TECHSUPPORT_FEATURE` に自動代入。`AUTO_TECHSUPPORT|GLOBAL` が存在しない場合はスキップ。

**結論**: init_cfg.json.j2 がビルド時に全フィーチャーの `AUTO_TECHSUPPORT_FEATURE` エントリを派生生成。パッケージ追加時は sonic_package_manager が条件付きで追加代入。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### memory_threshold_check.py — 常時登録

```python
# sonic-utilities/scripts/memory_threshold_check.py:118
self.feature_table = cfg_db.get_table(AUTO_TECHSUPPORT_FEATURE)
```

`AUTO_TECHSUPPORT_FEATURE` テーブルを常時読み取る。条件付き登録なし。

### sonic_package_manager — パッケージ削除時の条件付き処理

パッケージアンインストール時に `AUTO_TECHSUPPORT_FEATURE` の当該エントリを削除。`old_name` パラメータがある場合は旧エントリを削除してから新エントリを作成（rename 対応）。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### memory_threshold_check — per-feature state フィールド分岐

`AUTO_TECHSUPPORT_FEATURE|<feature>` の `state` フィールド（`enabled` / `disabled`）により:

| state 値 | 処理 |
|---------|------|
| `enabled` | 当該フィーチャーコンテナのメモリ超過時に techsupport 起動 |
| `disabled` | 当該フィーチャーは early return でスキップ |

### available_mem_threshold — 数値比較分岐

```python
# memory_threshold_check.py:144
threshold = float(feature_cfg.get('available_mem_threshold',
                  DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD))
```

`available_mem_threshold` の数値が 0.0 の場合はメモリチェックをスキップ（デフォルト値 `DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD = 0`）。非ゼロの場合のみチェック実行。

<!-- /handler-branching -->
