# GNMI_SERVER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-gnmi/telemetry/telemetry.go` (Go CLI フラグデフォルト、パス定数、JWT インターバル、gRPC メッセージサイズ)
- `sonic-net/sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` (環境変数・固定パス・SmartSwitch ZMQ ポート・終了コード)
- `sonic-net/sonic-gnmi/gnmi_server/constants_native.go` (ENABLE_NATIVE_WRITE ビルドタグ定数)
- `sonic-net/sonic-gnmi/gnmi_server/constants_translib.go` (ENABLE_TRANSLIB_WRITE ビルドタグ定数)
- `sonic-net/sonic-gnmi/gnmi_server/jwtAuth.go` (JwtRefreshInt / JwtValidInt パッケージグローバル変数)
- `sonic-net/sonic-gnmi/dialout/dialout_client_cli/dialout_client_cli.go` (dial-out クライアント固定デフォルト)

---

## 1. Unix ソケットパス (telemetry.go:175)

| 定数 | 値 | ソース |
|------|----|--------|
| `unix_socket` デフォルト | `/var/run/gnmi/gnmi.sock` | `telemetry.go:175` |

CONFIG_DB 対応フィールドなし。`gnmi-native.sh` から明示付与されないため、常にデフォルト `/var/run/gnmi/gnmi.sock` が有効。ローカル（TLS なし）接続パスとして利用される。

---

## 2. JWT 認証インターバル (telemetry.go:183-184)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `jwt_refresh_int` | `900` 秒 (15 分) | JWT トークンを期限切れ前にリフレッシュ可能な秒数 | `telemetry.go:183` |
| `jwt_valid_int` | `3600` 秒 (1 時間) | JWT トークンの有効期間 | `telemetry.go:184` |

`JwtRefreshInt` / `JwtValidInt` は `jwtAuth.go:17-18` でパッケージグローバル変数として宣言され、`telemetry.go:262-263` で代入される。CONFIG_DB に対応フィールドなし。gnmi-native.sh も付与しないため常に固定値。

---

## 3. 証明書シンボリックリンクパス (telemetry.go:199-201)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `ca_cert_lnk` | `/keys/ca_cert.lnk` | CA 証明書のシンボリックリンク生成先 | `telemetry.go:199` |
| `server_cert_lnk` | `/keys/server_cert.lnk` | サーバ証明書のシンボリックリンク生成先 | `telemetry.go:200` |
| `server_key_lnk` | `/keys/server_key.lnk` | サーバ秘密鍵のシンボリックリンク生成先 | `telemetry.go:201` |

`GNMI|certs.server_crt` が設定されている場合、`telemetry.go:306-310` にてシンボリックリンク先が自動的に `server_crt` と同一ディレクトリに変更される（デフォルト `/keys/*` からの上書き）。

---

## 4. gRPC メッセージサイズ上限 (telemetry.go:209-210)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `max_recv_msg_size` | `4 * 1024 * 1024` (4 MiB) | サーバが受信できる gRPC メッセージ最大サイズ | `telemetry.go:209` |
| `max_send_msg_size` | `4 * 1024 * 1024` (4 MiB) | サーバが送信できる gRPC メッセージ最大サイズ | `telemetry.go:210` |

CONFIG_DB 対応フィールドなし。大容量 Subscribe レスポンス（ポート数が多い場合など）では 4 MiB 上限がボトルネックになる可能性がある。

---

## 5. gnmi-native.sh 固定環境変数・パス・終了コード

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `EXIT_TELEMETRY_VARS_FILE_NOT_FOUND` | `1` | テンプレートファイル未存在時の終了コード | `gnmi-native.sh:3` |
| `INCORRECT_TELEMETRY_VALUE` | `2` | 設定値不正時の終了コード (`port` / `threshold` / `idle_conn_duration` 非数値) | `gnmi-native.sh:4` |
| `TELEMETRY_VARS_FILE` | `/usr/share/sonic/templates/telemetry_vars.j2` | CONFIG_DB → CLI フラグ変換テンプレートファイルパス | `gnmi-native.sh:5` |
| `GRPC_GO_LOG_VERBOSITY_LEVEL` | `99` | gRPC Go ライブラリ内部ログ冗長レベル (最大値 = 全量出力) | `gnmi-native.sh:26` |
| `GRPC_GO_LOG_SEVERITY_LEVEL` | `info` | gRPC Go ライブラリ内部ログ severity フィルタ | `gnmi-native.sh:27` |
| `CVL_SCHEMA_PATH` | `/usr/sbin/schema` | CVL (Config Validation Library) スキーマディレクトリパス | `gnmi-native.sh:30` |
| SmartSwitch ZMQ ポート | `8100` | `DEVICE_METADATA|localhost.subtype == "SmartSwitch"` 時に付与する `zmq_port` 値 | `gnmi-native.sh:91` |

`GRPC_GO_LOG_VERBOSITY_LEVEL=99` + `GRPC_GO_LOG_SEVERITY_LEVEL=info` は gRPC 内部ログを全量 stderr に出力する。これは `telemetry.go` 側の `-v` フラグ制御とは独立した gRPC ライブラリ固有の設定であり、`GNMI|gnmi.log_level` では制御できない。

---

## 6. その他固定パス (telemetry.go)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `img_dir` | `/tmp/host_tmp` | gNOI ファイル転送先の一時ディレクトリ | `telemetry.go:195` |
| `cert_crl_dir` | `/mtls/crl` | CRL (証明書失効リスト) ファイル格納ディレクトリ | `telemetry.go:203` |
| `grpc_meta` | `/keys/grpc-version.json` | gRPC 証明書メタデータ JSON ファイルパス | `telemetry.go:204` |
| `authz_meta` | `/keys/authz-version.json` | authz ポリシーメタデータ JSON ファイルパス | `telemetry.go:205` |
| `authorization_policy_file` | `/keys/authorization_policy.json` | authz ポリシー JSON ファイルパス (authz_policy_enabled=true 時に参照) | `telemetry.go:207` |

---

## 7. ビルドタグ定数

| 定数 | デフォルト値 | ビルドタグ | ソース |
|------|------------|----------|--------|
| `ENABLE_NATIVE_WRITE` | `false` | ビルドタグ `gnmi_native_write` 未指定時 | `constants_native.go:5` |
| `ENABLE_TRANSLIB_WRITE` | `false` | ビルドタグ `gnmi_translib_write` 未指定時 | `constants_translib.go:5` |

管理フレームワーク統合ビルド (`gnmi_translib_write` タグ付き) では `ENABLE_TRANSLIB_WRITE = true` となり、`telemetry.go:217-222` でデフォルト `user_auth` が `password+jwt` に変わる（コミュニティ版標準 SONiC ビルドでは `false`）。

---

## 8. dial-out クライアント固定デフォルト (dialout_client_cli.go:19-25)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SrcIp` | `""` (空文字列) | 送信元 IP アドレス初期値 | `dialout_client_cli.go:20` |
| `RetryInterval` | `30 * time.Second` (30 秒) | 接続再試行間隔初期値 | `dialout_client_cli.go:21, 31` |
| `Encoding` | `gpb.Encoding_JSON_IETF` | エンコーディング固定値 (DB から変更不可) | `dialout_client_cli.go:22` |
| `Unidirectional` | `true` | サーバ応答なし一方向モード固定 (DB から変更不可) | `dialout_client_cli.go:23, 32` |

`Encoding` と `Unidirectional` は `dialout_client.go:501-505` にて DB 読取値を強制上書きして固定値に戻す。`TELEMETRY_CLIENT|Global.encoding` / `.unidirectional` を CONFIG_DB で変更しても実際の動作は変わらない。

---

## 特記事項

1. **gRPC ログ vs telemetry ログの二重管理**: `GRPC_GO_LOG_VERBOSITY_LEVEL=99` は gRPC ライブラリ内部の冗長ログを全量有効化する。一方 `GNMI|gnmi.log_level` は `telemetry` の glog レベル (`-v` フラグ) のみ制御する。両者は独立しており、gRPC ライブラリのログを絞るには docker コンテナ起動スクリプトの書換が必要。
2. **JWT フィールドの CONFIG_DB 不在**: `jwt_refresh_int` (900s) / `jwt_valid_int` (3600s) は CONFIG_DB に対応エントリがなく、変更にはコンテナ内の `/usr/bin/gnmi-native.sh` 書換が必要（または `telemetry` バイナリに直接フラグ渡し）。
3. **SmartSwitch ZMQ ポート `8100` の固定性**: `GNMI|gnmi` テーブルには ZMQ ポート設定フィールドが存在しない。SmartSwitch では常に `8100` が使われる。Orchagent 側との合意値で変更する場合は両側の書換が必要。
4. **`/tmp/host_tmp` の揮発性**: gNOI ファイル転送先として `/tmp/host_tmp` が使われるが、これは tmpfs 上の一時ディレクトリ。コンテナ再起動で消える。大容量ファイル転送時は容量に注意。

---

## 出典

- `sonic-net/sonic-gnmi/telemetry/telemetry.go` L175, L183-184, L195, L199-201, L203-207, L209-210, L217-222, L262-263, L303-313 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh` L3-5, L26-27, L30, L91 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-net/sonic-gnmi/gnmi_server/constants_native.go` L5 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi/gnmi_server/constants_translib.go` L5 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi/gnmi_server/jwtAuth.go` L17-18 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi/dialout/dialout_client_cli/dialout_client_cli.go` L19-25, L31-32 (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
