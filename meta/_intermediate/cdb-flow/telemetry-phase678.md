# TELEMETRY — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/telemetry.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py / db_migrator.py 代入)

<!-- derivation -->

### 1. `gnmi` サブキーの固定値代入 (minigraph.py)

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2677-2688`

```python
results['TELEMETRY'] = {
    'gnmi': {
        'client_auth': 'true',
        'port': '50051',
        'log_level': '2'
    },
    'certs': {
        'server_crt': '/etc/sonic/telemetry/streamingtelemetryserver.cer',
        'server_key': '/etc/sonic/telemetry/streamingtelemetryserver.key',
        'ca_crt': '/etc/sonic/telemetry/dsmsroot.cer'
    }
}
```

- `port = 50051`、`client_auth = true`、`log_level = 2` がデフォルト値として固定代入。
- 証明書パスも `/etc/sonic/telemetry/` 配下に固定。

### 2. db_migrator.py `migrate_telemetry()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:621-629`

```python
def migrate_telemetry(self):
    ...
    self.configDB.set_entry("TELEMETRY", "gnmi", telemetry_data.get("gnmi"))
```

- 旧バージョンの TELEMETRY テーブルフォーマット（`TELEMETRY|gnmi` 以外のキー構造）を新フォーマットに変換。
- `gnmi` キーが存在しない場合は minigraph デフォルト値でエントリを作成。

### 3. db_migrator.py `migrate_gnmi()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:634`

- `gnmi` Feature 追加に伴う TELEMETRY テーブルの `gnmi` / `gnmi_port` フィールド分離マイグレーション。`gnmi_port` フィールドを `port` フィールドに統合。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

### `include_system_telemetry` によるビルド時条件

**ソース**: `sonic-buildimage/files/build_templates/init_cfg.json.j2:92`

```jinja
{%- if include_system_telemetry == "y" %}{% do features.append(("telemetry", "enabled", true, "enabled")) %}{% endif %}
```

- `include_system_telemetry != "y"` のビルドでは `FEATURE["telemetry"]` が生成されず、telemetry コンテナ自体が存在しないため TELEMETRY テーブルを処理する manager も登録されない。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### telemetry コンテナ内 gnmi_server の設定読み込み分岐

**ソース**: `sonic-gnmi/gnmi_server/server.go`

1. **`client_auth == "false"` 分岐**: TLS クライアント証明書検証をスキップ。`cert_pool` の構築処理を early return 相当でスキップし、`tls.NoClientCert` を設定。
2. **`port` 読み込み失敗 early return**: CONFIG_DB の `TELEMETRY|gnmi.port` が存在しない場合デフォルト 50051 を使用（早期フォールバック）。
3. **証明書パス検証**: `server_crt` / `server_key` ファイルが存在しない場合は起動時 `log.Fatal()` で終了。early return ではなくプロセス終了。
4. **`log_level` dispatch**: `0`=ERROR, `1`=WARNING, `2`=INFO, `3`=DEBUG に対応した glog レベルへマッピング。

<!-- /handler-branching -->
