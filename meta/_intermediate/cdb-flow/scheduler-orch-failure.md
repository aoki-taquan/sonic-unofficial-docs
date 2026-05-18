# scheduler-orch — 失敗挙動マトリクス (Phase D)

調査対象: `sonic-swss/orchagent/qosorch.cpp` `handleSchedulerTable()` L1347–1509 (commit 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 失敗条件一覧

### SET_COMMAND（CREATE / UPDATE）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 既存オブジェクトが `m_pendingRemove == true` の状態で SET | `qosorch.cpp:L1366-1369` | `task_need_retry` — エントリは `m_toSync` に残留し次回再試行 | `"Entry %s %s is pending remove, need retry"` (SWSS_LOG_NOTICE) | `qosorch.cpp:1368` |
| `type` フィールドに未知値（`DWRR`/`WRR`/`STRICT` 以外） | `qosorch.cpp:L1393-1396` | `task_invalid_entry` — エントリ全体が SAI 未反映 | `"Unknown scheduler type value:%s"` (SWSS_LOG_ERROR) | `qosorch.cpp:1394` |
| `meter_type` に未知値（`packets`/`bytes` 以外） | `qosorch.cpp:L1407` | `std::out_of_range` 例外 → **orchagent クラッシュ**（例外未キャッチ） | なし（シグナル終了） | `qosorch.cpp:1407` |
| `priority` フィールドを含む SET | `qosorch.cpp:L1436-1438` | `task_invalid_entry` — エントリ全体が SAI 未反映 | `"Unknown field:priority"` (SWSS_LOG_ERROR) | `qosorch.cpp:1437` |
| 未知フィールド（`priority` 以外） | `qosorch.cpp:L1436-1438` | `task_invalid_entry` — エントリ全体が SAI 未反映 | `"Unknown field:%s"` (SWSS_LOG_ERROR) | `qosorch.cpp:1437` |
| SAI `create_scheduler()` 失敗（新規作成時） | `qosorch.cpp:L1460-1469` | `handleSaiCreateStatus()` の戻り値に委ねる（通常 `task_failed` または `task_need_retry`） | `"Failed to create scheduler profile [%s:%s], rv:%d"` (SWSS_LOG_ERROR) | `qosorch.cpp:1463` |
| SAI `set_scheduler_attribute()` 失敗（既存更新時） | `qosorch.cpp:L1447-1454` | `handleSaiSetStatus()` の戻り値に委ねる（通常 `task_failed` または `task_need_retry`） | `"fail to set scheduler attribute, id:%d"` (SWSS_LOG_ERROR) | `qosorch.cpp:1449` |

### DEL_COMMAND

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 存在しないオブジェクトへの DEL | `qosorch.cpp:L1478-1481` | `task_invalid_entry` — 何もしない | `"Object with name:%s not found."` (SWSS_LOG_ERROR) | `qosorch.cpp:1480` |
| QUEUE から参照中の SCHEDULER を DEL | `qosorch.cpp:L1483-1488` | `m_pendingRemove = true` + `task_need_retry` — SAI DEL は保留、参照解除後に自動 DEL | `"Can't remove object %s due to being referenced (%s)"` (SWSS_LOG_NOTICE) | `qosorch.cpp:1486-1488` |
| SAI `remove_scheduler()` 失敗 | `qosorch.cpp:L1491-1498` | `handleSaiRemoveStatus()` の戻り値に委ねる（通常 `task_failed` または `task_need_retry`） | `"Failed to remove scheduler profile. db name:%s sai object:..."` (SWSS_LOG_ERROR) | `qosorch.cpp:1492` |

## 補足

- `task_invalid_entry` は `m_toSync` からエントリを破棄し、再試行しない。CONFIG_DB 側の SET は成功しているが SAI 反映はゼロ。
- `task_need_retry` は `m_toSync` にエントリを残留させ次の `doTask()` で再評価する。
- `meter_type` の未知値による `std::out_of_range` クラッシュは、YANG enum バリデーション（2 値のみ）が機能していれば通常発生しない。`sonic-db-cli` 等で直接投入する場合のみリスクあり。
