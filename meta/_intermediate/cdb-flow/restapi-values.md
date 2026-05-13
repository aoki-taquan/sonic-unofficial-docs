# RESTAPI — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

`RESTAPI|certs`:
- `ca_crt`: string（パスパターン）
- `server_crt`: string（`*.crt` パス）
- `server_key`: string（`*.key` パス）
- `client_crt_cname`: string（カンマ区切り CN リスト）

`RESTAPI|config`:
- `client_auth`: boolean。デフォルト `true`。
- `log_level`: string（`trace|info` pattern）。enum なし。
- `allow_insecure`: boolean。デフォルト `false`。

## Phase 2: per-value 挙動

### `client_auth` 値別挙動
| 値 | 挙動 |
|----|------|
| `true` | クライアント証明書認証必須（mTLS）。デフォルト。 |
| `false` | クライアント証明書不要。サーバ証明書のみ検証。 |

### `log_level` 値別挙動
| 値 | 挙動 |
|----|------|
| `trace` | 詳細ログ出力。 |
| `info` | 通常ログ。 |
| その他 | YANG `pattern "trace|info"` 違反でバリデーション拒否。 |

### `allow_insecure` 値別挙動
| 値 | 挙動 |
|----|------|
| `false` | HTTP 接続不可（デフォルト）。HTTPS のみ。 |
| `true` | HTTP 平文接続を許可。テスト用途向け。 |

## Phase 3: ソース確認

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-restapi.yang`: `log_level` は `pattern "trace|info"` の string leaf（enum 定義なし）。`client_auth` / `allow_insecure` は boolean 型。
- 変更反映: `docker-sonic-restapi` コンテナ再起動時のみ（hot reload 非対応）。

## enum 有無

- `log_level`: YANG enum なし（string + pattern `"trace|info"`）
- `client_auth` / `allow_insecure`: YANG boolean
