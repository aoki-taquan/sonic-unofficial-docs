# BGP_DEVICE_GLOBAL テーブル — consumer 例外条件分析

## Consumer: bgpcfgd / DeviceGlobalCfgMgr (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py)

### 処理関数
- `DeviceGlobalCfgMgr.set_handler(key, data)` (L~67)
- `DeviceGlobalCfgMgr.configure_tsa(data)` (L~96)
- `DeviceGlobalCfgMgr.configure_wcmp(data)` (L~120)
- `DeviceGlobalCfgMgr.configure_idf(data)` (L~130)

### 例外条件・特殊挙動

#### 1. data が None → log_err & return False
```python
if not data:
    log_err("DeviceGlobalCfgMgr:: data is None")
    return False
```

#### 2. tsa_enabled の値検証 → 不正値は FRR push しない
`isolate_unisolate_device(state)` 内で `state not in ["true", "false"]` の場合 log_err & return False。
FRR テンプレートレンダリングも行われない。

```python
if tsa_status not in ["true", "false"]:
    log_err("TSA: invalid value({}) is provided".format(tsa_status))
    return False
```

#### 3. wcmp_enabled の値検証 → 不正値は FRR push しない
`set_wcmp(status)` 内で `status not in ["true", "false"]` の場合 log_err & return False。

#### 4. chassis_tsa が "true" → TSA 操作をスキップ
chassis_tsa (シャーシ全体の TSA 状態) が true の場合、個別デバイスの TSA 操作はスキップ。
シャーシコントローラが優先される。

```python
if requires_update and self.chassis_tsa == "false":
    self.cfg_mgr.commit()
    self.cfg_mgr.update()
    self.isolate_unisolate_device(state)
else:
    log_notice("DeviceGlobalCfgMgr:: TSA configuration is up-to-date")
```

#### 5. is_update_required チェック (キャッシュ比較)
directory の現在値と変更値が同じ場合は FRR push をスキップ。

#### 6. Jinja2 テンプレートレンダリング失敗 → log_err & return False
TSA/WCMP テンプレートレンダリングで `jinja2.TemplateError` が発生した場合、log_err を出して False を返す。
FRR には反映されない。

#### 7. idf_isolation_state — 値検証なし
`configure_idf()` では `downstream_isolate_unisolate(state)` を呼ぶが、state の `"isolated"/"unisolated"` 以外の値検証は idf handler 側に委ねられている。

#### 8. DEVICE_METADATA.localhost/type 依存
`handle_type_update()` が switch_role を設定するが、type が不明な場合は role が空文字列のまま処理が進む。空 role 時の動作は TSA テンプレートの条件分岐に依存。
