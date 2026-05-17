# TELEMETRY — Phase G 通信メカニズム調査

対象テーブル: `TELEMETRY`
Consumer: `telemetry` コンテナ (`docker-sonic-telemetry`) / `sonic-gnmi` バイナリ
スキャン範囲: `telemetry/telemetry.go`、`dockers/docker-sonic-telemetry/telemetry.sh`、`gnmi_server/server.go`

---

## 結論

`TELEMETRY` テーブルに対する **継続的な Redis pub/sub 購読は存在しない**。

`sonic-cfggen -d -t telemetry_vars.j2` による**起動時スナップショット読み取り**が唯一の CONFIG_DB アクセス経路である。`ConfigDBConnector.subscribe()` / `listen()` / `swsscommon.SubscriberStateTable` は一切使用しない。

## 読み取り経路の詳細

### 起動時スナップショット (telemetry.sh)

`telemetry.sh` は起動時に `sonic-cfggen -d -t $TELEMETRY_VARS_FILE` を実行し、`TELEMETRY|certs` / `TELEMETRY|gnmi` を JSON 形式で一括取得する。取得した値はシェル変数 `CERTS` / `GNMI` に保持され、`telemetry` / `gnmi_server` バイナリへのコマンドライン引数 (`TELEMETRY_ARGS`) に変換される。

- evidence: `telemetry.sh:40-43` (`sonic-cfggen` 呼び出し)

```bash
TELEMETRY_VARS=$(sonic-cfggen -d -t $TELEMETRY_VARS_FILE)
GNMI=$(echo $TELEMETRY_VARS | jq -r '.gnmi')
CERTS=$(echo $TELEMETRY_VARS | jq -r '.certs')
```

### バイナリ起動後 — CONFIG_DB 参照なし

`telemetry.go` の `runTelemetry()` はフラグ解析後に `gnmi.NewServer()` を呼ぶだけで、起動後に CONFIG_DB を再読みする処理はない。`swsscommon.LoggerLinkToDbNative("telemetry")` のみがバイナリ内の DB アクセスであり、これはロガーリンクの設定であって TELEMETRY テーブルの読み取りではない。

- evidence: `telemetry/telemetry.go:111` (`LoggerLinkToDbNative`)

### GNMI_CLIENT_CERT テーブル — 実行時参照 (user_auth=cert)

`user_auth=cert` の場合、gNMI クライアント認証時に `ClientCertAuthenAndAuthor()` が `GNMI_CLIENT_CERT` テーブルをリクエストごとに参照する。これは `TELEMETRY` テーブルへの購読ではなく、接続認可テーブルへのポイント読み取りである。

- evidence: `gnmi_server/server.go:792` (`ClientCertAuthenAndAuthor`)

## 変更反映の仕組み

CONFIG_DB の `TELEMETRY` テーブル値を変更しても、実行中の `telemetry` コンテナには**自動で反映されない**。

| 変更の種類 | 反映タイミング | 操作 |
|-----------|--------------|------|
| `TELEMETRY|gnmi` フィールド変更 | コンテナ再起動後 | `systemctl restart telemetry` |
| `TELEMETRY|certs` フィールド変更 | コンテナ再起動後 | `systemctl restart telemetry` |
| TLS 証明書ファイルの内容更新 | inotify 検出で自動再起動 | `fsnotify.Watcher` が cert ディレクトリを監視 (`telemetry.go:340-404`) |

TLS 証明書ファイルの**内容**変更のみ例外で、`iNotifyCertMonitoring()` が `.cert`/`.crt`/`.cer`/`.pem`/`.key` ファイルの変更を検出し、`serverControlSignal <- ServerStart` でサーバを自動再起動する (`telemetry.go:363-379`)。

## 購読テーブル一覧

| テーブル | 購読方式 | 購読者 | ハンドラ |
|---------|---------|--------|---------|
| `TELEMETRY` | **なし**（起動時スナップショットのみ） | `telemetry.sh` (sonic-cfggen) | — |
| `GNMI_CLIENT_CERT` | ポイント読み取り (HGETALL) | `gnmi_server` (認証時) | `ClientCertAuthenAndAuthor` |

## 結論

`TELEMETRY` は「購読型 (event-driven)」ではなく「起動時読み取り型 (snapshot)」の消費パターン。変更を反映させるには必ずコンテナ再起動が必要であり、この制約は YANG / CLI ドキュメントには明示されていないが `telemetry.sh` と `telemetry.go` の実装から確認できる。
