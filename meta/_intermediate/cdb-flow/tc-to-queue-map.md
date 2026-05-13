# TC_TO_QUEUE_MAP 例外条件調査メモ

ソース: `sonic-swss/orchagent/qosorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件

1. **pending remove 中の SET はリトライ** — DEL 操作が参照されているため保留中（`m_pendingRemove = true`）の
   エントリに対して SET を試みると `"Entry TC_TO_QUEUE_MAP <name> is pending remove, need retry"` を LOG_NOTICE し
   `task_need_retry` を返す。Consumer はタスクをキューに戻す。

2. **参照中のエントリは DEL できない** — ポートに割り当てられているマップを DEL しようとすると
   `"Can't remove object <name> due to being referenced (<hint>)"` を LOG_NOTICE し
   `m_pendingRemove = true` をセットして `task_need_retry` を返す。
   参照が外れるまで削除は保留される。

3. **SAI create 失敗** — `sai_qos_map_api->create_qos_map()` が `SAI_STATUS_SUCCESS` 以外を返すと
   `"Failed to create tc_to_queue map. status:%d"` を LOG_ERROR し `SAI_NULL_OBJECT_ID` を返す。
   `processWorkItem` はそれを受けて `"Failed to create [TC_TO_QUEUE_MAP:<name>]"` を LOG_ERROR し
   `task_failed` を返す。

4. **SAI modify 失敗** — 既存マップの変更時に `modifyQosItem()` が失敗すると
   `"Failed to set [TC_TO_QUEUE_MAP:<name>]"` を LOG_ERROR して `task_failed` を返す。

5. **存在しない object への DEL** — SAI object ID が null (未作成) のエントリを DEL しようとすると
   `"Object with name:<name> not found."` を LOG_ERROR し `task_invalid_entry` を返す。

6. **`stoi()` 変換失敗** — フィールドキー（TC 値）または値（queue_index）が整数として解釈できない場合、
   `stoi()` が例外を投げ `convertFieldValuesToAttributes()` が異常終了して `task_invalid_entry` を返す。
