# Cross-refs 調査メモ: SECURITY_PROFILES / PKI テーブル (Phase C)

## 調査対象

- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-security-global.yang`
- `sonic-gnmi/gnmi_server/gnsi_certz.go`
- `sonic-gnmi/common_utils/notification_producer.go`

## 発見した参照関係

### 1. YANG leafref: SECURITY_GLOBAL → SECURITY_PROFILES

`sonic-security-global.yang:29-35` にて `SECURITY_GLOBAL|global.security_profile` が
`/spki:sonic-pki/spki:SECURITY_PROFILES/spki:SECURITY_PROFILES_LIST/spki:profile-name`
への leafref として定義されている。CVL バリデーション時に参照整合性が強制される。

### 2. STATE_DB: CREDENTIALS|CERT|<profileID>

`gnsi_certz.go:1036-1059` の `writeCredentialsMetadataToDB()` が
`common_utils.GetRedisDBClient()` 経由で STATE_DB に書き込む。
`notification_producer.go:16` にて `dbName = "STATE_DB"` と定数定義されている。

書き込みパス: `CREDENTIALS|CERT|<profileID>` (GetKey で `|` 区切り結合)
- `gnsi_certz.go:46-48` 定数: `certTbl = "CERT"`, `credentialsTbl = "CREDENTIALS"`
- `gnsi_certz.go:1046` パス構築: `common_utils.GetKey([]string{credentialsTbl, tbl})` + key

### 3. CONFIG_DB 参照なし (ハンドラ未実装)

`clientCertAuth.go:259-276` が `ConfigDBConnector.Get_entry(serviceConfigTableName, ...)` を呼ぶが、
serviceConfigTableName は `"GNMI_CLIENT_CERT"` テーブルを指す (server_test.go:6352 で確認)。
`SECURITY_PROFILES` を直接読む production コードは community master で未確認。

## 結論

- `SECURITY_PROFILES` ↔ `SECURITY_GLOBAL` は YANG leafref でのみ連携 (CVL バリデーション層)
- gNSI Certz が書き込む STATE_DB テーブルは `CREDENTIALS|CERT` であり `SECURITY_PROFILES` とは独立
- `GNMI_CLIENT_CERT` テーブルはクライアント証明書の CN ↔ ロールマッピング用の別テーブル
- certmgr デーモンは community master のソースで存在を確認できない
