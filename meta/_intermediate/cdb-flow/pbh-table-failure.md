# PBH_TABLE 失敗挙動スキャンノート (Phase D)

## スキャン対象

- `sonic-swss/orchagent/pbhorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/pbh/pbhmgr.cpp` (同 ref)

## SET 時の失敗パターン

### parsePbhTable() 失敗 (pbhmgr.cpp:462-491)
- `interface_list` フィールド parse 失敗 → `return false` → `pendingSetupMap` に追加されない → CONFIG_DB エントリは残るが SAI 未反映。retry なし。
- `description` フィールド parse 失敗 → 同様。
- `validatePbhTable()` で `interface_list` または `description` 未設定 → `SWSS_LOG_ERROR("Validation error: missing mandatory field(...)")` → `return false`。

### createPbhTable() 失敗 (pbhorch.cpp:229-300)
- 重複作成 → `SWSS_LOG_ERROR("...object already exists")` → `return false`
- `validateAddType()` 失敗 → 同上
- `validateAddStage()` 失敗 → 同上
- `validateAddPorts()` 失敗（ポート未解決以外） → `SWSS_LOG_ERROR("Failed to configure PBH table(%s) ports")` → `return false`
- `pbhTable.validate()` 失敗 → `SWSS_LOG_ERROR("Failed to validate PBH table(%s)")` → `return false`
- `aclOrch->addAclTable()` 失敗 (SAI エラー) → `SWSS_LOG_ERROR("Failed to create PBH table(%s) in SAI")` → `return false`
- `pbhHlpr.addPbhTable()` 失敗 → `SWSS_LOG_ERROR("Failed to add PBH table(%s) to internal cache")` → `return false`

### deployPbhTableSetupTasks() の失敗ハンドリング (pbhorch.cpp:405-436)
- `createPbhTable()` または `updatePbhTable()` が `false` を返した場合: `SWSS_LOG_ERROR("Failed to create/update PBH table(%s): ASIC and CONFIG DB are diverged")`
- **重要**: `it = map.erase(it)` で **retry なし**。CONFIG_DB と SAI が diverged 状態になる。

### タスク重複チェック (pbhorch.cpp:1577-1582)
- `pbhTaskExists(table)` が true の場合: `SWSS_LOG_WARN("Unable to process PBH table(%s): task already exists: adding a retry")` → `it++` で retry。

## DEL 時の失敗パターン

### deployPbhTableRemoveTasks() (pbhorch.cpp:438-475)
- オブジェクト不存在 → `SWSS_LOG_ERROR("Failed to remove PBH table(%s): object doesn't exist")` → erase (no retry)
- 依存関係あり（PBH_RULE が参照中）→ `SWSS_LOG_NOTICE("Unable to remove PBH table(%s): object has dependencies: adding a retry")` → `it++` (retry あり、PBH_RULE DEL 後に自動回復)
- `removePbhTable()` 失敗 → `SWSS_LOG_ERROR("Failed to remove PBH table(%s): ASIC and CONFIG DB are diverged")` → erase (no retry)

## エラーログとリカバリまとめ

| 失敗ケース | ログレベル | retry | 回復手順 |
|---|---|---|---|
| 必須フィールド欠損 (`interface_list` / `description`) | ERROR (pbhmgr) | なし | 両フィールドを補完して再 SET |
| 不明フィールド | WARN (pbhmgr) | N/A (スキップ継続) | 不要 |
| SAI addAclTable() 失敗 | ERROR (pbhorch) | なし | 原因調査後に再 SET |
| タスク重複競合 | WARN (pbhorch) | 自動 (次ループ) | 不要 |
| DEL: 依存 PBH_RULE あり | NOTICE (pbhorch) | 自動 (PBH_RULE DEL 後) | `PBH_RULE` を先に削除する |
| DEL: SAI removePbhTable() 失敗 | ERROR (pbhorch) | なし | 原因調査後に再 DEL |

## STATE_DB / エラーテーブルへの書き込み

`PbhOrch` は STATE_DB に `PBH_TABLE` のステータスを書き込まない（`ACL_TABLE` の `setAclTableStatus()` に相当するものはない）。`ERROR_TABLE` への書き込みもなし。失敗は syslog のみ。
