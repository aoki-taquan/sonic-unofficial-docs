# gnmi-dialin Phase E — ハードコード定数調査メモ

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase E (ハードコード定数)

## 調査対象ソース

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-net/sonic-buildimage | 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd | 起動スクリプト。多数のハードコードパスと exit code 定数を含む |
| `telemetry/telemetry.go` | sonic-net/sonic-gnmi | eb635b7679b260c3fd0786a6d0734fc8e82c9a22 | Go バイナリ。`setupFlags()` にフラグデフォルト値を宣言 |

## 検出した定数一覧

### gnmi-native.sh のシステム定数

| 定数名 | 値 | 宣言箇所 |
|--------|-----|---------|
| `EXIT_TELEMETRY_VARS_FILE_NOT_FOUND` | `1` | `gnmi-native.sh:3` |
| `INCORRECT_TELEMETRY_VALUE` | `2` | `gnmi-native.sh:4` |
| `TELEMETRY_VARS_FILE` | `/usr/share/sonic/templates/telemetry_vars.j2` | `gnmi-native.sh:5` |
| `CVL_SCHEMA_PATH` | `/usr/sbin/schema` | `gnmi-native.sh:30` |
| telemetry バイナリパス | `/usr/sbin/telemetry` | `gnmi-native.sh:150` |
| SmartSwitch ZMQ ポート | `8100` | `gnmi-native.sh:91` |
| デフォルトポート (GNMI テーブル欠如時) | `8080` | `gnmi-native.sh:65` |
| `GRPC_GO_LOG_VERBOSITY_LEVEL` | `99` | `gnmi-native.sh:26` |
| `GRPC_GO_LOG_SEVERITY_LEVEL` | `info` | `gnmi-native.sh:27` |

### telemetry.go の Go フラグデフォルト値（CONFIG_DB 非管理の定数）

以下は `setupFlags()` 内でデフォルト値として宣言されているが、`gnmi-native.sh` からは明示的に設定されない（CONFIG_DB からは読み取られない）ため、ハードコード定数として扱う。

| フラグ名 | デフォルト値 | 宣言箇所 |
|---------|------------|---------|
| `unix_socket` | `/var/run/gnmi/gnmi.sock` | `telemetry.go:175` |
| `jwt_refresh_int` | `900` 秒 | `telemetry.go:183` |
| `jwt_valid_int` | `3600` 秒 | `telemetry.go:184` |
| `max_recv_msg_size` | `4194304` (4 MiB) | `telemetry.go:209` |
| `max_send_msg_size` | `4194304` (4 MiB) | `telemetry.go:210` |
| `img_dir` | `/tmp/host_tmp` | `telemetry.go:195` |
| `ca_cert_lnk` | `/keys/ca_cert.lnk` | `telemetry.go:199` |
| `server_cert_lnk` | `/keys/server_cert.lnk` | `telemetry.go:200` |
| `server_key_lnk` | `/keys/server_key.lnk` | `telemetry.go:201` |
| `cert_crl_dir` | `/mtls/crl` | `telemetry.go:203` |
| `grpc_meta` | `/keys/grpc-version.json` | `telemetry.go:204` |
| `authz_meta` | `/keys/authz-version.json` | `telemetry.go:205` |
| `authorization_policy_file` | `/keys/authorization_policy.json` | `telemetry.go:207` |

### telemetry.go の TLS / gRPC ハードコード値（ランタイム定数）

| 定数 | 値 | 宣言箇所 |
|------|----|---------|
| TLS 最小バージョン | `tls.VersionTLS12` (TLS 1.2) | `telemetry.go:482` |
| TLS 優先暗号スイート | ECDHE-ECDSA/RSA + AES-256-GCM / ChaCha20 / AES-128-GCM | `telemetry.go:486-493` |
| TLS セッションチケット無効 | `SessionTicketsDisabled: true` | `telemetry.go:483` |
| TLS 優先曲線 | P521, P384, P256 | `telemetry.go:484` |
| keepalive MinTime | `20` 秒 | `telemetry.go:547` |
| keepalive PermitWithoutStream | `true` | `telemetry.go:548` |

## 注記

- `GRPC_GO_LOG_VERBOSITY_LEVEL=99` は gRPC Go ライブラリの全ログを出力する設定。コンテナ起動時に `export` されるため、`telemetry` バイナリの環境変数として継承される。本番環境でも変更不可。
- `/keys/` パスは Docker コンテナ内のシンボリックリンクパス。外部の証明書ファイルが `GNMI|certs` で指定された場合、`setupFlags()` が自動的にリンクパスを `filepath.Dir(certFile)/ca_cert.lnk` 等に書き換える (telemetry.go:303-310)。
- `/mtls/crl` は CRL ファイルのデフォルトディレクトリ。`enable_crl=true` + `user_auth=cert` 時のみ参照される。
