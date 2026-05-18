# CREDENTIALS|CERT (STATE_DB) — Phase G 通信メカニズム スキャンノート

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/certs.md`
対象テーブル: `STATE_DB CREDENTIALS|CERT|<profileID>`
Producer: `GNSICertzServer` (`sonic-gnmi/gnmi_server/gnsi_certz.go`)
Consumer: `sonic-mgmt-common/translib/transformer/xfmr_system.go`
スキャン範囲: `gnsi_certz.go:1036-1058` (writeCredentialsMetadataToDB), `xfmr_system.go:426-466` (Subscribe_grpc_server_xfmr), `xfmr_system.go:540-590` (DbToYang_grpc_server_xfmr)

---

## 検出した通信メカニズム

### 1. Producer: gnsi_certz.go → STATE_DB (直接 HSet)

`writeCredentialsMetadataToDB()` (`gnsi_certz.go:1036-1058`) は Redis keyspace notification ではなく
**直接 HSET** で STATE_DB に書き込む。Redis pub/sub チャンネルへの PUBLISH は行わない。

```go
func writeCredentialsMetadataToDB(tbl, key, fld, val string) error {
    sc, err := common_utils.GetRedisDBClient()  // STATE_DB に接続
    ...
    if err := sc.HSet(context.Background(), common_utils.GetKey([]string{tbl, key}), fld, val).Err(); err != nil {
        log.Error("Cannot write credentials metadata to the DB.")
    }
}
```

キー形式: `HSET CREDENTIALS|CERT|<profileID> <field> <value>`
Redis keyspace notification (`__keyspace@6__:CREDENTIALS|CERT|*`) は Redis サーバ設定 (`notify-keyspace-events`) が有効な場合のみ発行される。SONiC のデフォルト Redis 設定では有効。

### 2. Consumer: sonic-mgmt-common — gNMI OnChange 購読

`Subscribe_grpc_server_xfmr` (`xfmr_system.go:426-466`) が gNMI Subscribe RPC を受け取ったときの購読先を定義する:

```go
result.dbDataMap = RedisDbSubscribeMap{
    db.StateDB: map[string]map[string]map[string]string{
        CREDENTIALS_TBL: {
            "CERT|gnxi":           {},
            "PATHZ_POLICY|ACTIVE": {}},
    },
}
result.onChange = OnchangeEnable
result.nOpts = &notificationOpts{mInterval: 0, pType: OnChange}
```

| 購読先 | DB | テーブル | キー |
|--------|----|---------|------|
| STATE_DB | 6 | `CREDENTIALS` | `CERT\|gnxi` |
| STATE_DB | 6 | `CREDENTIALS` | `PATHZ_POLICY\|ACTIVE` |

購読モード: **OnChange** (`pType: OnChange`, `mInterval: 0`)。
`gnxi` はハードコード済み定数 `GNXI_ID = "gnxi"` (`xfmr_system.go:34`)。マルチプロファイル (`gnxi` 以外) は gNMI 経由では購読されない。

### 3. データ読み取り: DbToYang_grpc_server_xfmr

`DbToYang_grpc_server_xfmr` (`xfmr_system.go:540-590`) は OnChange 通知受信後または GET 要求時に
STATE_DB から `CREDENTIALS|CERT|gnxi` のすべてのフィールドを `GetEntry()` で取得し、
OpenConfig YANG (`openconfig-system:grpc-servers/grpc-server/state`) に変換する:

| STATE_DB フィールド | OpenConfig パス |
|------------------|--------------------|
| `certificate_version` | `gnsi-certz:certificate-version` |
| `ca_trust_bundle_version` | `gnsi-certz:ca-trust-bundle-version` |
| `certificate_revocation_list_bundle_version` | `gnsi-certz:certificate-revocation-list-bundle-version` |
| `authentication_policy_version` | `gnsi-certz:authentication-policy-version` |
| `certificate_created_on` | `gnsi-certz:certificate-created-on` (uint64, ナノ秒) |
| `ca_trust_bundle_created_on` | `gnsi-certz:ca-trust-bundle-created-on` |
| `certificate_revocation_list_bundle_created_on` | `gnsi-certz:certificate-revocation-list-bundle-created-on` |
| `authentication_policy_created_on` | `gnsi-certz:authentication-policy-created-on` |

`created_on` フィールドは `strconv.ParseUint()` で文字列 → uint64 変換される。変換失敗時はログのみで継続 (`xfmr_system.go:569-582`)。

### 4. 通信メカニズム サマリ

| 区間 | 方式 | チャンネル / パターン |
|------|------|--------------------|
| `gnsi_certz.go` → STATE_DB | 直接 `HSET` (pub/sub なし) | キー: `CREDENTIALS\|CERT\|<profileID>` |
| STATE_DB keyspace → translib | Redis keyspace notification (`__keyspace@6__`) | `__keyspace@6__:CREDENTIALS\|CERT\|gnxi` ※ |
| gNMI Subscribe → translib | `OnChange` (`Subscribe_grpc_server_xfmr`) | YANG path: `/openconfig-system:system/grpc-servers/...` |
| translib → gNMI client | gNMI `SubscribeResponse` | 更新検出ごとにプッシュ |

※ SONiC の Redis keyspace notification は `sonic-db-config` で `notify-keyspace-events KEA` 相当が設定されている場合のみ動作する。translib の `RedisDbSubscribeMap` 内部実装はこの通知を受けて `GetEntry()` を再実行する。

---

## evidence

- `sonic-gnmi/gnmi_server/gnsi_certz.go:1036-1058` — `writeCredentialsMetadataToDB()` (HSET 直接書き込み)
- `sonic-gnmi/common_utils/notification_producer.go:15-16` — `dbName="STATE_DB"` 定数
- `sonic-mgmt-common/translib/transformer/xfmr_system.go:29` — `CERT_TBL = "CREDENTIALS|CERT"`
- `sonic-mgmt-common/translib/transformer/xfmr_system.go:34` — `GNXI_ID = "gnxi"`
- `sonic-mgmt-common/translib/transformer/xfmr_system.go:112` — `XlateFuncBind("Subscribe_grpc_server_xfmr", ...)`
- `sonic-mgmt-common/translib/transformer/xfmr_system.go:426-466` — `Subscribe_grpc_server_xfmr` (OnChange 購読定義)
- `sonic-mgmt-common/translib/transformer/xfmr_system.go:540-590` — `DbToYang_grpc_server_xfmr` (フィールド変換)
