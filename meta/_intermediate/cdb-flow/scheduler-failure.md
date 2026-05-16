# SCHEDULER — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-scheduler)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/qosorch.cpp` `handleSchedulerTable()`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `type` が `DWRR`/`WRR`/`STRICT` 以外の不正値 | `handleSchedulerTable()` L1394 | `task_invalid_entry` を返す。エントリ全体を破棄、SAI 非反映 | `SWSS_LOG_ERROR("Unknown scheduler type value:%s")` | `qosorch.cpp:1394-1396` |
| `meter_type` が `packets`/`bytes` 以外の不正値 | `handleSchedulerTable()` L1407 | `scheduler_meter_map.at()` が `std::out_of_range` 例外をスロー → **orchagent プロセスクラッシュ** | uncaught exception（syslog にスタックトレース） | `qosorch.cpp:1407` |
| 未知フィールド（例: `priority`）を含む SET | `handleSchedulerTable()` L1434 | `task_invalid_entry` を返す。そのエントリの全フィールド（`type`/`weight`/`meter_type` 等を含む）が SAI 未反映 | `SWSS_LOG_ERROR("Unknown field:%s")` | `qosorch.cpp:1434-1435` |
| `weight` に 0〜255 範囲外の値（YANG `range "1..100"` 違反） | `handleSchedulerTable()` L1401–1404 | `(uint8_t)stoi()` で暗黙キャスト・切り捨て。コード側バリデーションなし、異常値が SAI に渡る | なし | `qosorch.cpp:1401-1404` |
| SAI `create_scheduler()` 失敗（新規オブジェクト作成時） | `handleSchedulerTable()` L1460–1467 | `handleSaiCreateStatus()` の返り値に従い処理。`task_success` 以外なら失敗ステータスを返す | `SWSS_LOG_ERROR("Failed to create scheduler profile [%s:%s], rv:%d")` | `qosorch.cpp:1463-1466` |
| SAI `set_scheduler_attribute()` 失敗（既存オブジェクト更新時） | `handleSchedulerTable()` L1446–1454 | `handleSaiSetStatus()` の返り値に従い処理 | `SWSS_LOG_ERROR("fail to set scheduler attribute, id:%d")` | `qosorch.cpp:1449-1454` |
| エントリが既存で SAI オブジェクト ID が `SAI_NULL_OBJECT_ID` | `handleSchedulerTable()` L1362–1366 | `task_invalid_entry` を返す（内部不整合の検出） | `SWSS_LOG_ERROR("Error sai_object must exist for key %s")` | `qosorch.cpp:1362-1366` |
| エントリが `m_pendingRemove=true` 状態で SET 発行 | `handleSchedulerTable()` L1368–1372 | `task_need_retry` を返す。DEL 完了まで SET は保留 | `SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry")` | `qosorch.cpp:1368-1372` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 存在しないオブジェクトの DEL（SAI オブジェクト ID が `SAI_NULL_OBJECT_ID`） | `handleSchedulerTable()` L1478–1482 | `task_invalid_entry` を返す | `SWSS_LOG_ERROR("Object with name:%s not found.")` | `qosorch.cpp:1478-1482` |
| QUEUE が参照中の SCHEDULER を DEL | `handleSchedulerTable()` L1484–1490 | `m_pendingRemove=true` をセットして `task_need_retry` を返す。SAI scheduler profile は削除されず、QUEUE 参照が解除されるまでリトライを繰り返す | `SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)")` | `qosorch.cpp:1484-1490` |
| SAI `remove_scheduler()` 失敗 | `handleSchedulerTable()` L1490–1497 | `handleSaiRemoveStatus()` の返り値に従い処理。CONFIG_DB からは削除されても ASIC に古いプロファイルが残留する可能性あり | `SWSS_LOG_ERROR("Failed to remove scheduler profile. db name:%s sai object:%" PRIx64)` | `qosorch.cpp:1492-1497` |

### 検出ロジック補足

- **`priority` フィールドの DEL エントリ全破棄**: `sonic-scheduler.yang` に `leaf priority { type uint8 { range "0..9"; } }` が定義されているが、`handleSchedulerTable` の if-else チェーンに対応分岐がない。`priority` フィールドを含む SET エントリは **すべてのフィールドが** SAI 未反映になる（partial 適用なし）。
- **`meter_type` クラッシュリスク**: `scheduler_meter_map` は `std::unordered_map<string, sai_meter_type_t>` で `"packets"` と `"bytes"` のみを保持。`.at()` は存在しないキーで `std::out_of_range` をスローし、orchagent プロセスごとクラッシュする。YANG 的には 2 値のみ許可だが、直接 `sonic-db-cli` 書き込み時は要注意。
- **`m_pendingRemove` による SET/DEL シリアライズ**: QUEUE 参照がある状態の SCHEDULER に対し DEL → SET の順でオペレーションを発行しても、DEL が `task_need_retry` を返し続けるため SET も保留される。QUEUE 参照を解除してから DEL → SET を再投入すること。
- **`weight` の暗黙オーバーフロー**: YANG では `range "1..100"` だが qosorch 側は `(uint8_t)stoi(fvValue(*i))` のみ。256 以上の値は 0 にオーバーフロー、負数は未定義動作となりベンダー SAI に渡る。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` (scheduler 関連) | 7 | `qosorch.cpp:871, 1362, 1394, 1449, 1463, 1493; qosorch.cpp:1526, 1581, 1607` |
| `task_invalid_entry` 返却 | 4 | `qosorch.cpp:1366, 1396, 1435, 1481` |
| `task_need_retry` 返却 | 2 | `qosorch.cpp:1372, 1490` |
| `std::out_of_range` リスク (`.at()`) | 1 | `qosorch.cpp:1407` |
| `m_pendingRemove = true` | 1 | `qosorch.cpp:1488` |

<!-- /failure -->
