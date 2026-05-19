# gnmi-dialin — Phase G pubsub 調査証跡

調査日: 2026-05-19
対象ページ: docs/reference/config-db/gnmi-dialin.md
対象テーブル: GNMI|gnmi, GNMI|certs

## 主な調査結果

### GNMI|gnmi / GNMI|certs — ポイントインタイム読み取り (Pub/Sub なし)

- `gnmi-native.sh` は起動時に `sonic-cfggen -d -t telemetry_vars.j2` を 1 回実行してスナップショットを取得する
- テンプレート `telemetry_vars.j2` は `GNMI["gnmi"]`, `GNMI["certs"]`, `DEVICE_METADATA["x509"]` を JSON 化する
- コンテナ稼働中の CONFIG_DB 変更は `telemetry` プロセスに通知されない — コンテナ再起動のみ反映手段
- 例外: TLS 証明書ファイルは `fsnotify` で動的リロードされるが、ファイルシステム監視であり CONFIG_DB テーブルの Pub/Sub ではない

### GNMI_CLIENT_CERT — 接続ごとポイントインタイム読み取り

- `clientCertAuth.go:PopulateAuthStructByCommonName()` が各 gNMI RPC 接続時に
  `ConfigDBConnector.Connect(false).Get_entry()` で `GNMI_CLIENT_CERT|<CN>` を読み取る
- Subscribe ではなく都度読み取りのため、エントリ追加/削除はコンテナ再起動不要で即時反映される

### DEVICE_METADATA|localhost.hwsku — RPC ごとポイントインタイム読み取り

- `pkg/bypass/bypass.go:IsAllowedSKU()` が SmartSwitch 向け gNMI Set RPC 時に
  `ConfigDBConnector.Get_entry()` で hwsku を読み取り CVL bypass 判定を行う

### TELEMETRY_CLIENT — PSUBSCRIBE (dial-out モード)

- `dialout_client.go:DialOutRun()` が `PSUBSCRIBE "__keyspace@<N>__:TELEMETRY_CLIENT|*"` を張り
  dial-out テレメトリ設定の変更をリアルタイム監視する
- 初回スナップショット (`KEYS TELEMETRY_CLIENT|*`) + 差分通知の 2 段構成

### gNMI Subscribe RPC — 任意 DB テーブルの keyspace 購読

- gNMI Subscribe RPC 受信時、`db_client.go:dbTableKeySubscribe()` が要求パスに対応する
  Redis DB へ `PSubscribe __keyspace@<N>__:<table>|<key>*` を張る
- `GNMI|gnmi` テーブル自体は監視対象外

## evidence refs

- sonic-net/sonic-buildimage:dockers/docker-sonic-gnmi/gnmi-native.sh:19-22
- sonic-net/sonic-buildimage:dockers/docker-sonic-gnmi/telemetry_vars.j2:1-5
- sonic-net/sonic-gnmi:telemetry/telemetry.go:453-456
- sonic-net/sonic-gnmi:gnmi_server/clientCertAuth.go:259-261
- sonic-net/sonic-gnmi:pkg/bypass/bypass.go:148-168
- sonic-net/sonic-gnmi:dialout/dialout_client/dialout_client.go:646-745
- sonic-net/sonic-gnmi:sonic_data_client/db_client.go:1419-1447
