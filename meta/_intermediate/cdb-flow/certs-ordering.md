# CREDENTIALS|CERT — Phase B 書込み順依存スキャンノート

対象テーブル: `CREDENTIALS|CERT` (STATE_DB)
Consumer: `gnsi_certz.go` (`sonic-gnmi/gnmi_server/gnsi_certz.go`)
スキャン範囲: `NewGNSICertzServer()`, `Rotate()`, `processRotateRequest()`, `doUpload()`, `activateEntity()`, `saveEntities()`, `finalizeProfile()`, `revertProfile()`, `writeEntityFreshness()`, `writeCredentialsMetadataToDB()`, `bootstrapDefaultProfile()`, `loadCertzMetadata()`, `saveCertzMetadata()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. NewGNSICertzServer() — STATE_DB 書き込みは telemetry バイナリ起動直後に実行される

- `NewGNSICertzServer()` (gnsi_certz.go:114) は `loadCertzMetadata()` でディスク上の JSON (`CertzMetaFile`, デフォルト `/keys/grpc-version.json`) からプロファイルをロードし、`defaultProfile` ("gnxi") が存在しない場合は `bootstrapDefaultProfile()` で新規生成する (gnsi_certz.go:126-131)。
- ロード直後にすべてのプロファイルに対して `writeEntityFreshness()` × 4 エンティティ（Cert / TrustBundle / CrlBundle / AuthPolicy）を呼び出し、STATE_DB の `CREDENTIALS|CERT|<profileID>` へ書き込む (gnsi_certz.go:134-139)。
- **順序依存**: `STATE_DB` が利用可能でない状態で telemetry が起動すると `writeCredentialsMetadataToDB()` の `NotificationProducer.Set()` が失敗する。`database.service` への After 依存はサービスファイル (`gnmi.service.j2`) に記述されており、通常は問題にならない。
- **依存なし**: CONFIG_DB への読み書きは行わない（この時点では STATE_DB のみ）。
- evidence: `gnsi_certz.go:114-159`, `gnmi.service.j2:3-4`

### 2. Rotate RPC — UploadRequest 処理順は entities[] の配列順に依存する

- `doUpload()` (gnsi_certz.go:381) は `req.GetEntities()` のスライスを **配列順** でイテレートし、各エンティティに対して `saveEntities()` → `activateEntity()` → `writeEntityFreshness()` を順次実行する (gnsi_certz.go:388-428)。
- 同一 Rotate ストリーム内で複数エンティティを送る場合（例: cert + trust_bundle の同時更新）、配列の先頭から順に STATE_DB へ書き込まれる。
- **順序依存**: cert の `atomicSetSrvCertKeyPair()` と trust_bundle の `atomicSetCACert()` は独立した操作であり、処理順序によって中間状態（cert 更新済み・CA 未更新の期間）が生じる。この期間中に gRPC クライアントが接続した場合は TLS ハンドシェイクが一時的に失敗する可能性がある。
- evidence: `gnsi_certz.go:381-429`

### 3. doUpload() — entities[] のバリデーション順序

- `doUpload()` は entities[] 配列のループ先頭で `created_on == 0` / `version == ""` のバリデーションを行う (gnsi_certz.go:389-394)。
- **順序依存**: 配列の 2 番目以降のエンティティにバリデーションエラーがある場合、1 番目のエンティティはすでに `saveEntities()` / `activateEntity()` が完了して STATE_DB に書き込まれている。バリデーション失敗後に `doUpload()` はエラーを返し、呼び出し元 `Rotate()` が `revertProfile()` を実行して ActiveEntities をロールバックするが、**STATE_DB の書き込みは revert されない**。
- **実害**: `revertProfile()` は `writeEntityFreshness()` を呼んで STATE_DB を previous state に更新するため、最終的には正しい値に戻る (gnsi_certz.go:611, 620, 633, 641)。ただし revert 処理が走るまでの短期間、STATE_DB の `version` / `created_on` フィールドが中途半端な値になる。
- evidence: `gnsi_certz.go:381-428`, `gnsi_certz.go:595-644`

### 4. FinalizeRotation — Cert / TrustBundle / CrlBundle / AuthPolicy の確定順序

- `finalizeProfile()` (gnsi_certz.go:646) は常に固定順序 (Cert → TrustBundle → CrlBundle → AuthPolicy) でエンティティを確定する。
- Cert/TrustBundle: `removeEntityFiles(profile.LastEntities.*)` で旧ファイルを削除し `Final = true` を設定 (gnsi_certz.go:652-662)。
- CrlBundle: ディレクトリを `copyCRLBundle()` で flush パスにコピー後 `Final = true` (gnsi_certz.go:664-673)。
- AuthPolicy: バックアップ (`.bak`) ファイルを `os.Remove()` で削除後 `Final = true` (gnsi_certz.go:676-682)。
- 最後に `saveCertzMetadata()` でプロファイルを JSON ファイルに永続化 (gnsi_certz.go:685)。
- **順序依存**: `saveCertzMetadata()` が失敗した場合 (disk full 等)、メモリ上のプロファイルは `Final = true` に更新されているが、次回起動時の `loadCertzMetadata()` はディスクの旧 JSON を読み込むため、再起動後に `writeEntityFreshness()` が旧 version/created_on を STATE_DB に書き込む。
- evidence: `gnsi_certz.go:646-686`

### 5. 排他ロック (certzMu) — 並行 Rotate は先着優先

- `certzMu.TryLock()` (gnsi_certz.go:233) により、2 つ以上の同時 Rotate RPC は Aborted エラーで弾かれる。先行の Rotate が完了（Finalize またはエラー/EOF）するまで後続は開始できない。
- **順序依存**: 先行 Rotate が entities の途中でキャンセルされた場合、`defer certzMu.Unlock()` (gnsi_certz.go:236) によってロックは解放される。後続 Rotate はその時点で取得可能になる。先行 Rotate の revert 完了前に後続が開始した場合でも、`revertProfile()` は `muPath` ロックを保持しないため後続の `doUpload()` 内の `muPath.Lock()` (gnsi_certz.go:382) との干渉は発生しない。
- evidence: `gnsi_certz.go:233-236`

### 6. STATE_DB 書き込みタイミング — 物理証明書ファイルとの非同期性

- `activateEntity()` (gnsi_certz.go:464) は物理ファイル操作 (`atomicSetSrvCertKeyPair()` / `atomicSetCACert()`) と STATE_DB 書き込み (`writeEntityFreshness()`) を順次実行する。ファイル操作後に STATE_DB が書かれる順序。
- **順序依存**: 物理ファイルの更新後・STATE_DB 書き込み前のウィンドウで gNMI サーバが再起動した場合、`NewGNSICertzServer()` が `loadCertzMetadata()` から旧 version を読み込み、旧 version を STATE_DB に書き込む。物理ファイルと STATE_DB の freshness 情報が一時的に不一致になる。
- evidence: `gnsi_certz.go:464-503`, `gnsi_certz.go:114-139`

### 7. CRL 設定の前提条件 — `CertCRLConfig` フラグが先行必須

- `doUpload()` 内で CRL エンティティが要求された場合、`srv.Server.config.CertCRLConfig == ""` であれば即時 `codes.Aborted: "CRL not configured"` を返す (gnsi_certz.go:405-407)。
- **順序依存 (起動時)**: telemetry バイナリの起動引数 `--cert_crl_dir` が設定されていない場合、CRL バンドルの Rotate が永遠に失敗する。CONFIG_DB や STATE_DB を書き換えることで動的変更はできない（再起動が必要）。
- **デフォルト**: `--cert_crl_dir` のデフォルト値は `/mtls/crl` (telemetry.go:202)。ディレクトリが存在しない場合は `NewGNSICertzServer()` が `os.MkdirAll()` で自動作成する (gnsi_certz.go:143-149)。
- evidence: `gnsi_certz.go:404-408`, `gnsi_certz.go:143-149`, `telemetry/telemetry.go:202`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | database.service → gnmi.service 起動 | 強制先行（systemd After 依存） | STATE_DB 未起動時は書き込みエラー（再起動で回復） |
| 2 | entities[] 配列順 → STATE_DB 書き込み順 (cert → trust_bundle 等) | 配列先頭から順次 | 中間状態は短期。revert/finalize で最終状態は一貫 |
| 3 | 配列後半エンティティバリデーション失敗 → 前半はすでに STATE_DB 書き込み済み | revert で回復 | revertProfile() が writeEntityFreshness() で STATE_DB 上書き |
| 4 | finalizeProfile() 内で Cert → TrustBundle → CrlBundle → AuthPolicy の固定順確定 | 固定順序 | saveCertzMetadata() 失敗時は再起動で旧 version を書き込む |
| 5 | certzMu により並行 Rotate は直列化 | 先着排他 | TryLock 失敗は即時 Aborted; defer Unlock で必ず解放 |
| 6 | 物理ファイル更新 → STATE_DB 書き込み（activateEntity の順序） | 順次（ファイル先・DB 後） | 再起動直後は loadCertzMetadata 由来の値が STATE_DB に反映 |
| 7 | --cert_crl_dir フラグ設定 → CRL Rotate 可能 | 起動時前提条件 | 未設定時は全 CRL Rotate が Aborted; CONFIG_DB での動的変更不可 |
