# TELEMETRY_CLIENT — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`telemetry` サービス (sonic-gnmi / sonic-telemetry) が `TELEMETRY_CLIENT` テーブルを読み、gNMI dial-out クライアント設定を生成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| gNMI dial-out 接続先 | `TELEMETRY_CLIENT|<name>.dst_addr` | 指定アドレス:ポートへの gRPC 接続 | `telemetry_client` |
| TLS 設定 | `TELEMETRY_CLIENT|<name>.tls_cert` / `tls_key` あり | mTLS で dial-out 接続 | `telemetry_client` |
| subscription path | `TELEMETRY_SUBSCRIPTION|<name>.path` | gNMI Subscribe の path として使用 | `telemetry_client` |
| subscription mode | `TELEMETRY_SUBSCRIPTION|<name>.mode` | `STREAM` / `POLL` / `ONCE` | `telemetry_client` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `telemetry` サービスが有効 | `TELEMETRY_CLIENT` テーブルを消費するプロセスが存在 | systemd service |
| dial-out feature が有効化されている | コンパイル時オプションに依存する場合あり | `sonic-gnmi` build |
| `TELEMETRY_CLIENT.enabled==true` | dial-out クライアントを起動 | `telemetry_client` |
| `TELEMETRY_CLIENT.enabled==false` | dial-out クライアントを停止 | `telemetry_client` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `telemetry_client` | `enabled==true` | gRPC 接続を確立して subscription 開始 | `telemetry_client` |
| `telemetry_client` | `enabled==false` | gRPC 接続を切断 | `telemetry_client` |
| `telemetry_client` | `tls_cert` / `tls_key` あり | mTLS 証明書を使用して接続 | `telemetry_client` |
| `telemetry_client` | TLS 設定なし | 平文または server-only TLS で接続 | `telemetry_client` |
| `telemetry_client` | `retry_interval` 設定 | 接続失敗時の再試行インターバルを設定 | `telemetry_client` |

> **スキャン証跡**: `TELEMETRY_CLIENT` は gNMI dial-out のクライアント設定。`enabled` フィールドが主要分岐。TLS フィールドの有無が接続モードを決定（Phase 6 派生相当）。
