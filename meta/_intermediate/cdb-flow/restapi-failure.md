# RESTAPI failure-behavior 調査メモ (Phase D)

調査日: 2026-05-19
対象ページ: docs/reference/config-db/restapi.md

## 調査対象ソース

- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/supervisord.conf`
- `sonic-utilities/scripts/db_migrator.py` L608-619

## 主要な失敗ポイント

### 1. mgmt_vars.j2 未存在 (exit 1)
- `rest-server.sh:6-9`: `MGMT_VARS_FILE=/usr/share/sonic/templates/mgmt_vars.j2` の存在チェック
- 未存在時 `exit $EXIT_MGMT_VARS_FILE_NOT_FOUND` (= 1)
- supervisord `autorestart=true` により無限再起動

### 2. sonic-cfggen 失敗
- `rest-server.sh:12`: `MGMT_VARS=$(sonic-cfggen -d -t $MGMT_VARS_FILE)`
- bash は `set -e` なし → 失敗しても空変数で続行
- 結果: `CLIENT_AUTH="user"` フォールバック + 自己署名証明書自動生成

### 3. 証明書自動生成失敗
- `rest-server.sh:44-49`: `generate_cert --host="localhost,127.0.0.1"` → `/tmp/cert.pem` / `/tmp/key.pem`
- `generate_cert` 失敗時もパス変数は設定済み → `rest_server` が TLS init 失敗で終了

### 4. 証明書ファイル実在チェックなし
- 指定パスの実在確認なし。`rest_server` 起動時に TLS init 失敗 → 終了 → 無限再起動

### 5. hot reload 未対応
- CONFIG_DB 変更はコンテナ再起動まで反映されない

### 6. db_migrator 早期 return
- `db_migrator.py:610-611`: `config_src_data` が None or `RESTAPI` キーなし → return
- `db_migrator.py:614-616`: 既存エントリがある場合は上書きしない
