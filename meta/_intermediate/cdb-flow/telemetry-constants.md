# TELEMETRY — Phase E ハードコード定数スキャンノート

対象テーブル: `TELEMETRY`
Consumer: `telemetry.sh` → `/usr/sbin/telemetry` (sonic-gnmi)
スキャン範囲:
- `sonic-gnmi/telemetry/telemetry.go` 全行精読
- `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh` 全行精読
- `sonic-gnmi/gnmi_server/server.go` 起動パラメータ部 (L200-260)

---

## 検出したハードコード定数

### プロセス起動フラグデフォルト値 (telemetry.go)

| 定数 / フラグ | 値 | 用途 | ソース |
|--------------|-----|------|--------|
| `--port` | `-1` | ポート未指定時の初期値。起動時に必ず上書きが必要 (`port > 0` または `unix_socket` 指定) | telemetry.go L174 |
| `--unix_socket` | `/var/run/gnmi/gnmi.sock` | TLS なしローカル接続用 UNIX ドメインソケットパス | telemetry.go L175 |
| `--v` (log level) | `2` | 非数値 / 負数の場合に強制回帰するデフォルトログレベル | telemetry.go L176, L248 |
| `--jwt_refresh_int` | `900` 秒 | JWT トークンのリフレッシュ可能期間 (期限の 15 分前から可能) | telemetry.go L183 |
| `--jwt_valid_int` | `3600` 秒 | JWT トークン有効期間 (1 時間) | telemetry.go L184 |
| `--threshold` | `100` | 最大クライアント接続数 | telemetry.go L187 |
| `--idle_conn_duration` | `5` 秒 | アイドル接続を閉じるまでの時間 | telemetry.go L190 |
| `--crl_expire_duration` | `86400` 秒 | CRL キャッシュ有効期限 (24 時間) | telemetry.go L194 |
| `--img_dir` | `/tmp/host_tmp` | SetPackage 等で転送されるイメージの一時ディレクトリ | telemetry.go L195 |
| `--max_recv_msg_size` | `4 * 1024 * 1024` (4 MiB) | gRPC 受信メッセージ最大サイズ | telemetry.go L209 |
| `--max_send_msg_size` | `4 * 1024 * 1024` (4 MiB) | gRPC 送信メッセージ最大サイズ | telemetry.go L210 |

### 証明書シンボリックリンクパス (telemetry.go)

| 定数 / フラグ | 値 | 用途 | ソース |
|--------------|-----|------|--------|
| `--ca_cert_lnk` | `/keys/ca_cert.lnk` | CA 証明書シンボリックリンクパス | telemetry.go L199 |
| `--server_cert_lnk` | `/keys/server_cert.lnk` | サーバ証明書シンボリックリンクパス | telemetry.go L200 |
| `--server_key_lnk` | `/keys/server_key.lnk` | サーバ秘密鍵シンボリックリンクパス | telemetry.go L201 |
| `--cert_crl_dir` | `/mtls/crl` | CRL ファイル格納ディレクトリ | telemetry.go L203 |
| `--grpc_meta` | `/keys/grpc-version.json` | gRPC クレデンシャルメタデータ JSON | telemetry.go L204 |
| `--authz_meta` | `/keys/authz-version.json` | 認可ポリシーメタデータ JSON | telemetry.go L205 |
| `--authorization_policy_file` | `/keys/authorization_policy.json` | 認可ポリシーファイルパス | telemetry.go L207 |

### TLS パラメータ (telemetry.go L482-493)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `MinVersion` | `tls.VersionTLS12` | TLS 1.2 を最低バージョンとして強制 | telemetry.go L482 |
| `CurvePreferences` | `[P521, P384, P256]` | ECDH 曲線優先順位（強度順） | telemetry.go L484 |
| `CipherSuites` | 6 ECDHE スイート | ECDHE_ECDSA/RSA × AES-256-GCM / ChaCha20 / AES-128-GCM | telemetry.go L486-492 |
| `SessionTicketsDisabled` | `true` | セッションチケット無効（前方秘匿性保持） | telemetry.go L483 |
| `PreferServerCipherSuites` | `true` | サーバ側優先暗号スイート選択 | telemetry.go L485 |

### keepalive 固定値 (telemetry.go L537-549)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `keepalive.EnforcementPolicy.MinTime` | `20` 秒 | クライアントが keepalive ping を送れる最短間隔 (デフォルト 5 分から短縮) | telemetry.go L547 |
| `keepalive.EnforcementPolicy.PermitWithoutStream` | `true` | アクティブストリームがなくても ping を許可 | telemetry.go L548 |

### telemetry.sh フォールバック値 (CONFIG_DB 非依存)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| フォールバックポート | `8080` | `TELEMETRY|gnmi` キー自体が CONFIG_DB にない場合のデフォルト | telemetry.sh L85 |
| フォールバックログレベル | `2` | `log_level` が非数値または未設定の場合 | telemetry.sh L104 |
| フォールバック threshold | `100` | `threshold` が null または未設定の場合 | telemetry.sh L121 |
| フォールバック idle_conn_duration | `5` 秒 | `idle_conn_duration` が null または未設定の場合 | telemetry.sh L134 |
| GNMI_CLIENT_CERT テーブル名 | `"GNMI_CLIENT_CERT"` | `user_auth=cert` 時に `--config_table_name` へ渡す固定テーブル名 | telemetry.sh L148 |

> **注意**: `threshold` と `idle_conn_duration` は YANG (`sonic-telemetry.yang`) に定義がなく、`telemetry.sh` のみで管理される隠れデフォルト。これらの値は CONFIG_DB に書き込まれず、YANG バリデーションの対象外。

evidence:
- `sonic-gnmi/telemetry/telemetry.go@eb635b7679b260c3fd0786a6d0734fc8e82c9a22` L171-215, L482-549
- `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh@9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` L85-158
