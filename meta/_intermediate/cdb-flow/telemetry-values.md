# TELEMETRY — 値依存挙動調査メモ

## ソース

- `sonic-telemetry.yang` (sonic-buildimage@9ea932ec)
- `sonic-gnmi/gnmi_server/server.go` (gNMI server startup)

## enum / pattern 値

### `user_auth` (string pattern)

- `password`: ユーザ名/パスワード認証
- `jwt`: JWT トークン認証
- `cert`: クライアント証明書認証
- `none`: 認証なし

### `client_auth` (boolean)

- `true`: クライアント証明書による mTLS 認証を要求
- `false`: サーバ証明書のみ (TLS のみ)

### `save_on_set` (boolean)

- `true`: gNMI Set RPC 完了時に `config save` を実行
- `false`: Set RPC は CONFIG_DB にのみ反映、永続化しない

### `enable_crl` (boolean)

- `true`: CRL チェックを有効化。`crl_expire_duration` で有効期間を指定
- `false`: CRL チェックなし

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `port` | 未設定 / 0 | サーバ起動失敗（`unix_socket` も未設定の場合） |
| `client_auth` | `true` | `ca_crt` 未設定/ファイル不在だとサーバ起動失敗 |
| `client_auth` | `false` | サーバ証明書のみで TLS 接続。クライアント証明書不要 |
| `server_crt` / `server_key` | 一方のみ設定 | サーバ起動失敗 (`"server certificate or key file path is empty"`) |
| `enable_crl` | `true` | `crl_expire_duration` も合わせて設定が必要 |
| `log_level` | 0..100 | 数値が大きいほど詳細ログ。0 はほぼ無音 |
| 全フィールド | 起動後変更 | 反映にはコンテナ再起動 (`systemctl restart telemetry`) が必要 |
