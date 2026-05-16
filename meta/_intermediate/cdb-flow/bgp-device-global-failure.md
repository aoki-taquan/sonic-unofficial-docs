# BGP_DEVICE_GLOBAL — Phase D 失敗挙動 中間ファイル

生成日: 2026-05-16

ソース:
- `sonic-net/sonic-buildimage`: `src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`

<!-- failure -->
## Phase D: 失敗挙動・retry 分岐スキャン

### set_handler() — data が None

```python
# managers_device_global.py:61-63
if not data:
    log_err("DeviceGlobalCfgMgr:: data is None")
    return False
```

`set_handler()` が `data=None` で呼ばれた場合、即座に `log_err` して `False` を返す。FRR へのコマンド push はすべてスキップされる。retry なし。

---

### configure_tsa() / isolate_unisolate_device() — TSA 適用スキップ

```python
# managers_device_global.py:186-188
if tsa_status not in ["true", "false"]:
    log_err("TSA: invalid value({}) is provided".format(tsa_status))
    return False
```

- `tsa_enabled` が `"true"` / `"false"` 以外の不正値 → `log_err` 後 `return False`。FRR への route-map push なし。
- `chassis_tsa == "true"` の場合も `isolate_unisolate_device()` 呼び出しをスキップ（シャーシ全体 TSA が優先）。ログのみ: `log_notice("TSA configuration is up-to-date")`。
- retry 機構なし。

---

### set_wcmp() — W-ECMP Jinja2 テンプレートレンダリング失敗

```python
# managers_device_global.py:158-162
try:
    cmd += self.wcmp_template.render(wcmp_enabled=status)
except jinja2.TemplateError as e:
    msg = "W-ECMP: error in template rendering"
    log_err("%s: %s" % (msg, str(e)))
    return False
```

- `jinja2.TemplateError` 発生時: `log_err` 後 `return False`。`cfg_mgr.push()` は呼ばれない。FRR 未反映のまま。
- retry なし。呼び出し元 `configure_wcmp()` も `set_wcmp()` の戻り値を確認し directory への書き込みを行わない（`False` 時はスキップ）。

```python
# managers_device_global.py:122-124
if self.is_update_required("wcmp_enabled", state):
    if self.set_wcmp(state):
        self.directory.put(self.db_name, self.table_name, "wcmp_enabled", state)
```

- 不正値（`"true"` / `"false"` 以外）: `set_wcmp()` 冒頭で `return False`。directory 更新なし。

---

### downstream_isolate_unisolate() — IDF 適用失敗

```python
# managers_device_global.py:256-263
if idf_isolation_state not in ["unisolated", "isolated_withdraw_all", "isolated_no_export"]:
    log_err("IDF: invalid value({}) is provided".format(idf_isolation_state))
    return False

if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]:
    log_debug("DeviceGlobalCfgMgr:: Skipping IDF isolation configuration on %s" % self.switch_role)
    return True
```

- 不正値: `log_err` 後 `return False`。呼び出し元 `configure_idf()` が `False` を受けて directory 書き込みをスキップ。
- 非対象 switch_role: FRR push せず `return True`（失敗ではなくスキップ）。directory は更新しない（`configure_idf` は戻り値 `True` 時のみ `directory.put()` を実行）。

---

### get_chassis_tsa_status() — CHASSIS_APP_DB 接続失敗

```python
# managers_device_global.py:244-250
try:
    ch = swsscommon.SonicV2Connector(use_unix_socket_path=False)
    ch.connect(ch.CHASSIS_APP_DB, False)
    chassis_tsa_status = ch.get(ch.CHASSIS_APP_DB, "BGP_DEVICE_GLOBAL|STATE", 'tsa_enabled')
except Exception as e:
    log_err("Got an exception {}".format(e))
```

- CHASSIS_APP_DB 接続例外発生時: `chassis_tsa_status = "false"` のまま返る。シャーシ TSA フラグを読み取れない場合は「chassis TSA なし」として処理継続する（フォールセーフ）。

---

### BFD capability 不在について

`managers_device_global.py` は BFD 関連フィールドを直接操作しない。`BGP_DEVICE_GLOBAL` テーブルには BFD フィールドが存在しないため、BFD capability 不在による失敗パスは本テーブルのスコープ外。

### retry 機構の総括

`DeviceGlobalCfgMgr` には **retry 機構が存在しない**。すべての失敗は `log_err` 記録後に即 `return False`。再試行は CONFIG_DB の次回変更イベント受信時に自然に発生する。

<!-- /failure -->
