# TELEMETRY — 失敗挙動調査メモ (Phase D)

調査日: 2026-05-17
ソース:
- `sonic-gnmi/gnmi_server/server.go` (eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-gnmi/telemetry/telemetry.go`
- `sonic-buildimage/dockers/docker-sonic-telemetry/telemetry.sh`
- `sonic-buildimage/dockers/docker-sonic-telemetry/supervisord.conf`

## 1. autorestart=false — 起動失敗時にコンテナが孤立

`supervisord.conf` の `[program:telemetry]` は `autorestart=false`。
`telemetry.sh` がエラーコード 1 (`EXIT_TELEMETRY_VARS_FILE_NOT_FOUND`) または
2 (`INCORRECT_TELEMETRY_VALUE`) で終了しても supervisord は再起動しない。
`dialout` も `dependent_startup_wait_for=telemetry:running` のため起動しない。

確認: `supervisorctl status telemetry` → `EXITED` ならコンテナは動いているが gNMI は死亡。

## 2. 設定ファイル不在エラー (exitcode=1)

`TELEMETRY_VARS_FILE=/usr/share/sonic/templates/telemetry_vars.j2` が存在しない場合:
```
Telemetry vars template file not found
exit 1
```
パッケージ再インストールが必要。

## 3. 不正フィールド値エラー (exitcode=2)

以下のフィールド値が不正な場合 `telemetry.sh` が `exit 2` で終了:

| フィールド | 期待値 | 不正例 | エラーメッセージ |
|-----------|--------|--------|----------------|
| `TELEMETRY\|gnmi.port` | 正整数文字列 | `"abc"`, `"-1"` | `Incorrect port value <PORT>, expecting positive integers` |
| `TELEMETRY\|gnmi.threshold` | 正整数文字列 | `"abc"` | `Incorrect threshold value, expecting positive integers` |
| `TELEMETRY\|gnmi.idle_conn_duration` | 正整数文字列 | `"abc"` | `Incorrect idle_conn_duration value, expecting positive integers` |

いずれも `telemetry.sh` が stderr に出力後 `exit 2` → supervisord は再起動しない。
復旧: `sonic-db-cli CONFIG_DB HSET 'TELEMETRY|gnmi' port 50051` で修正後、コンテナ再起動。

## 4. 証明書関連の起動エラー (gnmi_server/server.go SrvAdvConfig)

`SrvAdvConfig()` が以下の場合にエラーを返し、gNMI サーバが起動しない:

| 条件 | エラーメッセージ |
|------|----------------|
| `server_crt` XOR `server_key` が空 | `"server certificate or key file path is empty"` |
| `server_crt` ファイルが存在しない | `"server certificate file stat error: <os.Stat error>"` |
| `server_key` ファイルが存在しない | `"server key file stat error: <os.Stat error>"` |
| `ca_crt` ファイルが存在しない | `"CA certificate file not found: <os.Stat error>"` |
| CRL ディレクトリ `<crl_expire_duration>/crl/` が存在しない | `os.ReadDir error` |

`telemetry.go` の `startGNMIServer()` はこれらのエラーを受けて `log.Errorf` → `return`。
supervisord はプロセス終了を検知するが `autorestart=false` のため再起動しない。

## 5. 証明書ロード失敗時の待機ループ (telemetry.go)

`tls.LoadX509KeyPair()` が失敗した場合 (証明書ファイルが存在するが内容不正など):
```go
log.Errorf("could not load server key pair: %s", err)
for {
    serverControlValue := <-serverControlSignal
    if serverControlValue == ServerStop {
        return
    }
    if serverControlValue == ServerStart {
        break // retry loading certs after cert has been written or created
    }
}
continue
```
fsnotify (inotify) でファイル変更を検知し `ServerStart` シグナルを受けるとリトライ。
証明書ファイルを正しい内容に上書きすれば自動回復する (再起動不要)。
> evidence: `telemetry/telemetry.go:463-470`

## 6. リスナーポート競合 — TCP 縮退動作

`config.Port` 番ポートへの `net.Listen("tcp", ...)` が失敗した場合:
```
log.Warningf("Failed to open listener port <port>: <err>; disabling TCP listener", ...)
```
TCP リスナーを無効化して処理を継続する (UnixSocket が設定されていれば UDS のみで動作)。
UDS も未設定の場合は `"no listener configured"` エラーで `NewServer()` が返す。
> evidence: `gnmi_server/server.go:593-600, 643`

## 7. save_on_set 失敗 — dbus エラー

`save_on_set=true` 設定中に gNMI Set RPC が完了した後 `SaveOnSetEnabled()` が dbus 経由で
`config save` を呼ぶ。dbus クライアント生成失敗:
```
log.V(0).Infof("Saving startup config failed to create dbus client: %v", err)
```
config save 失敗:
```
log.V(0).Infof("Saving startup config failed: %v", err)
```
いずれも Set RPC 自体は成功するが CONFIG_DB 変更が永続化されない。サイレント失敗。
> evidence: `gnmi_server/server.go:1054-1061`

## 8. user_auth 不正値 — AuthTypes.Set() エラー

`user_auth` に `"cert"`, `"password"`, `"jwt"`, `"none"`, `""` 以外の値を設定した場合:
```
fmt.Errorf("Expecting one or more of 'cert', 'password' or 'jwt'")
```
`telemetry.sh` は `--client_auth <USER_AUTH>` をそのまま渡し、gnmi_server 起動時に検証される。
不正値の場合 `startGNMIServer()` がエラーを返してプロセス終了 → autorestart=false。
> evidence: `gnmi_server/server.go:315-327`

## まとめ — 回復手順

| 障害 | 検知 | 回復 |
|------|------|------|
| 不正フィールド値 (port/threshold/idle_conn_duration) | supervisorctl status → EXITED | `sonic-db-cli` で修正 → `docker restart telemetry` |
| 証明書ファイル不在 | supervisorctl status → EXITED | ファイル配置 → `docker restart telemetry` |
| 証明書内容不正 | 自動待機ループ | ファイル上書き → 自動回復 (再起動不要) |
| ポート競合 | TCP disabled (Warning ログ) | ポート解放 → `docker restart telemetry` |
| save_on_set dbus 失敗 | ログのみ | dbus / hostcfgd 確認 |
