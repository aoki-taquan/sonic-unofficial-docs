# SWITCH_TRIMMING 例外条件調査メモ

ソース: `sonic-swss/orchagent/switchorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件

1. **size フィールド削除不可** — DEL 操作で `size` を削除しようとすると
   `"Failed to remove switch trimming size configuration: operation is not supported"` を LOG_ERROR して `return false`。

2. **DSCP mode capability 未サポート** — `validateTrimDscpModeCap()` が false を返すと
   `"Failed to validate switch trimming DSCP mode: capability is not supported"` を LOG_ERROR して `return false`。

3. **DSCP mode 削除不可** — `dscp.mode` の DEL は
   `"Failed to remove switch trimming DSCP configuration: operation is not supported"` を LOG_ERROR して拒否。

4. **queue_index capability 未サポート** — `validateTrimQueueIndexCap()` が false を返すと
   `"Failed to validate switch trimming queue index: capability is not supported"` を LOG_ERROR。

5. **SAI set 失敗** — size / DSCP mode / queue_index の SAI 設定失敗時はそれぞれ対応するエラーメッセージを LOG_ERROR して `return false`。

6. **ASIC/CONFIG_DB 乖離** — SET/DEL 時に乖離を検出すると
   `"Failed to set/remove switch trimming: ASIC and CONFIG DB are diverged"` を LOG_ERROR。

7. **空キー** — key が空文字列だと `"Failed to parse switch trimming key: empty string"` を LOG_ERROR してスキップ。
