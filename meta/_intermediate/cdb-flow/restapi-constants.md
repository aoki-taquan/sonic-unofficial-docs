# RESTAPI ハードコード定数抽出 (Phase E)

## ソース
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/rest-server.sh`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/supervisord.conf`
- `sonic-buildimage/dockers/docker-sonic-mgmt-framework/mgmt_vars.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-restapi.yang`

## 抽出した定数

### rest-server.sh 起動スクリプト定数

| 定数名 | 値 | 用途 |
|-------|----|------|
| `EXIT_MGMT_VARS_FILE_NOT_FOUND` | `1` | mgmt_vars.j2 テンプレートファイル未存在時の exit code。`rest-server.sh:4` |
| `MGMT_VARS_FILE` | `/usr/share/sonic/templates/mgmt_vars.j2` | sonic-cfggen が読み込む Jinja2 テンプレートの固定パス。`rest-server.sh:5` |
| `CLIENT_AUTH` (フォールバック) | `"user"` | `RESTAPI\|config.client_auth` が未設定の場合に適用されるデフォルト認証モード。YANG スキーマの `default true` (boolean) と異なる文字列。`rest-server.sh:20,30` |
| `generate_cert --host` | `"localhost,127.0.0.1"` | 証明書自動生成時のホスト名固定値。`rest-server.sh:47` |
| `SERVER_CRT` (自動生成時) | `/tmp/cert.pem` | 証明書未設定時の自己署名証明書パス固定値。`rest-server.sh:48` |
| `SERVER_KEY` (自動生成時) | `/tmp/key.pem` | 証明書未設定時の秘密鍵パス固定値。`rest-server.sh:49` |
| `REST_SERVER_ARGS` (固定引数) | `-ui /rest_ui -logtostderr` | `rest_server` バイナリに常に付与される起動引数。UI パスとログ出力先が固定。`rest-server.sh:53` |
| `CVL_SCHEMA_PATH` | `/usr/sbin/schema` | YANG ベースのバリデーション (CVL) が参照するスキーマディレクトリの固定パス。`rest-server.sh:64` |

### supervisord.conf 定数

| 設定キー | 値 | 用途 |
|---------|-----|------|
| `[program:rest-server] priority` | `3` | supervisord プロセス起動優先度。`rsyslogd(1)` → `start(2)` → `rest-server(3)` の順序を保証。`supervisord.conf:39` |
| `[program:rest-server] autorestart` | `true` | `rest_server` 終了時の自動再起動有効。`supervisord.conf:41` |
| `dependent_startup_wait_for` | `start:exited` | `start.sh` 完了後に `rest-server.sh` を起動する依存順序設定。CONFIG_DB への書き込みが確実に先行する。`supervisord.conf:47` |
| `logfile_maxbytes` | `1MB` | supervisord 自身のログファイル最大サイズ。`supervisord.conf:2` |
| `logfile_backups` | `2` | supervisord ログローテーション保存数。`supervisord.conf:3` |

### YANG スキーマ定数 (sonic-restapi.yang)

| フィールド | 定数値 | 種別 |
|-----------|--------|------|
| `config.client_auth` | `default true` | YANG `default` 文。boolean 型。`sonic-restapi.yang:64` |
| `config.allow_insecure` | `default false` | YANG `default` 文。boolean 型。`sonic-restapi.yang:79` |
| `config.log_level` pattern | `"trace\|info"` | YANG `pattern` 制約。それ以外の値は sonic-yang バリデーション拒否。`sonic-restapi.yang:70` |
| `certs.ca_crt` pattern | `'(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).([a-z]+)'` | ファイルパス形式制約。`sonic-restapi.yang:31` |
| `certs.server_crt` pattern | `'(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).crt'` | `.crt` 拡張子強制。`sonic-restapi.yang:37` |
| `certs.server_key` pattern | `'(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).key'` | `.key` 拡張子強制。`sonic-restapi.yang:50` |
| `certs.client_crt_cname` pattern | `'((\*\.)?[a-zA-Z0-9_\-\.]+,)*((\*\.)?[a-zA-Z0-9_\-\.]+)'` | CN 形式制約（ワイルドカード可、末尾カンマ不可）。`sonic-restapi.yang:44` |

## 注記

- YANG の `client_auth` は boolean (`default true`) だが、`rest-server.sh` は文字列 `"user"` をフォールバックとして使用する。これは YANG スキーマと実装の乖離点。
- `REST_SERVER_ARGS="-ui /rest_ui -logtostderr"` の UI パス `/rest_ui` はコンテナイメージ内の固定パス。
