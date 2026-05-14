# BGP_DEVICE_GLOBAL — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### init_cfg.json.j2 — STATE エントリ自動生成

```jinja2
{# sonic-buildimage/files/build_templates/init_cfg.json.j2:60 #}
"BGP_DEVICE_GLOBAL": {
    "STATE": {
        "tsa_enabled": "false",
        "wcmp_enabled": "false",
        "idf_isolation_state": "unisolated"
    }
},
```

ビルド時に `BGP_DEVICE_GLOBAL|STATE` が固定デフォルト値で自動生成される。テンプレート変数なし（全フィールドがハードコード）。

### minigraph.py / db_migrator.py

BGP_DEVICE_GLOBAL への代入なし。

**結論**: ビルド時に init_cfg.json.j2 が `BGP_DEVICE_GLOBAL|STATE` を固定デフォルト（TSA無効・WCMP無効・IDF unisolated）で派生代入。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd — DeviceGlobalCfgMgr (常時)

```python
# sonic-bgpcfgd/bgpcfgd/main.py:104
DeviceGlobalCfgMgr(common_objs, "CONFIG_DB", swsscommon.CFG_BGP_DEVICE_GLOBAL_TABLE_NAME),
```

`DeviceGlobalCfgMgr` は **常時** 登録される。

### bgpcfgd — ChassisAppDbMgr (条件付き)

```python
# sonic-bgpcfgd/bgpcfgd/main.py:113
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

chassis 環境のみ `ChassisAppDbMgr` が追加登録される。CHASSIS_APP_DB の `BGP_DEVICE_GLOBAL` を購読し、chassis レベルの TSA 状態を同期する。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### DeviceGlobalCfgMgr.set_handler() — 3 フィールド個別 dispatch

```python
# managers_device_global.py:set_handler()
def set_handler(self, key, data):
    if not data:
        return False  # early return: データなし
    self.configure_tsa(data)
    self.configure_wcmp(data)
    self.configure_idf(data)
    return True
```

### configure_tsa() — chassis_tsa early return

```python
# managers_device_global.py:configure_tsa()
self.chassis_tsa = self.get_chassis_tsa_status()
requires_update = self.is_update_required("tsa_enabled", state)
if requires_update and self.chassis_tsa == "false":
    self.isolate_unisolate_device(state)
else:
    log_notice("TSA configuration is up-to-date")  # early return 相当
```

| 条件 | 処理 |
|------|------|
| `chassis_tsa == "true"` | ローカル TSA 操作をスキップ（chassis 優先） |
| `chassis_tsa == "false"` かつ値変更あり | FRR route-map に TSA/TSB を適用 |
| 値変更なし | no-op |

### idf_isolation_state フィールド分岐

```python
# managers_device_global.py:downstream_isolate_unisolate()
if idf_isolation_state not in ["unisolated", "isolated_withdraw_all", "isolated_no_export"]:
    log_err("IDF: invalid value({}) is provided".format(idf_isolation_state))
    return False  # early return: 無効値
if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]:
    return True  # early return: 対象 role 外
```

| idf_isolation_state 値 | FRR 処理 |
|----------------------|---------|
| `unisolated` | `idf_unisolate.conf.j2` テンプレートを push |
| `isolated_withdraw_all` | `idf_isolate.conf.j2` を `isolation_status=isolated_withdraw_all` で push |
| `isolated_no_export` | `idf_isolate.conf.j2` を `isolation_status=isolated_no_export` で push |

**switch_role early return**: `SpineRouter` / `LowerSpineRouter` / `UpperSpineRouter` 以外の role では IDF 設定を適用しない。

### configure_wcmp() — 値変更チェック

```python
# managers_device_global.py:configure_wcmp()
if self.is_update_required("wcmp_enabled", state):
    self.set_wcmp(state)
else:
    log_notice("W-ECMP configuration is up-to-date")
```

`wcmp_enabled` が `"true"` / `"false"` 以外の場合 `set_wcmp()` が `False` を返してスキップ。

<!-- /handler-branching -->
