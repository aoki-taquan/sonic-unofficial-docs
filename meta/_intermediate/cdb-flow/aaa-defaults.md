# AAA フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `AAA`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (AaaCfg クラス)
- `sonic-utilities/config/aaa.py` (CLI 書き込み)
- `sonic-utilities/scripts/db_migrator.py` (migrate_aaa_table_field_sync)

---

## フィールド別 暗黙デフォルト

### `login` (AAA|authentication)

**コード由来デフォルト**: `'local'`

```python
# hostcfgd:357-359
self.authentication_default = {
    'login': 'local',
}
```

`modify_conf_file()` (hostcfgd:642-643) で:
```python
authentication = self.authentication_default.copy()
authentication.update(self.authentication)
```
→ DB に `login` キーが存在しない場合、`authentication_default['login'] = 'local'` が有効になる。

**authorization の login デフォルト**: `'local'`

```python
# hostcfgd:361-363
self.authorization_default = {
    'login': 'local',
}
```

**accounting の login デフォルト**: `'disable'`

```python
# hostcfgd:364-366
self.accounting_default = {
    'login': 'disable',
}
```

---

### `failthrough` (AAA|authentication)

**コード由来デフォルト**: `False` (Python bool)

`authentication_default` に `failthrough` キーは存在しない。  
`aaa_update()` (hostcfgd:422-423) で `failthrough` が DB に存在する場合のみ `is_true()` で変換。

`modify_conf_file()` では `authentication_default.copy()` + `authentication` の merge。  
DB に `failthrough` が無い場合、`authentication` dict にも存在しない → Jinja2 テンプレートへ渡す dict に `failthrough` キー自体が無い。

Jinja2 テンプレート (`common-auth-sonic.j2:16`) では `auth.failthrough` を参照。  
キーが存在しない場合 Jinja2 は `undefined` → falsy → 事実上 `false` と同等の PAM 生成 (auth_err=die 付与)。

**is_true() の判定**: `'True'/'true'` のみ `True`。それ以外 (`'False'`, `'false'`, 不正値) は全て `False` を返す (hostcfgd:156-162)。

---

### `fallback` (AAA|authentication)

**コード由来デフォルト**: キーなし → Jinja2 で falsy → `false` 相当

`authentication_default` にも `aaa_update()` にも `fallback` の変換処理なし。  
DB から来た文字列がそのまま dict に格納される (bool 変換なし)。  
テンプレート側が真偽判定を担う。

---

### `debug` (AAA|authentication — class attribute)

**コード由来デフォルト**: `False` (Python bool literal)

```python
# hostcfgd:393
self.debug = False
```

`aaa_update()` (hostcfgd:424-425) で DB に `debug` キーが存在する場合のみ上書き:
```python
if 'debug' in data:
    self.debug = is_true(data['debug'])
```

DB に `debug` キーが無い場合 → `self.debug = False` のまま。  
`modify_conf_file()` は `debug=self.debug` を Jinja2 に渡す (hostcfgd:721-722)。

---

### `trace` (AAA|authentication — class attribute)

**コード由来デフォルト**: `False` (Python bool literal)

```python
# hostcfgd:394
self.trace = False
```

**重要な差異**: `aaa_update()` に `trace` の処理ブロックが存在しない (`debug` と異なる)。  
DB に `trace` キーが存在しても `self.trace` は更新されない。

`modify_conf_file()` は `trace=self.trace` を Jinja2 に渡す (hostcfgd:721)。  
つまり `trace` フィールドを CONFIG_DB に設定しても `hostcfgd` は無視し、常に `False` となる。

**バグ扱いの可能性**: `debug` は `aaa_update()` で処理されるが `trace` は未処理。  
実際の PAM 生成に `trace` が反映されない。

---

## 要約表

| フィールド | key (AAA type) | コード由来デフォルト | fallback 源 |
|-----------|---------------|-------------------|------------|
| `login` | authentication | `'local'` | `authentication_default` dict (hostcfgd:357) |
| `login` | authorization | `'local'` | `authorization_default` dict (hostcfgd:361) |
| `login` | accounting | `'disable'` | `accounting_default` dict (hostcfgd:364) |
| `failthrough` | authentication | `False` (Jinja2 undefined → falsy) | キー不在時は dict に存在しない |
| `fallback` | authentication | `False` (Jinja2 undefined → falsy) | キー不在時は dict に存在しない |
| `debug` | authentication | `False` (Python literal `self.debug`) | `__init__` hostcfgd:393 |
| `trace` | authentication | `False` (Python literal `self.trace`) | `__init__` hostcfgd:394 — **DB値は無視** |

---

## 追記: db_migrator の挙動

`migrate_aaa_table_field_sync()` (db_migrator.py:876-903):

- DB に `AAA|authentication` が存在しない場合のみ `config_src_data['AAA']['authentication']` から補完。
- DB に既にエントリがある場合はスキップ (上書きしない)。
- `config_src_data` は migration 元の設定ファイルから来る値であり、`'local'` がデフォルトと想定。

---

## 証拠リンク

- `hostcfgd:354-394` — `AaaCfg.__init__` (authentication_default / accounting_default / self.debug / self.trace)
- `hostcfgd:419-435` — `aaa_update()` (failthrough/debug 処理あり、trace 処理なし)
- `hostcfgd:641-648` — `modify_conf_file()` (default.copy() + update() パターン)
- `db_migrator.py:876-903` — `migrate_aaa_table_field_sync()`
