# RESTAPI 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-restapi.yang`
- `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/tests/restapi.json`

## 抽出した例外条件

1. **TLS パス pattern 制約**: `ca_crt`、`server_crt`、`server_key` は YANG の `pattern` 制約でファイルパス形式 (`(/[a-zA-Z0-9_-]+)*/([a-zA-Z0-9_-]+).(ext)`) のみ受け入れる。パターン違反は sonic-yang バリデーション時に拒否。
   - 証拠: YANG l.29-54、テスト `RESTAPI_TABLE_WITH_INCORRECT_CERT` / `TABLE_WITH_INCORRECT_CLIENT` が Pattern エラーを期待

2. **client_crt_cname のワイルドカード制約**: `client_crt_cname` は `((\*\.)?[a-zA-Z0-9_\-\.]+,)*` の pattern で有効なドメイン/ワイルドカードを要求。カンマ区切りの複数指定は可能だが末尾カンマや空白は不可。
   - 証拠: テストケース `TABLE_WITH_INCORRECT_WILDCARD_CLIENT_1` ～ `_5`

3. **log_level は trace/info のみ**: `config.log_level` は YANG の `pattern "trace|info"` で制約。それ以外はバリデーション拒否。

4. **docker-sonic-restapi の runtime 読み込み**: RESTAPI テーブルは `docker-sonic-restapi` コンテナ起動時に CONFIG_DB から読み込まれる。コンテナ起動中の変更は再起動するまで反映されない（hot reload 未対応）。

5. **client_auth=false + allow_insecure=false の競合**: TLS 証明書を設定しないまま `allow_insecure=false` (デフォルト) にすると RESTAPI サーバが起動できない。証明書ファイルが実際に存在しない場合もサーバ起動に失敗するが、これは CONFIG_DB レベルでは検知されない。
