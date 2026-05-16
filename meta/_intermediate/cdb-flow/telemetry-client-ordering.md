# TELEMETRY_CLIENT — Phase B 書込み順依存スキャンノート

対象テーブル: `TELEMETRY_CLIENT`
Consumer: `dialout_client_cli` / `dialout/dialout_client/dialout_client.go` (`sonic-gnmi`)
スキャン範囲: `dialout_client.go` 全行精読、`supervisord.conf` 全行、`dialout.sh` 全行、`gnmi.service.j2` 全行
スキャン日: 2026-05-16

---

## 検出した順序依存・タイミング依存

### 1. DestinationGroup → Subscription 先行必須

- `processTelemetryClientConfig()` (`dialout_client.go:552-641`) が `Subscription_*` キーを処理する際、`cs.destGroupName` が空文字列の場合は `return nil` で**サイレントスキップ**する (`dialout_client.go:622-625`)。
- 起動時の一括読み込み (`DialOutRun` L706-715) は Redis `KEYS` コマンドの返却順序に依存する。`KEYS` は辞書順でも挿入順でもなくランダム順で返すため、`DestinationGroup_*` より先に `Subscription_*` が処理された場合は gRPC セッションが確立されない。
- **順序依存**: `TELEMETRY_CLIENT|DestinationGroup_<name>` を先に書き込み、その後 `TELEMETRY_CLIENT|Subscription_<name>` を書き込むこと。起動後のオンライン変更では keyspace notification 経由で再投入されるため問題ない。
- evidence: `dialout_client.go:552-641, 706-715`

### 2. gnmi-native (gNMI サーバ) 先行必須 — supervisord dependent_startup

- `supervisord.conf:58-68`: `dialout` プロセス (`dialout_client_cli`) は `dependent_startup_wait_for=gnmi-native:running` が設定されている。
- gnmi-native (gNMI サーバ) が `running` 状態になるまで dialout プロセスは起動しない。
- **順序依存**: `TELEMETRY_CLIENT` を読み込む `dialout_client_cli` は gNMI サーバ起動後にのみ実行される。gNMI サーバ起動前に CONFIG_DB に書き込んでおけば、dialout 起動時に一括読み込みで反映される。
- evidence: `supervisord.conf:68` (`dependent_startup_wait_for=gnmi-native:running`)

### 3. database.service → gnmi.service (systemd)

- `gnmi.service.j2:3-4`: `Requires=database.service`、`After=database.service swss.service syncd.service`。
- gnmi コンテナは Redis (CONFIG_DB) が起動してから開始する。`TELEMETRY_CLIENT` 読み込みは必ず Redis 起動後になる。
- **順序依存**: Redis 未起動時に `TELEMETRY_CLIENT` が参照されることはない（systemd After= による強制）。
- evidence: `gnmi.service.j2:3-4`

### 4. Global 設定変更時は全 DestinationGroup クライアントが再起動

- `processTelemetryClientConfig()` L508-512: `Global` キーを hset すると、`destGrpNameMap` の全グループに対して `closeDestGroupClient()` + `setupDestGroupClients()` を実行する。
- これにより `Global` の `src_ip` / `retry_interval` 変更が既存セッションに即時反映される（セッション再確立コスト発生）。
- **順序依存**: `Global` → `DestinationGroup` の順で書くと DestinationGroup 処理時に Global 設定が適用済みのため安全。逆順（DestinationGroup → Global）でも動作はするが、Global 変更時に全セッションが一度再起動される。
- evidence: `dialout_client.go:508-512`

### 5. `dialout_client_cli` は CVL スキーマを起動前に必要とする

- `dialout.sh:4`: `export CVL_SCHEMA_PATH=/usr/sbin/schema`。
- YANG CVL スキーマが `/usr/sbin/schema` にない場合、ConfigDBConnector の YANG バリデーションが失敗する可能性がある（ただし `dialout_client_cli` は直接 Redis に接続するため影響は限定的）。
- evidence: `dialout.sh:4`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `TELEMETRY_CLIENT\|DestinationGroup_<name>` → `TELEMETRY_CLIENT\|Subscription_<name>` | 先行推奨（逆順では Subscription がサイレントスキップ） | オンライン変更時は keyspace notification 再投入で自動回復 |
| 2 | `gnmi-native:running` → `dialout_client_cli` 起動 | supervisord dependent_startup 強制 | CONFIG_DB への書き込みは gnmi-native 起動前でも可（一括読み込みで反映） |
| 3 | `database.service` → `gnmi.service` 起動 | systemd After= 強制 | Redis 未起動で dialout が起動することはない |
| 4 | `Global` → `DestinationGroup` 書き込み推奨 | 推奨先行（逆順では Global 変更時に全セッション再起動コスト） | 機能上は逆順でも動作する |
| 5 | CVL スキーマ配置 (`/usr/sbin/schema`) → `dialout.sh` 起動 | コンテナビルド時に保証済み | 通常は自動 |
