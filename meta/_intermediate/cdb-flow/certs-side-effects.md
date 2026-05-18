# CREDENTIALS|CERT (STATE_DB) — Phase F 副次 DB 書込スキャンノート

対象ページ: `docs/reference/config-db/certs.md`
対象テーブル: `STATE_DB` — `CREDENTIALS|CERT|<profileID>`
Producer: `GNSICertzServer` (`sonic-gnmi/gnmi_server/gnsi_certz.go`)
スキャン範囲: `doUpload()` / `activateEntity()` / `finalizeProfile()` / `revertProfile()` / `atomicSetSrvCertKeyPair()` / `atomicSetCACert()` / `copyCRLBundle()` / `saveCertzMetadata()` の全行精読

---

## 副次 DB 書込の有無

| DB 名 | 書込有無 | 根拠 |
|-------|---------|------|
| STATE_DB | あり（主体） | `writeCredentialsMetadataToDB()` が CREDENTIALS|CERT|<profileID> に `HSet` |
| CONFIG_DB | なし | `gnsi_certz.go` に CONFIG_DB 接続・書き込み処理ゼロ |
| APPL_DB | なし | 接続・書き込み処理ゼロ |
| ASIC_DB | なし | 接続・書き込み処理ゼロ |
| FLEX_COUNTER_DB | なし | 接続・書き込み処理ゼロ |
| COUNTERS_DB | なし | 接続・書き込み処理ゼロ |
| LOGLEVEL_DB | なし | 接続・書き込み処理ゼロ |

## ファイルシステムへの副次書き込み

STATE_DB 以外の主な副次効果はすべてファイルシステムに対して発生する。

| リソース | 操作 | タイミング | evidence |
|---------|------|----------|----------|
| TLS サーバ証明書シンボリックリンク (`SrvCertLnk`) | 旧リンク削除 → 新ファイルへの symlink 作成 | `activateEntity(certType)` 実行時 | `gnsi_certz.go:938-961` |
| TLS サーバ秘密鍵シンボリックリンク (`SrvKeyLnk`) | 旧リンク削除 → 新ファイルへの symlink 作成 | `activateEntity(certType)` 実行時 | `gnsi_certz.go:943-960` |
| CA 証明書シンボリックリンク (`CaCertLnk`) | 旧リンク削除 → 新ファイルへの symlink 作成 | `activateEntity(tbType)` 実行時 | `gnsi_certz.go:977-984` |
| CRL バンドルディレクトリ (`CertCRLConfig/<profileID>/`) | PEM ファイル群を書き込み | `activateEntity(crlType)` → `rotateCRLBundle()` | `gnsi_certz.go:531-534` |
| CRL flush ディレクトリ (`CertCRLConfig/<profileID>_flush/`) | `FinalizeRotation` 時に active dir へコピー | `finalizeProfile()` → `copyCRLBundle()` | `gnsi_certz.go:671` |
| AuthPolicy バックアップファイル (`.bak`) | Rotate 中に `os.Rename` でバックアップ作成、Finalize 時に `os.Remove` で削除 | `saveEntities(apType)` / `finalizeProfile()` | `gnsi_certz.go:537-540,678` |
| プロファイル JSON メタデータ (`CertzMetaFile`) | Rotate Finalize 確定後に JSON 上書き保存 | `finalizeProfile()` → `saveCertzMetadata()` | `gnsi_certz.go:685,717-725` |

## gnmi サービスへの影響（TLS 再ロード）

`atomicSetSrvCertKeyPair()` および `atomicSetCACert()` はシンボリックリンクを更新するが、
gnmi サーバ (`server.go`) が TLS 証明書を再ロードするタイミングは独立している。
symlink 更新直後から次回 TLS ハンドシェイクで新証明書が有効になる（ファイルシステムレベルの即時反映）。
`STATE_DB` の `CREDENTIALS|CERT` フィールドは TLS 証明書の実体ではなく freshness メタデータのみを保持する。

evidence: `gnsi_certz.go:924-964`, `gnsi_certz.go:966-990`

---

## サマリ

- 副次 DB 書き込みは STATE_DB のみ（主書き込み）
- CONFIG_DB / APPL_DB / ASIC_DB / FLEX_COUNTER_DB への書き込みはゼロ
- 主な副次効果はファイルシステム：TLS シンボリックリンク・CRL ディレクトリ・JSON メタデータファイルへの書き込み
