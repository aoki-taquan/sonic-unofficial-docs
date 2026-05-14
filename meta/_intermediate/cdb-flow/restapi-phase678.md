# RESTAPI — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/restapi.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py / db_migrator.py 代入)

<!-- derivation -->

### 1. `config` / `certs` サブキーの固定値代入 (minigraph.py)

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2689-2701`

```python
results['RESTAPI'] = {
    'config': {
        'client_auth': 'true',
        'allow_insecure': 'false',
        'log_level': 'info'
    },
    'certs': {
        'server_crt': '/etc/sonic/credentials/restapiserver.crt',
        'server_key': '/etc/sonic/credentials/restapiserver.key',
        'ca_crt': '/etc/sonic/credentials/restapica.crt',
        'client_crt_cname': 'client.restapi.sonic'
    }
}
```

- `client_auth = true`、`allow_insecure = false`、`log_level = info` が固定デフォルト値として代入。
- 証明書パスは `/etc/sonic/credentials/` 配下に固定。

### 2. db_migrator.py `migrate_restapi()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:608-619`

```python
def migrate_restapi(self):
    ...
    self.configDB.set_entry("RESTAPI", "config", restapi_data.get("config"))
    self.configDB.set_entry("RESTAPI", "certs", restapi_data.get("certs"))
```

- 旧バージョンの RESTAPI テーブルフォーマット（フラット構造）を `config` / `certs` の 2 サブキー構造に変換。
- 旧エントリが存在しない場合は minigraph デフォルト値で新規作成。

### 3. `include_restapi` ビルドフラグによる Feature 条件付与

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:84-88`

```jinja
{%- if include_restapi == "y" and BUILD_REDUCE_IMAGE_SIZE == "y" and sonic_asic_platform == "broadcom" %}
    {% do features.append(("restapi", "{% if ... type not in ['LeafRouter', 'BackEndLeafRouter'] %}enabled{% else %}disabled{% endif %}", ...)) %}
{%- elif include_restapi == "y" %}
    {% do features.append(("restapi", "enabled", false, "enabled")) %}
{%- endif %}
```

- `include_restapi == "y"` の場合のみ `FEATURE["restapi"]` が生成される。Broadcom 縮小イメージでは device type 条件が追加される。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

該当なし。

`restapi` コンテナは `FEATURE["restapi"]["state"]` が `enabled` の場合のみ systemd で起動する。コンテナ内部での CONFIG_DB 参照は起動後に行われ、動的な manager 登録の仕組みは使用しない。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### restapi コンテナ内 server.py の設定読み込み分岐

1. **`allow_insecure == "true"` 分岐**: TLS なしで HTTP/8080 でリッスン。証明書パス検証をスキップして early return 相当。`allow_insecure == "false"` の場合は HTTPS/443（`port` フィールド参照）でリッスン。
2. **`client_auth == "false"` 分岐**: クライアント証明書検証なし。`client_crt_cname` フィールドは参照されない。
3. **証明書ファイル存在チェック early return**: `server_crt` / `server_key` ファイルが存在しない場合はサービス起動を中止してエラーログ。
4. **`log_level` dispatch**: `debug` / `info` / `warning` / `error` の各レベルに対応した Python logging レベルへマッピング。

<!-- /handler-branching -->
