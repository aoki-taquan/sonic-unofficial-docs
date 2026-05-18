# CREDENTIALS|CERT 暗黙参照テーブル調査 (Phase C)

## 調査対象

`sonic-gnmi/gnmi_server/gnsi_certz.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
`sonic-gnmi/common_utils/notification_producer.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
`sonic-gnmi/telemetry/telemetry.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
`sonic-buildimage/files/build_templates/gnmi.service.j2`

## 調査結果

### `CREDENTIALS|CERT` は STATE_DB への書き出し専用

`gnsi_certz.go` の `writeCredentialsMetadataToDB()` (L1037) は `common_utils.GetRedisDBClient()` 経由で STATE_DB に直接接続し、`HSet()` で書き込む。CONFIG_DB からは一切読み込まない。

```go
// common_utils/notification_producer.go:16
dbName = "STATE_DB"

// gnsi_certz.go:1037-1058
func writeCredentialsMetadataToDB(tbl, key, fld, val string) error {
    sc, err := common_utils.GetRedisDBClient()
    ...
    err = sc.HSet(context.Background(), path, fld, val).Err()
    ...
}
```

### 起動時依存: database.service (systemd)

`gnmi.service.j2:3-4`:
```
Requires=database.service
After=database.service swss.service syncd.service
```
STATE_DB (Redis) が起動していなければ `writeEntityFreshness()` が失敗する。

### CLI フラグ由来の外部参照

証明書ファイルパスは CONFIG_DB ではなく telemetry バイナリの CLI フラグから取得:
- `--ca_cert_lnk` / `--server_cert_lnk` / `--server_key_lnk`: シンボリックリンクパス
- `--cert_crl_dir`: CRL ディレクトリ (`/mtls/crl`)
- `--grpc_meta`: JSON メタファイルパス (`/keys/grpc-version.json`)

これらは CONFIG_DB テーブルではなく、コンテナ起動引数として渡される (telemetry.go:196-204)。

### GNMI / TELEMETRY CONFIG_DB との関係

`GNMI` テーブル (`GNMI|certs` 等) は gnmi サーバ全体の設定を保持するが、`gnsi_certz.go` は直接 `GNMI` テーブルを読まない。
gnmi サーバの TLS 証明書パスはシンボリックリンク (`CaCertLnk` / `SrvCertLnk` / `SrvKeyLnk`) 経由で参照され、Certz Rotate で更新されると同ファイルが書き換えられる (gnmi_server/server.go:452, 429)。

### TELEMETRY_CONNECTIONS STATE_DB との関係

`gnmi_server/connection_manager.go:52` が `STATE_DB:TELEMETRY_CONNECTIONS` を読み取るが、これは接続管理 (gnmi 接続統計) であり `CREDENTIALS|CERT` テーブルとは独立したパス。

## まとめ

| 参照先 | 方向 | 条件 | evidence |
|-------|------|------|----------|
| STATE_DB (Redis インスタンス) | 書き出し専用 | 常時 (`writeCredentialsMetadataToDB`) | `common_utils/notification_producer.go:16` |
| `database.service` (systemd) | 起動順序依存 | gnmi.service 起動前提 | `gnmi.service.j2:3-4` |
| ファイルシステム (`CertzMetaFile`) | 読み取り (JSON プロファイル永続化) | 起動時 `loadCertzMetadata()` | `gnsi_certz.go:126,727` |
| ファイルシステム (`CertCRLConfig` ディレクトリ) | 読み書き (CRL バンドルファイル) | CRL Rotate 時 | `gnsi_certz.go:144-151,204` |
| TLS シンボリックリンク (`SrvCertLnk` 等) | 書き出し (Rotate で更新) | Rotate 確定時 (`finalizeProfile`) | `gnmi_server/server.go:429,452` |
| `GNMI` / `TELEMETRY` CONFIG_DB テーブル | 間接 (gnmi サーバ設定) | gnmi サーバ起動時 | telemetry パッケージ (certz とは独立パス) |

CONFIG_DB テーブルへの直接参照は **ゼロ**。外部参照はすべてファイルシステムまたは systemd 起動順序依存である。
