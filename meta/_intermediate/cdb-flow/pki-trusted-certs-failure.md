# pki-trusted-certs failure (Phase D) 調査メモ

調査日: 2026-05-19  
対象: `SECURITY_PROFILES` / `SECURITY_GLOBAL` / gNSI Certz

## CVL バリデーション失敗

### SECURITY_GLOBAL|global.security_profile 設定失敗

- 条件: 参照先 `SECURITY_PROFILES|<profile>` が存在しない状態で SET
- エラー種別: CVL `invalid-value` (leafref バリデーション失敗)
- 挙動: CONFIG_DB への書込みが拒否される。既存の `security_profile` 値は変更されない
- 証拠: `sonic-security-global.yang:29-35` (leafref 定義), `cvl_test.go:2506-2537`

### SECURITY_PROFILES|<profile> 削除失敗

- 条件: `SECURITY_GLOBAL|global.security_profile` が当該プロファイルを参照中に DEL
- エラー種別: CVL `instance-in-use`
- 挙動: 削除が拒否される。参照元の `security_profile` を先に削除する必要がある
- 証拠: `cvl_test.go:2506-2537` — `TestDeleteEntryNotPermittedByLeafRef` 系テスト

## gNSI Certz 起動時失敗

### loadCertzMetadata 失敗

- 条件: `CertzMetaFile` (デフォルト `/keys/grpc-version.json`) が読み込めない / 不正 JSON
- 挙動: `log.V(0).Info(err)` でログ出力のみ。処理は継続し `bootstrapDefaultProfile()` が呼ばれる
- 証拠: `gnsi_certz.go:126-127`

### CRL ディレクトリ作成失敗

- 条件: `CertCRLConfig` 配下の default / flush ディレクトリの `os.MkdirAll` が失敗
- 挙動: `log.V(1).Infof("Failed Creating CRL Flush dir: ...")` のみ。プロセスは継続するが CRL 操作が後続で失敗する
- 証拠: `gnsi_certz.go:145-155`

## Rotate RPC 失敗パス

### 入力バリデーション失敗 (codes.InvalidArgument)

| 条件 | エラーメッセージ | 証拠 |
|------|----------------|------|
| `ssl_profile_id` が未登録プロファイル | `"Rotate requested with invalid ssl_profile_id: %s"` | `gnsi_certz.go:287-289` |
| `entity` が空 | `"entity cannot be empty"` | `gnsi_certz.go:386` |
| `created_on` が空 | `"created_on cannot be empty"` | `gnsi_certz.go:390` |
| `version` が空文字列 | `"version cannot be empty"` | `gnsi_certz.go:393` |
| CRL 未設定状態で CRL entity を Upload | `codes.Aborted: "CRL not configured"` | `gnsi_certz.go:406` |
| 不明な entity type | `"failed to find entity type: ..."` | `gnsi_certz.go:414` |

### 並行 Rotate 拒否

- 条件: 既に Rotate ストリームが処理中に新規 Rotate RPC が来た場合
- エラー: `codes.Aborted: "concurrent certz.Rotate RPCs are not allowed"`
- 証拠: `gnsi_certz.go:232-234` (`certzMu.TryLock()` 失敗)

### 証明書ファイル操作失敗 (codes.Aborted)

- `saveEntities` 失敗: ファイル書き込みエラーなど。`codes.Aborted: "Entity save err: ..."` を返す。ストリームが終了し Rotate 全体が中断される
- `activateEntity` 失敗: シンボリックリンク操作 (`atomicSetSrvCertKeyPair` / `atomicSetCACert`) 失敗。
  - `atomicSetSrvCertKeyPair`: 新しいシンボリックリンク作成に失敗した場合、`restoreSymlink` で旧シンボリックリンク (`SrvCertLnk`, `SrvKeyLnk`) を復元してロールバック (`gnsi_certz.go:951-952`, `958-959`)。ただし restore 自体が失敗した場合 (`_ =` で無視) はシンボリックリンクなし状態になりうる
  - `atomicSetCACert`: 新しいシンボリックリンク作成に失敗した場合、`restoreSymlink(oldCert, CaCertLnk)` でロールバック (`gnsi_certz.go:984`)
- 証拠: `gnsi_certz.go:422-426, 925-989`

### Finalize なし終了

- 条件: クライアントが Upload を送らずに Rotate ストリームを切断 (EOF)
- 挙動: `codes.Aborted: "No Finalize message"` を返す。`ActiveEntities` に中間状態のエンティティが残る可能性がある。次回 Rotate では既存のエンティティが上書きされる
- 証拠: `gnsi_certz.go:244-248`

## STATE_DB 書込み失敗

- 条件: Redis (`STATE_DB`) に接続できない場合
- 挙動: `writeCredentialsMetadataToDB` が `fmt.Errorf("REDIS is not available: ...")` を返す。`writeEntityFreshness` はこのエラーを `log.V(0).Infof` でログするが処理を継続する (証明書自体は有効)
- 証拠: `gnsi_certz.go:1038-1042`, `gnsi_certz.go:688-730`

## AddProfile / DeleteProfile / GetProfileList 未実装

- `AddProfile`, `DeleteProfile`, `GetProfileList` はすべて `codes.Unimplemented` を返す
- `DeleteProfile` は `"gnxi"` デフォルトプロファイルの削除を含む全プロファイル削除 RPC が無効
- 証拠: `gnsi_certz.go:162-170`

## ハンドラ未実装による非影響

`SECURITY_PROFILES` を CONFIG_DB から読み込む production ハンドラが community master に存在しないため、DB 書込みエラー (CVL 以外) が runtime 動作に影響を与える経路は現時点で確認されない。
