# TELEMETRY — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`telemetry` サービス (sonic-gnmi) が `TELEMETRY` グローバルテーブルを読み、gNMI サーバーの起動設定を決定する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| gNMI サーバーポート | `TELEMETRY.port` 未設定 | デフォルト `8080` または `50051` | `telemetry` |
| TLS 証明書 | `TELEMETRY.server_crt` / `server_key` あり | TLS 有効で gNMI サーバー起動 | `telemetry` |
| auth mode | `TELEMETRY.client_auth==jwt` | JWT 認証を有効化 | `telemetry` |
| dial-in 有効化 | `TELEMETRY.allow_no_client_auth==true` | クライアント証明書なしの接続を許可 | `telemetry` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `telemetry` サービスが有効 | `TELEMETRY` テーブルを消費する sonic-gnmi が動作 | systemd service |
| `TELEMETRY|gnmi` エントリのみ処理 | シングルトン制約 | `sonic-gnmi.yang` |
| `log_level` フィールド | gNMI サーバーのログレベルを動的に変更 | `telemetry` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `telemetry` | `server_crt` / `server_key` フィールドあり | TLS 有効で gNMI サーバー起動 | `telemetry` |
| `telemetry` | TLS 設定なし | 平文または insecure モードで起動 | `telemetry` |
| `telemetry` | `client_auth==jwt` | JWT 認証ミドルウェアを有効化 | `telemetry` |
| `telemetry` | `client_auth==cert` | クライアント証明書認証を有効化 | `telemetry` |
| `telemetry` | `allow_no_client_auth==true` | mTLS を強制しない | `telemetry` |
| `telemetry` | `log_level` 変化 | ランタイムログレベルを変更 | `telemetry` |

> **スキャン証跡**: `TELEMETRY` は gNMI/gRPC サーバー設定のシングルトン。TLS フィールド有無と `client_auth` 値が起動モードを決定する主要分岐。
