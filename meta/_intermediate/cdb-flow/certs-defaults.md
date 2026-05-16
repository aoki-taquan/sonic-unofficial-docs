# Phase A 調査メモ: CREDENTIALS|CERT (STATE_DB) / gNSI Certz 証明書バンドル

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/certs.md`  
調査者: Claude (batch #6)

---

## 1. grep entry (1回のみ)

```
grep -rn "certTbl\|\"CERT\"\|CREDENTIALS" /home/coder/sonic-unofficial-docs/.cache/sonic-sources/sonic-gnmi/
```

結果:
- `gnmi_server/gnsi_certz.go:32`: `certTbl string = "CERT"`
- `gnmi_server/gnsi_certz.go:48`: `credentialsTbl string = "CREDENTIALS"`
- `gnmi_server/gnsi_certz.go:713-714`: `writeCredentialsMetadataToDB(certTbl, profileID, ...)` — STATE_DB への書き込み

---

## 2. ソース精読結果

### sonic-gnmi/gnmi_server/gnsi_certz.go — 全行精読

#### 定数 (L29-49)

```go
const (
    defaultProfile string = "gnxi"
    // DB entry prefixes
    certTbl  string = "CERT"
    certId   string = "certificate"
    tbId     string = "ca_trust_bundle"
    crlId    string = "certificate_revocation_list_bundle"
    authId   string = "authentication_policy"
    // DB entry suffixes
    versionFld string = "_version"
    createdFld string = "_created_on"
    // CRL
    crlDefault string = "crl"
    backupExt  string = ".bak"
    credentialsTbl string = "CREDENTIALS"
)
```

**重要**: `credentialsTbl = "CREDENTIALS"` と `certTbl = "CERT"` が組み合わさり、DB キーは `CREDENTIALS|CERT|<profileID>` になる。

#### STATE_DB キー構造 (`writeCredentialsMetadataToDB` L1036-1058)

```go
path := common_utils.GetKey([]string{credentialsTbl, tbl})  // "CREDENTIALS|CERT"
if len(key) > 0 {
    path = common_utils.GetKey([]string{path, key})          // "CREDENTIALS|CERT|gnxi"
}
sc.HSet(ctx, path, fld, val)
```

`GetKey` は `strings.Join(k, "|")` — パイプ区切り。
対象 DB: `common_utils/notification_producer.go:16` — `dbName = "STATE_DB"`

#### フィールド一覧 (`writeEntityFreshness` L688-715)

| entityType | version フィールド | created_on フィールド |
|-----------|-------------------|--------------------|
| certType  | `certificate_version` | `certificate_created_on` |
| tbType    | `ca_trust_bundle_version` | `ca_trust_bundle_created_on` |
| crlType   | `certificate_revocation_list_bundle_version` | `certificate_revocation_list_bundle_created_on` |
| apType    | `authentication_policy_version` | `authentication_policy_created_on` |

#### コード由来のデフォルト値

| フィールド | デフォルト値 | ソース |
|-----------|------------|--------|
| `certificate_version` (bootstrap 時) | `"V1"` | `gnsi_certz.go:188` — `bootstrapDefaultProfile()` |
| `ca_trust_bundle_version` (bootstrap 時) | `"V1"` | `gnsi_certz.go:195` |
| `certificate_revocation_list_bundle_version` (bootstrap 時) | `"V1"` | `gnsi_certz.go:202` |
| `authentication_policy_version` (bootstrap 時) | `"V1"` | `gnsi_certz.go:209` |
| `*_created_on` (bootstrap 時) | `time.Now().UnixNano()` の文字列+"000000000" | `gnsi_certz.go:180,693-695` |
| プロファイル ID (デフォルト) | `"gnxi"` | `gnsi_certz.go:30` |

注: `created_on` の格納値は `strconv.FormatUint(entity.CreatedOn, 10) + "000000000"` (L693-695)。
`entity.CreatedOn` は `bootstrapDefaultProfile()` で `uint64(time.Now().UnixNano())` をナノ秒で取得 (L180)。
Rotate RPC では `entityMsg.GetCreatedOn()` (クライアント指定値、秒単位) + `"000000000"` として格納する (L693)。

#### バリデーション (Rotate RPC 時)

- `created_on == 0` の場合 → `codes.InvalidArgument`: `"created_on cannot be empty"` (L389-391)
- `version == ""` の場合 → `codes.InvalidArgument`: `"version cannot be empty"` (L392-394)
- trust bundle の encoding は `CERTIFICATE_ENCODING_PEM` のみ (L520-522)
- trust bundle の type は `CERTIFICATE_TYPE_X509` のみ (L517-519)
- CRL bundle が空の場合 → `codes.InvalidArgument` (L795-796)
- CRL encoding は `CERTIFICATE_ENCODING_PEM` のみ (L801-803)

### sonic-gnmi/telemetry/telemetry.go — 証明書パス CLI フラグデフォルト

| フラグ | デフォルト値 | 対応する Config フィールド |
|-------|------------|--------------------------|
| `ca_cert_lnk` | `"/keys/ca_cert.lnk"` | `Config.CaCertLnk` |
| `server_cert_lnk` | `"/keys/server_cert.lnk"` | `Config.SrvCertLnk` |
| `server_key_lnk` | `"/keys/server_key.lnk"` | `Config.SrvKeyLnk` |
| `ca_crt` | `""` (必須ではない) | `Config.CaCertFile` |
| `server_crt` | `""` (必須) | `Config.SrvCertFile` |
| `server_key` | `""` (必須) | `Config.SrvKeyFile` |
| `cert_crl_dir` | `"/mtls/crl"` | `Config.CertCRLConfig` |
| `grpc_meta` | `"/keys/grpc-version.json"` | `Config.CertzMetaFile` |
| `integrity_manifest_file` | `""` | `Config.IntManFile` |

ソース: `telemetry/telemetry.go:196-204`

シンボリックリンクデフォルトの自動調整 (L303-310):
- `CaCertFile` が空でなく `CaCertLnk == "/keys/ca_cert.lnk"` の場合 → `CaCertLnk = dir(CaCertFile)/ca_cert.lnk`
- `SrvCertFile` が空でなく `SrvCertLnk == "/keys/server_cert.lnk"` の場合 → `SrvCertLnk = dir(SrvCertFile)/server_cert.lnk`
- `SrvKeyFile` が空でなく `SrvKeyLnk == "/keys/server_key.lnk"` の場合 → `SrvKeyLnk = dir(SrvKeyFile)/server_key.lnk`

### sonic-gnmi/common_utils/notification_producer.go

- L16: `dbName = "STATE_DB"` — `CREDENTIALS|CERT|<profileID>` は CONFIG_DB ではなく STATE_DB に書き込まれる
- L95-97: `GetKey` = `strings.Join(k, "|")`

---

## 3. 乖離・注意点

1. **CONFIG_DB ではなく STATE_DB**: `CREDENTIALS|CERT` は STATE_DB テーブル。`certs.md` はリファレンスセクションに配置するが、STATE_DB の読み取り専用テーブルであることを明記する。
2. **`created_on` の単位変換**: `bootstrapDefaultProfile()` はナノ秒で取得するが、Rotate RPC では `GetCreatedOn()` が秒で返す。常に `"000000000"` suffix を付加して「疑似ナノ秒」文字列とする — 事実上すべてのエントリで `created_on` は 19 桁の数値文字列になる。
3. **`CERT_BUNDLE` という CONFIG_DB テーブルは存在しない**: `ca_trust_bundle` は STATE_DB フィールド名の一部 (prefix)。
4. **bootstrap の `Final: true`**: `bootstrapDefaultProfile()` が生成する全エンティティは `Final: true` で生成され、`revertProfile()` ではロールバックされない。

---

## 4. evidence 行

- `sonic-gnmi/gnmi_server/gnsi_certz.go:29-49` — 定数定義 (certTbl, credentialsTbl, フィールド名 prefix/suffix)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:178-222` — `bootstrapDefaultProfile()` (Version="V1", CreatedOn=time.Now().UnixNano())
- `sonic-gnmi/gnmi_server/gnsi_certz.go:688-715` — `writeEntityFreshness()` (フィールド名生成とDB書き込み)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:1036-1058` — `writeCredentialsMetadataToDB()` (STATE_DB, キー = CREDENTIALS|CERT|profileID)
- `sonic-gnmi/common_utils/notification_producer.go:16` — `dbName = "STATE_DB"`
- `sonic-gnmi/telemetry/telemetry.go:196-204` — CLI フラグデフォルト値
- `sonic-gnmi/telemetry/telemetry.go:303-313` — シンボリックリンクパス自動調整
- `sonic-gnmi/gnmi_server/gnsi_certz.go:381-428` — `doUpload()` バリデーション (version必須, created_on必須)
