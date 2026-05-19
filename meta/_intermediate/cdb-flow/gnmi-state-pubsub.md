# TELEMETRY_CONNECTIONS — Phase G 通信メカニズム スキャンノート

対象テーブル: `TELEMETRY_CONNECTIONS` (STATE_DB)
Consumer: `telemetry` デーモン (`sonic-gnmi`) の `ConnectionManager`、`show gnmi`（sonic-utilities）
スキャン範囲: `gnmi_server/connection_manager.go` 全行、`gnmi_server/server.go:866`、`gnmi-native.sh:19`、`dialout_client.go:648-746`

---

## 検出した購読メカニズム

### 1. TELEMETRY_CONNECTIONS — STATE_DB 直接書き込み (購読なし)

- `ConnectionManager.Add()` は Subscribe RPC の接続確立時に `rclient.HSet(ctx, table, key, "active")` で STATE_DB に直接書き込む (`connection_manager.go:116`)。
- `ConnectionManager.Remove()` は接続切断時に `rclient.HDel(ctx, table, key)` で削除する (`connection_manager.go:127`)。
- `PrepareRedis()` は起動時に `rclient.HGetAll` → 全 `HDel` で前回残留エントリをクリアする (`connection_manager.go:32-61`)。
- `go-redis` ライブラリを TCP で直接使用。swsscommon 非経由。keyspace 通知の PUBLISH なし。
- evidence: `connection_manager.go:16,32-61,111-131`

### 2. CONFIG_DB 購読なし

- `TELEMETRY_CONNECTIONS` テーブルは CONFIG_DB に存在しない。`telemetry` デーモンは `TELEMETRY_CONNECTIONS` に関して CONFIG_DB を購読しない。
- CONFIG_DB との通信は以下の独立したパスが存在するが、いずれも `TELEMETRY_CONNECTIONS` の書き込みとは直接連動しない:
  - `GNMI|certs` / `GNMI|gnmi`: `sonic-cfggen` スナップショット（起動時 1 回のみ）
  - `GNMI_CLIENT_CERT|<cert_cname>`: swsscommon ConfigDBConnector one-shot（接続認証ごと）
  - `TELEMETRY_CLIENT|*`: `go-redis PSUBSCRIBE` keyspace 通知（`dialout_client_cli` プロセス）

### 3. 読み取り consumer

- `show gnmi`（sonic-utilities）: `HGetAll(TELEMETRY_CONNECTIONS)` でアクティブ接続一覧を表示。ポーリング型（keyspace 通知登録なし）。
- `gnmi_server/server_test.go`: 単体テストの検証用 `HGetAll`。

---

## 購読方式サマリ

| テーブル | 方向 | API / 方式 | 購読者 | タイミング |
|---------|------|-----------|--------|----------|
| `TELEMETRY_CONNECTIONS` | デーモン → STATE_DB (書き込み) | `go-redis HSet/HDel` 直接呼び出し（swsscommon 非経由） | `telemetry` (connection_manager) | Subscribe RPC 接続/切断ごと |
| `TELEMETRY_CONNECTIONS` | STATE_DB → consumer (読み取り) | `go-redis HGetAll` 直接呼び出し | `show gnmi`、テストコード | 随時（ポーリング型） |

**結論**: `TELEMETRY_CONNECTIONS` は純粋な write-only ランタイム状態テーブルであり、CONFIG_DB 購読メカニズム（SubscriberStateTable / ConsumerStateTable / NotificationConsumer）は一切使用しない。変更通知の PUBLISH も発生しない。
