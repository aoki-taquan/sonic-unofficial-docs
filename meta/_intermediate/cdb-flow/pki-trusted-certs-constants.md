# PKI / SECURITY_PROFILES — Phase E: ハードコード定数調査

調査日: 2026-05-19
対象スコープ: CONFIG_DB `SECURITY_PROFILES` 管理コンポーネント (gNSI Certz `sonic-gnmi/gnmi_server/gnsi_certz.go`)

---

## 定数一覧 (gnsi_certz.go const ブロック)

### プロファイル・テーブル名 (グローバル定数)

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `defaultProfile` | `"gnxi"` | gNSI Certz デフォルトプロファイル ID | `gnsi_certz.go:30` |
| `certTbl` | `"CERT"` | STATE_DB CREDENTIALS テーブル内の entity ID プレフィクス | `gnsi_certz.go:32` |
| `credentialsTbl` | `"CREDENTIALS"` | STATE_DB テーブル名 | `gnsi_certz.go:48` |

### Entity フィールド識別子

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `certId` | `"certificate"` | SERVER CERTIFICATE エンティティ ID | `gnsi_certz.go:33` |
| `tbId` | `"ca_trust_bundle"` | CA TRUST BUNDLE エンティティ ID | `gnsi_certz.go:34` |
| `crlId` | `"certificate_revocation_list_bundle"` | CRL BUNDLE エンティティ ID | `gnsi_certz.go:35` |
| `authId` | `"authentication_policy"` | AUTHENTICATION POLICY エンティティ ID | `gnsi_certz.go:36` |

### メタデータフィールド サフィックス

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `versionFld` | `"_version"` | フィールド名サフィックス (e.g., `certificate_version`) | `gnsi_certz.go:39` |
| `createdFld` | `"_created_on"` | フィールド名サフィックス (e.g., `certificate_created_on`) | `gnsi_certz.go:40` |

### CRL 管理ディレクトリ

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `crlDefault` | `"crl"` | デフォルト CRL ディレクトリ名 (v0→v1 互換性) | `gnsi_certz.go:43` |
| `crlFlush` | `"_flush"` | CRL flush サブディレクトリサフィックス | `gnsi_certz.go:44` |
| `crlTmpDir` | `"tmp"` | CRL 一時ディレクトリ名 | `gnsi_certz.go:45` |

### ファイル操作

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `backupExt` | `".bak"` | ロールバック用バックアップファイル拡張子 | `gnsi_certz.go:47` |

---

## Version 定数 (bootstrap 初期値)

`bootstrapDefaultProfile()` 関数内で硬止めされる version:

| エンティティ | Version 値 | ソース行 |
|-------------|-----------|---------|
| SERVER CERTIFICATE | `"V1"` | `gnsi_certz.go:188` |
| CA TRUST BUNDLE | `"V1"` | `gnsi_certz.go:196` |
| CRL BUNDLE | `"V1"` | `gnsi_certz.go:203` |
| AUTHENTICATION POLICY | `"V1"` | `gnsi_certz.go:210` |

bootstrap 起動時に生成される全エンティティはバージョン `"V1"` で初期化される。Rotate RPC による更新時にはクライアント指定値 (必須、空文字列拒否) で上書きされる。

---

## Entity 処理順序 (const iota)

STATE_DB 書込みおよび Rotate 処理の順序は以下の enum で固定化:

```go
const (
    certType CertzType = iota      // 0: SERVER CERTIFICATE
    tbType                         // 1: CA TRUST BUNDLE
    crlType                        // 2: CRL BUNDLE
    apType                         // 3: AUTHENTICATION POLICY
)
```

ソース: `gnsi_certz.go:91-96`

この enum 順序は `bootstrapDefaultProfile()` の for-loop (`gnsi_certz.go:134-138`) で使用され、STATE_DB への書込み順序が固定される。

---

## 特記事項

1. **`defaultProfile = "gnxi"` はプロファイル ID**: CONFIG_DB の `SECURITY_PROFILES|<profile-name>` キーとは独立。gNSI Certz 内部管理で固定使用される。

2. **Version "V1" は bootstrap オンリー**: 起動時のデフォルトバージョン。実際の Rotate RPC での version 更新はクライアント指定値を採用。空文字列は `codes.InvalidArgument` で拒否される (`gnsi_certz.go:393`)。

3. **Entity ID の STATE_DB フィールド名マッピング**:
   - `certId` + `versionFld` = `"certificate_version"` (STATE_DB フィールド)
   - `tbId` + `versionFld` = `"ca_trust_bundle_version"`
   - `crlId` + `versionFld` = `"certificate_revocation_list_bundle_version"`
   - `authId` + `versionFld` = `"authentication_policy_version"`

4. **CSR プレフィックス**: 関数スコープで `csrPrefix = []byte("CSR1_")` が定義されるが、これは定数ではなく var。community master では CSR 検証コードが実装されていない可能性あり。

5. **Integrity Manifest File パス**: デフォルト `"/mbm/boot_manifest.cbor"` (`gnsi_certz.go:54`) はハードコード。`NewGNSICertzServer()` で srv.config から上書き可能。

---

## 出典

- `sonic-gnmi/gnmi_server/gnsi_certz.go:29-49` — const ブロック定義
- `sonic-gnmi/gnmi_server/gnsi_certz.go:91-96` — Entity type enum (iota)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:178-222` — bootstrapDefaultProfile (Version "V1" 初期化)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:385-416` — doUpload validation (version 必須チェック)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:134-138` — Entity 書込み順序固定ループ
