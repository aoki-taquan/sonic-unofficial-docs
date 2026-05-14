# AUTO_TECHSUPPORT — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### init_cfg.json.j2 — GLOBAL エントリ自動生成

```jinja2
{# sonic-buildimage/files/build_templates/init_cfg.json.j2:128 #}
"AUTO_TECHSUPPORT": {
    "GLOBAL": {
{%- if enable_auto_tech_support == "y" %}
        "state" : "enabled", {% else %}
        "state" : "disabled", {% endif %}
        "rate_limit_interval" : "180",
        "max_techsupport_limit" : "10.0",
        "max_core_limit" : "5.0",
        "available_mem_threshold": "10.0",
        "min_available_mem": "200",
        "since" : "2 days ago"
    }
},
```

`enable_auto_tech_support` ビルドフラグが `"y"` の場合 `state=enabled`、それ以外は `state=disabled` として自動生成される。`rate_limit_interval` / `max_techsupport_limit` 等は固定値で派生代入。

### minigraph.py / db_migrator.py

AUTO_TECHSUPPORT への代入なし。

**結論**: ビルド時に init_cfg.json.j2 が `AUTO_TECHSUPPORT|GLOBAL` を `enable_auto_tech_support` フラグに基づき自動派生代入する。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### sonic_package_manager — 条件付き AUTO_TECHSUPPORT_FEATURE 登録

```python
# sonic-utilities/sonic_package_manager/service_creator/feature.py:186
if not auto_ts_add_cfg:
    log.debug("Skip adding AUTO_TECHSUPPORT_FEATURE table because no AUTO_TECHSUPPORT|GLOBAL entry is found")
    return False
```

パッケージインストール時に `AUTO_TECHSUPPORT|GLOBAL` エントリが存在しない場合、`AUTO_TECHSUPPORT_FEATURE` への新フィーチャー登録をスキップする。

### memory_threshold_check.py

```python
# sonic-utilities/scripts/memory_threshold_check.py:117
self.table = cfg_db.get_table(AUTO_TECHSUPPORT)
self.feature_table = cfg_db.get_table(AUTO_TECHSUPPORT_FEATURE)
config = self.table.get("GLOBAL")
```

`memory_threshold_check` は起動時に `AUTO_TECHSUPPORT|GLOBAL` を読み取る。常時動作（条件付き登録なし）だが、`state=disabled` の場合は内部で処理スキップ。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### memory_threshold_check — state フィールド分岐

`AUTO_TECHSUPPORT|GLOBAL` の `state` フィールド（`enabled` / `disabled`）により:

| state 値 | 処理 |
|---------|------|
| `enabled` | メモリ閾値チェック実行、閾値超過時に `show techsupport` を起動 |
| `disabled` | メモリチェックを early return でスキップ |

### coredump_gen_handler — state フィールド early return

```python
# coredump_gen_handler.py (auto_techsupport_helper.py 経由)
auto_ts = cfg_db.get_entry("AUTO_TECHSUPPORT", "GLOBAL")
if auto_ts.get("state", "disabled") != "enabled":
    return  # early return
```

`state != "enabled"` の場合は coredump 検知後も techsupport 収集をスキップ。

<!-- /handler-branching -->
