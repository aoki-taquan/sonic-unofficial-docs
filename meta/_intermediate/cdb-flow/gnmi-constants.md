# GNMI — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-gnmi/telemetry/telemetry.go` (Go CLI フラグデフォルト、パス定数、JWT インターバル、gRPC メッセージサイズ)
- `sonic-net/sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` (環境変数・固定パス・SmartSwitch ZMQ ポート)
- `sonic-net/sonic-gnmi/gnmi_server/constants_native.go` (ENABLE_NATIVE_WRITE ビルドタグ定数)
- `sonic-net/sonic-gnmi/gnmi_server/constants_translib.go` (ENABLE_TRANSLIB_WRITE ビルドタグ定数)
- `sonic-net/sonic-gnmi/gnmi_server/jwtAuth.go` (JwtRefreshInt / JwtValidInt パッケージグローバル変数)

---

## 1. Unix ソケットパス (telemetry.go:175)

| 定数 | 値 | ソース |
|------|----|--------|
| `unix_socket` デフォルト | `/var/run/gnmi/gnmi.sock` | `telemetry.go:175` |

CONFIG_DB 対応フィールドなし。`gnmi-native.sh` から付与されないため常にデフォルト有効。

---

## 2. JWT 認証インターバル (telemetry.go:183-184)

| 定数 | 値 | ソース |
|------|----|--------|
| `jwt_refresh_int` | `900` 秒 | `telemetry.go:183` |
| `jwt_valid_int` | `3600` 秒 | `telemetry.go:184` |

`JwtRefreshInt` / `JwtValidInt` は `jwtAuth.go:17-18` で宣言。`telemetry.go:262-263` で代入。CONFIG_DB に対応フィールドなし。

---

## 3. 証明書シンボリックリンクパス (telemetry.go:199-201)

| 定数 | 値 | ソース |
|------|----|--------|
| `ca_cert_lnk` | `/keys/ca_cert.lnk` | `telemetry.go:199` |
| `server_cert_lnk` | `/keys/server_cert.lnk` | `telemetry.go:200` |
| `server_key_lnk` | `/keys/server_key.lnk` | `telemetry.go:201` |

`GNMI|certs.server_crt` が設定されている場合、`telemetry.go:306-310` で自動的に同一ディレクトリに変更される。

---

## 4. gRPC メッセージサイズ制限 (telemetry.go:209-210)

| 定数 | 値 | ソース |
|------|----|--------|
| `max_recv_msg_size` | `4 * 1024 * 1024` (4 MiB) | `telemetry.go:209` |
| `max_send_msg_size` | `4 * 1024 * 1024` (4 MiB) | `telemetry.go:210` |

CONFIG_DB 対応フィールドなし。大容量 Subscribe レスポンス時のボトルネックになる可能性。

---

## 5. gnmi-native.sh 固定環境変数・パス

| 定数 | 値 | ソース |
|------|----|--------|
| `GRPC_GO_LOG_VERBOSITY_LEVEL` | `99` | `gnmi-native.sh:26` |
| `GRPC_GO_LOG_SEVERITY_LEVEL` | `info` | `gnmi-native.sh:27` |
| `CVL_SCHEMA_PATH` | `/usr/sbin/schema` | `gnmi-native.sh:30` |
| `TELEMETRY_VARS_FILE` | `/usr/share/sonic/templates/telemetry_vars.j2` | `gnmi-native.sh:5` |
| SmartSwitch ZMQ ポート | `8100` | `gnmi-native.sh:91` |

`GRPC_GO_LOG_VERBOSITY_LEVEL=99` + `GRPC_GO_LOG_SEVERITY_LEVEL=info` の組み合わせで gRPC 内部ログが全量 stderr に出力される。

---

## 6. その他固定パス (telemetry.go)

| 定数 | 値 | ソース |
|------|----|--------|
| `img_dir` | `/tmp/host_tmp` | `telemetry.go:195` |
| `cert_crl_dir` | `/mtls/crl` | `telemetry.go:203` |
| `grpc_meta` | `/keys/grpc-version.json` | `telemetry.go:204` |
| `authz_meta` | `/keys/authz-version.json` | `telemetry.go:205` |
| `authorization_policy_file` | `/keys/authorization_policy.json` | `telemetry.go:207` |

---

## 7. ビルドタグ定数

| 定数 | デフォルト値 | ビルドタグ | ソース |
|------|------------|----------|--------|
| `ENABLE_NATIVE_WRITE` | `false` | `gnmi_native_write` 未指定時 | `constants_native.go:5` |
| `ENABLE_TRANSLIB_WRITE` | `false` | `gnmi_translib_write` 未指定時 | `constants_translib.go:5` |

管理フレームワーク統合ビルドでは `ENABLE_TRANSLIB_WRITE = true` となり、デフォルト認証モードが `password+jwt` に変わる。

---

## 出典

- `sonic-net/sonic-gnmi/telemetry/telemetry.go` L175, L183-184, L195, L199-201, L203-207, L209-210, L262-263, L303-313
- `sonic-net/sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` L5, L26-27, L30, L91
- `sonic-net/sonic-gnmi/gnmi_server/constants_native.go` L5
- `sonic-net/sonic-gnmi/gnmi_server/constants_translib.go` L5
- `sonic-net/sonic-gnmi/gnmi_server/jwtAuth.go` L17-18
