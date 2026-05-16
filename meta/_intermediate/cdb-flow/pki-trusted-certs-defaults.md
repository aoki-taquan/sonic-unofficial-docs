# PKI / SECURITY_PROFILES フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: CONFIG_DB `SECURITY_PROFILES` (sonic-pki.yang)

## 調査対象ファイル

- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` — YANG スキーマ定義
- `sonic-mgmt-common/cvl/testdata/schema/sonic-security-global.yang` — `SECURITY_GLOBAL` との leafref 関係
- `sonic-mgmt-common/cvl/cvl_test.go` — テストコードによる使用例
- `sonic-gnmi/gnmi_server/gnsi_certz.go` — gNSI Certz 実装（STATE_DB `CREDENTIALS|CERT|<profileID>` 書き込み）

---

## 調査結果サマリ

`PKI_TRUSTED_CERTS` というテーブル名は SONiC community master (2026-05-14 時点) の
いかなるソースファイル（Python / Go / YANG / JSON）にも存在しない。

PKI 関連の CONFIG_DB テーブルとして確認できたのは:

1. **`SECURITY_PROFILES`** — `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang` に定義される
   CVL テストデータスキーマ。`sonic-buildimage/src/sonic-yang-models/` には含まれていない
   (community master YANG には未マージ)。
2. **`GNMI_CLIENT_CERT`** — `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang` に
   定義済み。クライアント証明書 CN → ロールマッピング。PKI 信頼設定の一形態ではあるが、
   `pki-trusted-certs` とは別概念。
3. **STATE_DB `CREDENTIALS|CERT|<profileID>`** — `sonic-gnmi/gnmi_server/gnsi_certz.go` が書き込む
   gNSI Certz の証明書フレッシュネスメタデータ。CONFIG_DB ではなく STATE_DB。

---

## SECURITY_PROFILES フィールド別 暗黙デフォルト

### `profile-name` (KEY)

**YANG デフォルト**: なし (key フィールドのため必須)

```yang
# sonic-pki.yang:31-35
list SECURITY_PROFILES_LIST {
    key "profile-name";
    leaf "profile-name" {
        type string;
    }
}
```

→ キーフィールドのため値省略不可。デフォルト値なし。

---

### `certificate-name`

**YANG デフォルト**: なし (optional leaf、DB に存在しない場合は空扱い)

```yang
# sonic-pki.yang:36-41
leaf "certificate-name" {
    type string;
    description "Certificate file name";
}
```

`SECURITY_GLOBAL|global.security_profile` が `SECURITY_PROFILES_LIST` への leafref を持ち、
削除は leafref 違反でブロックされる (cvl_test.go:2509-2533 — `instance-in-use` エラー)。

**コード由来デフォルト**: キーが存在しない場合は空文字列相当。参照元ハンドラが未実装の
ため実際の runtime fallback は不明。

---

## gNSI Certz (sonic-gnmi) の STATE_DB 書き込みフィールド

`gnsi_certz.go` は CONFIG_DB を読み書きしない。証明書メタデータのみを
STATE_DB `CREDENTIALS|CERT|<profileID>` に書き込む。

| フィールド | 値例 | ソース |
|-----------|------|--------|
| `certificate_version` | `"V1"` (bootstrap 初期値) | `gnsi_certz.go:186-190` — bootstrapDefaultProfile |
| `certificate_created_on` | 起動時 `time.Now().UnixNano()` (ns) | `gnsi_certz.go:181,692-693` |
| `ca_trust_bundle_version` | `"V1"` (bootstrap 初期値) | `gnsi_certz.go:193-198` |
| `ca_trust_bundle_created_on` | 起動時 `time.Now().UnixNano()` (ns) | 同上 |
| `certificate_revocation_list_bundle_version` | `"V1"` (bootstrap 初期値) | `gnsi_certz.go:199-204` |
| `authentication_policy_version` | `"V1"` (bootstrap 初期値) | `gnsi_certz.go:205-212` |

**デフォルト profile**: `"gnxi"` (`gnsi_certz.go:30` — `defaultProfile` 定数)

---

## 要約

| テーブル | 所在 | コミュニティ master | デフォルト源 |
|---------|------|-------------------|------------|
| `SECURITY_PROFILES` | sonic-mgmt-common CVL testdata | **未マージ** (testdata のみ) | YANG 定義なし |
| `SECURITY_GLOBAL` | 同上 | **未マージ** | YANG leafref 参照 |
| `GNMI_CLIENT_CERT` | sonic-buildimage YANG | マージ済み | デフォルトなし (key = CN) |
| STATE_DB `CREDENTIALS|CERT` | sonic-gnmi gnsi_certz.go | マージ済み | Version=`"V1"`, Created=起動時刻 |

---

## 証拠リンク

- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang:28-44` — SECURITY_PROFILES YANG 定義
- `sonic-mgmt-common/cvl/testdata/schema/sonic-security-global.yang:26-38` — SECURITY_GLOBAL leafref
- `sonic-mgmt-common/cvl/cvl_test.go:2505-2535` — leafref 削除テスト
- `sonic-gnmi/gnmi_server/gnsi_certz.go:29-36` — 定数定義 (defaultProfile, certTbl, credentialsTbl)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:178-222` — bootstrapDefaultProfile (Version="V1", 初期時刻)
- `sonic-gnmi/gnmi_server/gnsi_certz.go:688-715` — writeEntityFreshness (STATE_DB 書き込み)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang:100-121` — GNMI_CLIENT_CERT YANG
