# CREDENTIALS|CERT — Phase E ハードコード定数スキャンノート

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go`
- `sonic-gnmi/common_utils/notification_producer.go`
- `sonic-gnmi/telemetry/telemetry.go`

## 検出した定数

### const ブロック (gnsi_certz.go:29-49)

```go
const (
    defaultProfile string = "gnxi"
    certTbl  string = "CERT"
    certId   string = "certificate"
    tbId     string = "ca_trust_bundle"
    crlId    string = "certificate_revocation_list_bundle"
    authId   string = "authentication_policy"
    versionFld string = "_version"
    createdFld string = "_created_on"
    crlDefault string = "crl"
    crlFlush   string = "_flush"
    crlTmpDir  string = "tmp"
    backupExt      string = ".bak"
    credentialsTbl string = "CREDENTIALS"
)
```

### var ブロック (gnsi_certz.go:51-57)

```go
var (
    certzMu               sync.Mutex
    csrPrefix             []byte = []byte("CSR1_")
    integrityManifestFile string = "/mbm/boot_manifest.cbor"
    dbWriteMutex sync.Mutex
)
```

### common_utils/notification_producer.go:15-16

```go
const (
    dbName = "STATE_DB"
)
```

## 結論

- STATE_DB テーブル名・フィールド prefix/suffix は全て定数で固定
- `defaultProfile="gnxi"` はコード定数; 起動時 JSON に存在しなければ自動生成
- CRL ディレクトリ構造 (`crl/`, `crl_flush/`, `tmp/`) もコード定数
- ConfigDB / YANG に相当する管理インターフェイスなし
