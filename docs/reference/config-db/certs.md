---
title: CREDENTIALS|CERT テーブル (STATE_DB)
description: "CREDENTIALS|CERT テーブル — gNSI Certz が証明書バンドルのフレッシュネス情報を書き込む STATE_DB テーブル。certificate / ca_trust_bundle / certificate_revocation_list_bundle / authentication_policy の version と created_on フィールドを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-gnmi
    path: gnmi_server/gnsi_certz.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-gnmi
    path: common_utils/notification_producer.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-gnmi
    path: telemetry/telemetry.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
related:
  config_db:
    - GNMI
    - TELEMETRY
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# CREDENTIALS|CERT テーブル (STATE_DB)

!!! note "STATE_DB テーブル"
    `CREDENTIALS|CERT` は **CONFIG_DB ではなく STATE_DB** に書き込まれる読み取り専用テーブルである。gNSI Certz サーバ (`gnsi_certz.go`) が証明書バンドルの更新時に自動書き込みする。オペレータは直接 CONFIG_DB を介して操作しない。

## 概要

`CREDENTIALS|CERT|<profileID>` は gNSI Certz (`sonic-gnmi/gnmi_server/gnsi_certz.go`) が各 SSL プロファイルの証明書バンドルフレッシュネス情報を [STATE_DB](../../reference/glossary.md#term-state_db) に記録するテーブルである[^1]。

gNSI Certz は gRPC 経由の `certz.Rotate` RPC で証明書を更新し、確定 (FinalizeRotation) 後に以下 4 種類のエンティティの `version` / `created_on` フィールドを書き込む:

| エンティティ | フィールド prefix |
|------------|----------------|
| サーバ証明書チェーン (X.509) | `certificate` |
| CA トラストバンドル | `ca_trust_bundle` |
| 証明書失効リストバンドル (CRL) | `certificate_revocation_list_bundle` |
| 認証ポリシー | `authentication_policy` |

デフォルトプロファイル名は `"gnxi"` で、起動時に `bootstrapDefaultProfile()` が自動生成する[^1]。

<!-- cdb-mermaid -->
### データフロー

```mermaid
flowchart LR
  GNSI["gNSI Certz<br/>(gnsi_certz.go)"]
  SDB[("STATE_DB<br/>CREDENTIALS|CERT|&lt;profileID&gt;")]
  CRL["ファイルシステム<br/>CRL ディレクトリ"]
  GNSI -->|writeEntityFreshness| SDB
  GNSI -->|ファイル書き込み| CRL
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
CREDENTIALS|CERT|<profileID>
```

- `<profileID>` — SSL プロファイル識別子。デフォルトは `"gnxi"`

## フィールド

### `CREDENTIALS|CERT|<profileID>`

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `certificate_version` | string | `"V1"` (bootstrap) | サーバ証明書のバージョン文字列 |
| `certificate_created_on` | string (数値) | bootstrap 時の UnixNano 文字列 | サーバ証明書の作成タイムスタンプ (疑似ナノ秒) |
| `ca_trust_bundle_version` | string | `"V1"` (bootstrap) | CA トラストバンドルのバージョン |
| `ca_trust_bundle_created_on` | string (数値) | bootstrap 時の UnixNano 文字列 | CA トラストバンドルの作成タイムスタンプ |
| `certificate_revocation_list_bundle_version` | string | `"V1"` (bootstrap) | CRL バンドルのバージョン |
| `certificate_revocation_list_bundle_created_on` | string (数値) | bootstrap 時の UnixNano 文字列 | CRL バンドルの作成タイムスタンプ |
| `authentication_policy_version` | string | `"V1"` (bootstrap) | 認証ポリシーのバージョン |
| `authentication_policy_created_on` | string (数値) | bootstrap 時の UnixNano 文字列 | 認証ポリシーの作成タイムスタンプ |

## 制約

- `version` フィールドは Rotate RPC 時に空文字列不可 (`codes.InvalidArgument: "version cannot be empty"`)
- `created_on` フィールドは Rotate RPC 時に 0 不可 (`codes.InvalidArgument: "created_on cannot be empty"`)
- CA トラストバンドルの証明書は X.509 / PEM エンコードのみ受け付ける
- CRL バンドルは空不可

## 購読者

- `gnsi_certz.go` (`sonic-gnmi`): 証明書バンドル更新時に STATE_DB へ書き込む

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`GNMI`](gnmi.md) (`GNMI|certs` で証明書パスを設定), [`TELEMETRY`](telemetry.md)
- 関連 CLI: なし (gNSI Certz は gRPC `certz.Rotate` RPC 経由で設定)
- 関連 YANG: なし (community master には対応 YANG 未定義)

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **STATE_DB 書き込みのみ**: 本テーブルは gNSI Certz が STATE_DB に書き込む。CONFIG_DB には書き込まない。`sonic-cfggen` / `config reload` の対象外
- **同時 Rotate 禁止**: `certzMu.TryLock()` による排他制御。並行 `certz.Rotate` RPC は `codes.Aborted: "concurrent certz.Rotate RPCs are not allowed"` で拒否される
- **`created_on` 疑似ナノ秒**: 格納値は `strconv.FormatUint(entity.CreatedOn, 10) + "000000000"` で生成される 19 桁以上の文字列。bootstrap では `time.Now().UnixNano()` (ナノ秒) をそのまま + `"000000000"` サフィックスを付加するため、実際の精度は秒未満まで記録される
- **CRL ディレクトリ管理**: `certificate_revocation_list_bundle` は DB フィールドのみでなく、`CertCRLConfig` ディレクトリ (デフォルト `/mtls/crl`) にもファイルとして保存される
- **bootstrap の `Final: true`**: `bootstrapDefaultProfile()` が生成する全エンティティは `Final: true` で初期化されるため、Rotate が失敗しても bootstrap 値へのロールバックは発生しない
<!-- /cdb-exceptions -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

> gNSI Certz `gnsi_certz.go` および `telemetry/telemetry.go` のコードから導出した フィールドデフォルト値を整理する。

### `<profileID>` (CREDENTIALS|CERT key)

| 種別 | 値 | ソース |
|------|----|--------|
| コード由来デフォルト | `"gnxi"` | `gnsi_certz.go:30` — `defaultProfile` 定数 |

起動時に `bootstrapDefaultProfile()` が `profiles["gnxi"]` を生成する。プロファイルが既に JSON ファイル (`CertzMetaFile`) に存在する場合は上書きしない[^1]。

---

### `certificate_version`

| 種別 | 値 | ソース |
|------|----|--------|
| bootstrap 初期値 | `"V1"` | `gnsi_certz.go:188` — `bootstrapDefaultProfile()` |
| Rotate 後 | クライアント指定値 (必須、空文字不可) | `gnsi_certz.go:392-394` |

---

### `ca_trust_bundle_version`

| 種別 | 値 | ソース |
|------|----|--------|
| bootstrap 初期値 | `"V1"` | `gnsi_certz.go:195` — `bootstrapDefaultProfile()` |
| Rotate 後 | クライアント指定値 (必須、空文字不可) | `gnsi_certz.go:392-394` |

---

### `certificate_revocation_list_bundle_version`

| 種別 | 値 | ソース |
|------|----|--------|
| bootstrap 初期値 | `"V1"` | `gnsi_certz.go:202` — `bootstrapDefaultProfile()` |
| Rotate 後 | クライアント指定値 (必須、空文字不可) | `gnsi_certz.go:392-394` |

CRL バンドルが有効化されていない場合 (`CertCRLConfig == ""`): Rotate RPC は `codes.Aborted: "CRL not configured"` を返す[^1]。

---

### `authentication_policy_version`

| 種別 | 値 | ソース |
|------|----|--------|
| bootstrap 初期値 | `"V1"` | `gnsi_certz.go:209` — `bootstrapDefaultProfile()` |
| Rotate 後 | クライアント指定値 (必須、空文字不可) | `gnsi_certz.go:392-394` |

---

### `*_created_on` フィールド群

| 種別 | 値 | ソース |
|------|----|--------|
| bootstrap 初期値 | `time.Now().UnixNano()` の文字列 + `"000000000"` | `gnsi_certz.go:180,693-695` |
| Rotate 後 | `entityMsg.GetCreatedOn()` (秒) の文字列 + `"000000000"` | `gnsi_certz.go:693-695` |

格納形式: `strconv.FormatUint(entity.CreatedOn, 10) + "000000000"` (常に 19 桁以上の数値文字列)[^1]

---

### gNSI Certz 証明書ファイルパスデフォルト (CLI フラグ)

以下は `telemetry` バイナリのフラグデフォルト値であり、CONFIG_DB のフィールドではない。

| CLIフラグ | デフォルト値 | 対応フィールド |
|---------|-----------|--------------|
| `--ca_cert_lnk` | `/keys/ca_cert.lnk` | `Config.CaCertLnk` |
| `--server_cert_lnk` | `/keys/server_cert.lnk` | `Config.SrvCertLnk` |
| `--server_key_lnk` | `/keys/server_key.lnk` | `Config.SrvKeyLnk` |
| `--ca_crt` | `""` (省略可) | `Config.CaCertFile` |
| `--server_crt` | `""` (起動時に必須) | `Config.SrvCertFile` |
| `--server_key` | `""` (起動時に必須) | `Config.SrvKeyFile` |
| `--cert_crl_dir` | `/mtls/crl` | `Config.CertCRLConfig` |
| `--grpc_meta` | `/keys/grpc-version.json` | `Config.CertzMetaFile` |
| `--integrity_manifest_file` | `""` (省略可) | `Config.IntManFile` |

ソース: `telemetry/telemetry.go:196-204`[^2]

**パス自動調整**: `CaCertFile` が非空かつ `CaCertLnk` がデフォルト (`/keys/ca_cert.lnk`) の場合、`CaCertLnk` は `dir(CaCertFile)/ca_cert.lnk` に自動変更される。`SrvCertLnk` / `SrvKeyLnk` も同様[^2]。

<!-- evidence:
  sonic-gnmi/gnmi_server/gnsi_certz.go:29-49 — 定数 (certTbl="CERT", credentialsTbl="CREDENTIALS", フィールド名 prefix/suffix, defaultProfile="gnxi")
  sonic-gnmi/gnmi_server/gnsi_certz.go:178-222 — bootstrapDefaultProfile() (Version="V1", CreatedOn=time.Now().UnixNano())
  sonic-gnmi/gnmi_server/gnsi_certz.go:688-715 — writeEntityFreshness() (フィールド名生成, STATE_DB書き込み)
  sonic-gnmi/gnmi_server/gnsi_certz.go:1036-1058 — writeCredentialsMetadataToDB() (STATE_DB, path="CREDENTIALS|CERT|profileID")
  sonic-gnmi/common_utils/notification_producer.go:16 — dbName="STATE_DB"
  sonic-gnmi/common_utils/notification_producer.go:95-97 — GetKey() = strings.Join(k, "|")
  sonic-gnmi/telemetry/telemetry.go:196-204 — CLI フラグデフォルト値
  sonic-gnmi/telemetry/telemetry.go:303-313 — シンボリックリンクパス自動調整ロジック
  sonic-gnmi/gnmi_server/gnsi_certz.go:381-428 — doUpload() バリデーション
-->
<!-- /defaults -->

[^1]: `sonic-gnmi` `gnmi_server/gnsi_certz.go` — gNSI Certz 実装。defaultProfile, bootstrapDefaultProfile, writeEntityFreshness, writeCredentialsMetadataToDB
[^2]: `sonic-gnmi` `telemetry/telemetry.go` — CLI フラグデフォルトと CertzMetaFile パス設定ロジック
