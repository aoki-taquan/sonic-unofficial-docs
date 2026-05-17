# TELEMETRY — Phase C 暗黙参照スキャンノート

対象テーブル: `TELEMETRY`
Consumer: `telemetry.sh` / `gnmi_server/server.go` (`sonic-gnmi`) / `docker-telemetry-entry.sh`
スキャン範囲: `telemetry.sh` 全行、`docker-telemetry-entry.sh` 全行、`telemetry_vars.j2` 全行、`gnmi_server/server.go` L380-660、`sonic-telemetry.yang` 全行

---

## 検出した暗黙参照テーブル

### 1. FEATURE|telemetry (CONFIG_DB) — コンテナ起動前提

`docker-telemetry-entry.sh` L39-48 が `redis-cli -n 4 HGET "FEATURE|telemetry" state` でポーリング。
`state == "enabled"` でなければ supervisord を起動しないため、TELEMETRY テーブルを読む前に FEATURE が設定されていることが必須。YANG leafref なし（実装上の暗黙依存）。

### 2. DEVICE_METADATA|localhost.x509 (CONFIG_DB) — legacy 証明書フォールバック

`telemetry_vars.j2` L4 が `DEVICE_METADATA["x509"]` を参照。`TELEMETRY|certs` が未設定の場合、`telemetry.sh` L66-80 は `DEVICE_METADATA|x509.server_crt` / `server_key` / `ca_crt` を証明書パスとして使用（legacy 経路）。YANG leafref なし。

### 3. GNMI_CLIENT_CERT (CONFIG_DB) — cert 認証時の参照テーブル

`telemetry.sh` L147-148 が `user_auth=cert` の場合に `--config_table_name GNMI_CLIENT_CERT` フラグを gnmi_server に渡す。gnmi_server が実行時に `GNMI_CLIENT_CERT` テーブルを参照してクライアント証明書の fingerprint チェックを行う。YANG leafref なし（引数経由の動的参照）。

### 4. STATE_DB DEVICE_METADATA|localhost.chassis_serial_number — 書き込み副作用

`telemetry.sh` L6-22: `TELEMETRY_WATCHDOG_SERIALNUMBER_PROBE_ENABLED=true` 環境変数が設定されている場合、`decode-syseeprom -s` でシリアル番号を取得し `STATE_DB HSET "DEVICE_METADATA|localhost" chassis_serial_number` へ書き込む。CONFIG_DB の TELEMETRY テーブルそのものとは独立した副作用（watchdog オプション機能）。

### 5. CONFIG_DB Journal (gnmi_server/server.go) — save_on_set 機能

`gnmi_server/server.go` L647-649: `save_on_set=true` が有効な場合、gnmi_server が `CONFIG_DB Journal` を開き、gNMI Set RPC の変更ログを記録する。CONFIG_DB 全体への横断的な書き込み参照。

---

## 暗黙参照サマリ

| 参照先 | DB | 参照方向 | 条件 | 証拠 |
|--------|-----|---------|------|------|
| `FEATURE\|telemetry.state` | CONFIG_DB | 読み取り（コンテナ起動制御） | 常時 | `docker-telemetry-entry.sh:40` |
| `DEVICE_METADATA\|localhost.x509` | CONFIG_DB | 読み取り（legacy 証明書フォールバック） | `TELEMETRY\|certs` 未設定時 | `telemetry_vars.j2:4`, `telemetry.sh:66-80` |
| `GNMI_CLIENT_CERT\|*` | CONFIG_DB | 読み取り（証明書 fingerprint チェック） | `user_auth=cert` 設定時 | `telemetry.sh:147-148` |
| `DEVICE_METADATA\|localhost.chassis_serial_number` | STATE_DB | 書き込み（シリアル番号更新） | watchdog オプション有効時 | `telemetry.sh:10-13` |
| CONFIG_DB Journal | CONFIG_DB | 書き込み（gNMI Set 変更ログ） | `save_on_set=true` 時 | `server.go:647-649` |

### SAI 参照

なし。telemetry (gnmi_server) は CONFIG_DB / STATE_DB / DATA_DB を gRPC/gNMI 経由でクライアントに公開するが、SAI/ASIC に直接アクセスしない。
