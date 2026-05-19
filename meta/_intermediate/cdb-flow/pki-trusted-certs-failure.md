# pki-trusted-certs — Phase D: 失敗挙動 (failure)

## 調査対象

- `sonic-gnmi/gnmi_server/gnsi_certz.go`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-pki.yang`
- `sonic-mgmt-common/cvl/testdata/schema/sonic-security-global.yang`
- `sonic-mgmt-common/cvl/cvl_test.go:2506-2537`

## CVL バリデーション失敗

### SET 時

| 操作 | 失敗条件 | CVL エラーコード | ErrAppTag |
|------|---------|-----------------|-----------|
| `SECURITY_GLOBAL\|global security_profile=X` 書き込み | `SECURITY_PROFILES\|X` が存在しない | `CVL_SEMANTIC_ERROR` | `invalid-value` (leafref violation) |

### DEL 時

| 操作 | 失敗条件 | CVL エラーコード | ErrAppTag |
|------|---------|-----------------|-----------|
| `SECURITY_PROFILES\|X` 削除 | `SECURITY_GLOBAL\|global.security_profile=X` が参照中 | `CVL_SEMANTIC_ERROR` | `instance-in-use` |

証跡: `cvl_test.go:2506-2537` — `TestValidateEditConfig_Delete_Dep_Leafref_singleton` で確認。

## gNSI Certz RPC 失敗

### Rotate RPC (certz.Rotate streaming RPC)

| 失敗ケース | gRPC ステータスコード | revertProfile 呼ばれるか |
|-----------|---------------------|------------------------|
| 並行 Rotate 試行 | `codes.Aborted` — "concurrent certz.Rotate RPCs are not allowed" | 不要（未着手）|
| ストリーム途中で EOF (Finalize なし) | `codes.Aborted` — "No Finalize message" | ○ (`revertProfile`) |
| ストリーム recv エラー | `codes.Aborted` — "Stream recv err: ..." | ○ |
| processRotateRequest 失敗 | `codes.Aborted` — "Process err: ..." | ○ |
| Finalize 後の finalizeProfile 失敗 | `codes.Unknown` — "Failed to remove the old credentials: ..." | — |

### Upload 内バリデーション失敗 (doUpload)

| 失敗ケース | gRPC ステータスコード |
|-----------|---------------------|
| `entities` が空 | `codes.InvalidArgument` — "entity cannot be empty" |
| `created_on == 0` | `codes.InvalidArgument` — "created_on cannot be empty" |
| `version` が空文字 | `codes.InvalidArgument` — "version cannot be empty" |
| CRL エンティティ & `CertCRLConfig` 未設定 | `codes.Aborted` — "CRL not configured" |
| エンティティ型が不明 | `codes.Internal` — "failed to find entity type: ..." |
| saveEntities 失敗 | `codes.Aborted` — "Entity save err: ..." |
| activateEntity 失敗 | `codes.Aborted` — "Entity activate err: ..." |

### 未実装 RPC

| RPC | gRPC ステータスコード |
|-----|---------------------|
| `AddProfile` | `codes.Unimplemented` |
| `DeleteProfile` | `codes.Unimplemented` |
| `GetProfileList` | `codes.Unimplemented` |

## CONFIG_DB への影響

- gNSI Certz RPC 失敗時に CONFIG_DB は変更されない（RPC は CONFIG_DB を参照・書き込みしない）
- CVL エラーは `sonic-configd` / `translib` レイヤで返却され、CONFIG_DB への書き込みは行われない
- STATE_DB (`CREDENTIALS|CERT|<profileID>`) は `revertProfile` によってロールバックされるが、gNSI Certz プロセスがクラッシュした場合（`writeEntityFreshness` の途中）は、一部エンティティのフレッシュネスのみが記録された中間状態が残りうる
