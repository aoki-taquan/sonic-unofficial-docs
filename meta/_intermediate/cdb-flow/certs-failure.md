# CREDENTIALS|CERT — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-18 (chore/q67-f-batch99-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-gnmi/gnmi_server/gnsi_certz.go`

### Rotate RPC における失敗経路

| 失敗条件 | 検出箇所 | gRPC エラーコード | 結果 | evidence |
|---------|---------|-----------------|------|----------|
| 並行 `certz.Rotate` RPC を試行 | `certzMu.TryLock()` (L233) | `codes.Aborted` | "concurrent certz.Rotate RPCs are not allowed" を返し即時拒否。STATE_DB 変更なし | `gnsi_certz.go:233-234` |
| Finalize メッセージなしで接続が切断 (io.EOF) | `stream.Recv()` (L243-248) | `codes.Aborted` | `revertProfile()` で前回 Finalize 済みの値を STATE_DB に書き戻す | `gnsi_certz.go:244-248` |
| ストリーム受信エラー | `stream.Recv()` (L250-254) | `codes.Aborted` | `revertProfile()` 実行。エラーメッセージに詳細 err を付加 | `gnsi_certz.go:250-255` |
| 不正な `ssl_profile_id` で Rotate 要求 | `processRotateRequest()` (L287-288) | `codes.InvalidArgument` | "Rotate requested with invalid ssl_profile_id: <id>" 。revert なし（profile が存在しないため） | `gnsi_certz.go:287-288` |
| UploadRequest の処理失敗 (バリデーション / ファイル保存失敗) | `processRotateRequest()` (L273-276) | `codes.Aborted` | `revertProfile()` を実行後、"Process err: <err>" を返す | `gnsi_certz.go:273-281` |
| ストリーム送信エラー (UploadResponse 送信失敗) | `stream.Send()` (L279-281) | `codes.Aborted` | `revertProfile()` 実行 | `gnsi_certz.go:279-281` |
| Finalize 時の `finalizeProfile()` 失敗 (`saveCertzMetadata` 失敗等) | `finalizeProfile()` (L260-261) | `codes.Unknown` | "Failed to remove the old credentials: <err>" 。証明書ファイル・DB の整合性が崩れる可能性あり（再起動で回復） | `gnsi_certz.go:260-261` |
| 不正な `ssl_profile_id` で Finalize 要求 | `finalizeProfile()` (L649-651) | `codes.InvalidArgument` | "Finalize requested with invalid ssl_profile_id: <id>" | `gnsi_certz.go:649-651` |

### UploadRequest バリデーション失敗

| 失敗条件 | 検出箇所 | gRPC エラーコード | evidence |
|---------|---------|-----------------|----------|
| `entities[]` が空 | `doUpload()` L386 | `codes.InvalidArgument: "entity cannot be empty"` | `gnsi_certz.go:385-387` |
| `created_on == 0` | `doUpload()` L390 | `codes.InvalidArgument: "created_on cannot be empty"` | `gnsi_certz.go:389-391` |
| `version == ""` | `doUpload()` L393 | `codes.InvalidArgument: "version cannot be empty"` | `gnsi_certz.go:392-394` |
| CRL エンティティを含むが `--cert_crl_dir` 未設定 (`""`) | `doUpload()` L406 | `codes.Aborted: "CRL not configured"` | `gnsi_certz.go:404-407` |
| 認識不能なエンティティ型 | `doUpload()` L413-414 | `codes.Internal: "failed to find entity type: ..."` | `gnsi_certz.go:413-414` |
| エンティティファイル保存 (`saveEntities`) 失敗 | `doUpload()` L422-423 | `codes.Aborted: "Entity save err: ..."` | `gnsi_certz.go:422-423` |
| エンティティ有効化 (`activateEntity`) 失敗 | `doUpload()` L425-426 | `codes.Aborted: "Entity activate err: ..."` | `gnsi_certz.go:425-426` |
| CA トラストバンドルの型が X.509 以外 | `activateEntity()` L521 | `codes.InvalidArgument: "trustBundle type has to be X.509"` | `gnsi_certz.go:521` |
| CA トラストバンドルのエンコードが PEM 以外 | `activateEntity()` L524 | `codes.InvalidArgument: "trustBundle encoding has to be PEM"` | `gnsi_certz.go:524` |
| CA トラストバンドルが空 | `activateEntity()` L528 | `codes.InvalidArgument: "trustBundle cannot be empty"` | `gnsi_certz.go:528` |
| 証明書 (CertificateChain) が欠如 | `saveCertificate()` L558 | `codes.InvalidArgument: "Missing Certificate"` | `gnsi_certz.go:557-558` |
| 証明書の型が X.509 以外 | `saveCertificate()` L561 | `codes.InvalidArgument: "certificate type has to be X.509"` | `gnsi_certz.go:561` |
| 証明書のエンコードが PEM 以外 | `saveCertificate()` L564 | `codes.InvalidArgument: "certificate encoding has to be PEM"` | `gnsi_certz.go:564` |
| 証明書データが空 | `saveCertificate()` L567 | `codes.InvalidArgument: "Missing Cert data"` | `gnsi_certz.go:567` |
| GenerateCSR の鍵生成失敗 | `doGenerateCsr()` L333, L350 | `codes.Internal: "GenerateKey failed: ..."` | `gnsi_certz.go:333,350` |
| GenerateCSR で非対応 ECDSA 鍵サイズ | `doGenerateCsr()` L346 | `codes.InvalidArgument: "Unsupported key size for ECDSA: ..."` | `gnsi_certz.go:346` |
| GenerateCSR で非対応アルゴリズム | `doGenerateCsr()` L357 | `codes.InvalidArgument: "Unsupported Algorithm: ..."` | `gnsi_certz.go:357` |
| GenerateCSR での CSR 生成失敗 | `doGenerateCsr()` L363 | `codes.Internal: "CreateCertificateRequest failed: ..."` | `gnsi_certz.go:363` |

### STATE_DB への書き込み失敗

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---------|---------|------|----------|
| Redis 接続失敗 (`GetRedisDBClient` エラー) | `writeCredentialsMetadataToDB()` L1041 | エラーログ出力のみ。STATE_DB 未更新 (証明書は更新済みの可能性あり) | `gnsi_certz.go:1041-1044` |
| `sc.HSet()` 失敗 | `writeCredentialsMetadataToDB()` L1051 | エラーログ出力のみ ("Cannot write credentials metadata to the DB.")。処理継続 | `gnsi_certz.go:1051-1055` |
| 起動時 `loadCertzMetadata()` でメタファイル読み込み失敗 | `NewGNSICertzServer()` L126 | ログ出力のみ。`bootstrapDefaultProfile()` で初期値を生成してフォールバック | `gnsi_certz.go:126-131` |

### 未実装メソッドの呼び出し

| メソッド | エラーコード |
|---------|------------|
| `AddProfile` | `codes.Unimplemented` |
| `DeleteProfile` | `codes.Unimplemented` |
| `GetProfileList` | `codes.Unimplemented` |

### revertProfile による STATE_DB 復元の注意点

`revertProfile()` は失敗した Rotate RPC のロールバックとして呼ばれる。処理順は以下のとおり:

1. Cert が `Final != true` → `atomicSetSrvCertKeyPair()` でファイル復元 → `writeEntityFreshness()` で STATE_DB を前回値に戻す → 新ファイル削除
2. TrustBundle が `Final != true` → ファイル復元 → STATE_DB 更新
3. CrlBundle が `Final != true` → CRL ディレクトリ復元 → STATE_DB 更新
4. AuthPolicy が `Final != true` → バックアップからファイル復元 → STATE_DB 更新

`atomicSetSrvCertKeyPair()` 等のファイル復元が失敗してもログのみで処理継続する (`log.V(0).Infof("Failed to revert...")`)。  
ファイル復元失敗時は STATE_DB が前回値で更新されるが、物理ファイルは中途半端な状態のままになる可能性がある。
<!-- /failure -->
