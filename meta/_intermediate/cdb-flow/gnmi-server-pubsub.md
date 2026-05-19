# GNMI_SERVER — Phase G 通信メカニズム スキャンノート

対象テーブル: `GNMI` / `GNMI_CLIENT_CERT` / `TELEMETRY_CLIENT`
Consumer: `gnmi-native.sh` + `/usr/sbin/telemetry` (dial-in)、`dialout_client_cli` (dial-out)
スキャン範囲: `gnmi-native.sh` 全行、`dialout_client.go` `watchConfig()` 周辺、`clientCertAuth.go:PopulateAuthStructByCommonName()`、`connection_manager.go` 全行

---

## 検出した購読メカニズム

### 1. GNMI | GNMI_CLIENT_CERT — 起動時スナップショット読み取り (購読なし)

- `gnmi-native.sh` は起動時に `sonic-cfggen -d -t telemetry_vars.j2` で CONFIG_DB を**一度だけ**スナップショット読み取りする (`gnmi-native.sh:19`)。
- `sonic-cfggen` は `GNMI` テーブル（`certs` / `gnmi` サブキー）と `DEVICE_METADATA["x509"]` を読む (`telemetry_vars.j2:2-4`)。
- 取得したフラグ一覧を組み立てた後、`exec /usr/sbin/telemetry ${TELEMETRY_ARGS}` でプロセスを置き換える (`gnmi-native.sh:150`)。
- **`telemetry` プロセス起動後は CONFIG_DB 変更を一切監視しない**。
  - `GNMI|gnmi` / `GNMI|certs` の変更を反映させるにはコンテナ再起動 (`docker restart docker-sonic-gnmi`) が必要。
- evidence: `gnmi-native.sh:19-150`

### 2. GNMI_CLIENT_CERT — 認証ごとの one-shot ConfigDB ルックアップ (購読なし)

- `telemetry` の gRPC 認証インターセプター内で `PopulateAuthStructByCommonName()` (`clientCertAuth.go:254`) が毎接続呼ばれる。
- 内部で `swsscommon.NewConfigDBConnector()` を生成し `Connect(false)` → `Get_entry(serviceConfigTableName, certCommonName)` で `GNMI_CLIENT_CERT|<cert_cname>` を読む。
- `Connect(false)` は永続接続なし (引数 `false` = wait_for_init 無効)。取得後に `DeleteConfigDBConnector_Native` でコネクタを破棄する。
- **Redis Subscribe / PSubscribe は使用しない**。`GNMI_CLIENT_CERT` テーブルの変更は次回の接続認証から即時有効になる（コンテナ再起動不要）。
- evidence: `clientCertAuth.go:259-284`

### 3. TELEMETRY_CLIENT — Redis keyspace PSUBSCRIBE (ランタイム購読)

- `dialout_client_cli` プロセスの `watchConfig()` 関数 (`dialout_client.go:648-746`) が CONFIG_DB に対して
  `PSUBSCRIBE "__keyspace@<dbId>__:TELEMETRY_CLIENT|*"` パターンを登録する。
- SubscribeAPI: `go-redis` v9 の `redisDb.PSubscribe()` を直接使用。swsscommon の `SubscriberStateTable` / `ConsumerStateTable` は**使用しない**。
- 起動時に既存 `TELEMETRY_CLIENT|*` エントリをスキャン (`KEYS "TELEMETRY_CLIENT|*"`) し、`processTelemetryClientConfig(ctx, redisDb, dbkey, "hset")` で初期適用する (`dialout_client.go:705-715`)。
- ランタイム: keyspace 通知を `pubsub.ReceiveTimeout(..., 1000ms)` のポーリングで受信し、payload が `hset` → SET ハンドラ、`del`/`hdel` → DEL ハンドラへ振り分ける (`dialout_client.go:731-738`)。
- evidence: `dialout_client.go:648-746`

### 4. TELEMETRY_CONNECTIONS — STATE_DB への副次書込 (Subscribe RPC 接続ごと)

- `gnmi_server/connection_manager.go` の `ConnectionManager.Add()` は Subscribe RPC の接続確立時に
  STATE_DB の `TELEMETRY_CONNECTIONS` ハッシュへ `HSet(table, key, "active")` を書き込む (`connection_manager.go:116`)。
- 接続切断時は `HDel(table, key)` で削除する (`connection_manager.go:127`)。
- 起動時に `PrepareRedis()` で STATE_DB に TCP 接続し `redis.Client` を保持する (`connection_manager.go:32-50`)。
- `rclient` は STATE_DB に直接 `go-redis` で接続。swsscommon 非経由。
- `TELEMETRY_CONNECTIONS` はダイレクト Redis アクセス (keyspace 通知なし、TTL なし)。
- evidence: `connection_manager.go:16,32-50,111-131`

---

## 購読方式サマリ

| テーブル | 方向 | API / 方式 | 購読者 | タイミング |
|---------|------|-----------|--------|----------|
| `GNMI\|certs` / `GNMI\|gnmi` | CONFIG_DB → デーモン (読み取り) | `sonic-cfggen` 一括スナップショット | `gnmi-native.sh` | コンテナ起動時 1 回のみ |
| `DEVICE_METADATA\|localhost` / `MGMT_VRF_CONFIG\|vrf_global` | CONFIG_DB → デーモン (読み取り) | `sonic-db-cli hget` 直接呼び出し | `gnmi-native.sh` | コンテナ起動時 1 回のみ |
| `GNMI_CLIENT_CERT\|<cert_cname>` | CONFIG_DB → デーモン (読み取り) | swsscommon ConfigDBConnector one-shot | `telemetry` 認証インターセプター | 接続認証ごと (ランタイム、変更即時有効) |
| `TELEMETRY_CLIENT\|*` | CONFIG_DB → デーモン (読み取り) | `go-redis PSUBSCRIBE` keyspace 通知 | `dialout_client_cli` | 起動時スキャン + ランタイム追従 |
| `STATE_DB:TELEMETRY_CONNECTIONS` | デーモン → STATE_DB (書き込み) | `go-redis HSet/HDel` 直接呼び出し | `telemetry` (connection_manager) | Subscribe RPC 接続/切断ごと |
