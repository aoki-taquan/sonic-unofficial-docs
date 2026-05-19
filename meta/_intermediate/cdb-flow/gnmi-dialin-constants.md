# GNMI (dial-in) — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-gnmi:telemetry/telemetry.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi:pkg/bypass/bypass.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi:gnmi_server/clientCertAuth.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

---

## 1. Go フラグデフォルト（CONFIG_DB 非管理）

`telemetry.go` の `flag.String` / `flag.Int` / `flag.Uint64` 定義から取得。CONFIG_DB の YANG モデルや gnmi-native.sh では管理されない固定値。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `unix_socket` デフォルト | `/var/run/gnmi/gnmi.sock` | TLS なしローカル接続用 Unix ソケットパス | telemetry.go:175 |
| `jwt_refresh_int` | `900` 秒 | JWT トークンをリフレッシュ可能になる有効期限前秒数 | telemetry.go:183 |
| `jwt_valid_int` | `3600` 秒 | JWT トークン有効期間 | telemetry.go:184 |
| `max_recv_msg_size` | `4194304` (4 MiB) | gRPC サーバが受信できる最大メッセージサイズ | telemetry.go:209 |
| `max_send_msg_size` | `4194304` (4 MiB) | gRPC サーバが送信できる最大メッセージサイズ | telemetry.go:210 |
| `cert_crl_dir` | `/mtls/crl` | CRL ファイル格納ディレクトリ (`enable_crl=true` 時に参照) | telemetry.go:203 |
| `config_table_name` | `""` (空文字列) | gNMI クライアント証明書 CN 認証テーブル名フラグデフォルト。`user_auth=cert` 時は gnmi-native.sh が `GNMI_CLIENT_CERT` を明示設定 | telemetry.go:177 |

## 2. TLS / gRPC セキュリティ定数

CONFIG_DB から変更不可。コード内にリテラルで固定されている。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| TLS 最小バージョン | `tls.VersionTLS12` (= `0x0303`) | TLS 1.2 未満の接続を拒否 | telemetry.go:482 |
| keepalive MinTime | `20` 秒 | クライアントからの keepalive ping を許容する最短間隔 (DPU Proxy 等向け) | telemetry.go:547 |

## 3. bypass.go — CVL バイパス許可 SKU プレフィックス

`AllowedSKUPrefixes` は SmartSwitch 向け gNMI Set RPC で CVL バリデーションをスキップする SKU ハードコードリスト。CONFIG_DB / YANG での管理なし。

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `AllowedSKUPrefixes[0]` | `"Cisco-8102"` | CVL bypass 対象 SKU プレフィックス | bypass.go:34 |
| `AllowedSKUPrefixes[1]` | `"Cisco-8101"` | 同上 | bypass.go:35 |
| `AllowedSKUPrefixes[2]` | `"Cisco-8223"` | 同上 | bypass.go:36 |
| `defaultRedisSocket` | `/var/run/redis/redis.sock` | bypass 機能内部の Redis 接続用 Unix ソケット | bypass.go:43 |
| `defaultRedisTCP` | `127.0.0.1:6379` | 同 TCP フォールバック | bypass.go:44 |
| `configDbId` | `4` | bypass 機能が参照する CONFIG_DB の Redis DB ID | bypass.go:45 |

## 4. 補足

- `cert_crl_dir` (`/mtls/crl`) は `enable_crl=true` 設定時にのみ参照される。ディレクトリが存在しないまま `enable_crl=true` にすると CRL ダウンロードを試みるが、ローカルファイルが空のため全接続が拒否される。
- `AllowedSKUPrefixes` はコード変更なしに拡張できない。新 SKU 追加には `bypass.go` の再ビルドが必要。
- `max_recv_msg_size` / `max_send_msg_size` はフラグ経由で CLI から上書き可能だが、CONFIG_DB / YANG スキーマには反映されていない。
