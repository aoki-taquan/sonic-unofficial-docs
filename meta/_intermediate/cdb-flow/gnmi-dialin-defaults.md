# gnmi-dialin Phase A — コード由来デフォルト調査メモ

調査日: 2026-05-14
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase A (コード由来デフォルト)

## 調査対象ソース

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `telemetry/telemetry.go` | sonic-net/sonic-gnmi | eb635b76 | Go バイナリのエントリポイント。`setupFlags()` でフラグデフォルト値を定義 |
| `dockers/docker-sonic-gnmi/gnmi-native.sh` | sonic-net/sonic-buildimage | 9ea932ec | 起動スクリプト。CONFIG_DB から設定を読み取り CLI フラグへ変換 |
| `src/sonic-yang-models/yang-models/sonic-gnmi.yang` | sonic-net/sonic-buildimage | 9ea932ec | YANG スキーマ定義 |
| `dockers/docker-sonic-gnmi/telemetry_vars.j2` | sonic-net/sonic-buildimage | 9ea932ec | Jinja2 テンプレート。`GNMI|gnmi`, `GNMI|certs` を読み取る |
| `tests/db_migrator_input/config_db/gnmi-*.json` | sonic-net/sonic-utilities | — | テストケース。フィールド値の実例 |

## デフォルト値まとめ

### `GNMI|gnmi` フィールド

| フィールド | YANG default | Go flag default | シェル fallback | 確定デフォルト |
|-----------|-------------|-----------------|----------------|--------------|
| `port` | 未宣言 | `-1` (必須) | `8080` (テーブル欠如時) | **8080** (シェル) / 必須 (テーブルあり) |
| `log_level` | 未宣言 | `2` | `2` (非数字時) | **2** |
| `client_auth` | 未宣言 | `false` | `false` → `--allow_no_client_auth` | **false** |
| `threshold` | 未宣言 | `100` | `100` (null 時) | **100** |
| `idle_conn_duration` | 未宣言 | `5` | `5` (null 時) | **5** 秒 |
| `save_on_set` | 未宣言 | `false` | **読まれない** (dead field) | **false** (Go デフォルト) |
| `enable_crl` | 未宣言 | `false` | `false` ("true" 以外) | **false** |
| `crl_expire_duration` | 未宣言 | `86400` | 未読 → Go default | **86400** 秒 (24h) |
| `user_auth` | 未宣言 | 全 false | `cert` (null 補完) | **cert** |

### `GNMI|certs` フィールド

| フィールド | YANG default | fallback |
|-----------|-------------|---------|
| `ca_crt` | 未宣言 | 未設定 → CA 検証なし |
| `server_crt` | 未宣言 | 未設定 → `--insecure` |
| `server_key` | 未宣言 | 未設定 → `--insecure` |

### ハードコード定数 (telemetry.go)

| 定数 | 値 | 行 |
|------|----|----|
| `unix_socket` | `/var/run/gnmi/gnmi.sock` | L175 |
| `jwt_refresh_int` | `900` 秒 | L183 |
| `jwt_valid_int` | `3600` 秒 | L184 |
| `max_recv_msg_size` | `4194304` (4 MiB) | L209 |
| `max_send_msg_size` | `4194304` (4 MiB) | L210 |
| TLS 最小バージョン | `TLS 1.2` | L482 |
| keepalive MinTime | `20` 秒 | L547 |

## 主要な発見・Discrepancy

1. **`save_on_set` dead field**: YANG で定義されているが `gnmi-native.sh` が読み取らない。`--with-save-on-set` Go フラグを手動指定しなければ有効にならない。

2. **`port` の二重デフォルト**: テーブル欠如時は `8080` (シェル)、テーブル存在時は必須フィールドとなる。Go バイナリ自体のデフォルトは `-1` であり、`0 以下 = 起動エラー` のため port は事実上必須。

3. **`user_auth` vs `client_auth` の区別**: `client_auth` (boolean) は TLS クライアント証明書の強制有無を制御し、`user_auth` (string) は認証方式を制御する。両者は独立したフラグ (`--allow_no_client_auth` と `--client_auth`) に変換される。

4. **`user_auth=cert` と `ca_crt` の依存**: `user_auth=cert` 設定時に `ca_crt` が未設定だと、シェルスクリプトと Go 両方で `cert` 認証が自動無効化される (silent fallback)。

5. **TELEMETRY → GNMI 移行**: `db_migrator.py:migrate_gnmi()` (L634) が旧 `TELEMETRY` テーブルから `GNMI` テーブルへ自動移行。両方存在する場合は `GNMI` が優先。

## 証跡

- `telemetry/telemetry.go:171-328`: `setupFlags()` 関数全体
- `dockers/docker-sonic-gnmi/gnmi-native.sh:63-150`: CONFIG_DB 読み取りと引数構築
- `sonic-gnmi.yang`: YANG スキーマ (default 宣言なし)
- `tests/db_migrator_input/config_db/gnmi-configdb-expected.json`: `port: "50051"`, `log_level: "2"`, `client_auth: "true"`
- `tests/db_migrator_input/config_db/gnmi-minigraph-expected.json`: `port: "50052"`
