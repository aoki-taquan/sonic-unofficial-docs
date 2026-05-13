# CONFIG_DB 例外条件分析: MAP_PFC_PRIORITY_TO_QUEUE

## Consumer

- `orchagent` / `QosOrch` / `PfcToQueueHandler` (`sonic-swss/orchagent/qosorch.cpp`): `MAP_PFC_PRIORITY_TO_QUEUE` テーブルを購読し、`handlePfcToQueueTable` → `PfcToQueueHandler::processWorkItem` に委譲。

## 例外条件

### 1. pfc_priority / qindex が 0-7 の範囲外 → YANG が拒否
- ソース: `sonic-pfc-priority-queue-map.yang` — `pfc_priority` / `qindex` ともに `pattern "[0-7]?"` で制約。
- YANG バリデーション段階で弾かれ、CONFIG_DB への書き込みが拒否される。

### 2. フィールド変換失敗 → task_invalid_entry
- ソース: `qosorch.cpp` L147, L179, L199 — `convertFieldValuesToAttributes` が false を返した場合。
- `stoi()` による変換例外は呼び出し元がキャッチし `task_invalid_entry` を返す。

### 3. 削除時に他オブジェクトから参照中 → task_need_retry (pendingRemove)
- ソース: `qosorch.cpp` L180-186 — `isObjectBeingReferenced()` が true の場合、`m_pendingRemove = true` にして `task_need_retry` を返す。
- 参照が解除されるまで削除は保留され、次のイベントループで再試行される。

### 4. 削除対象エントリが存在しない → task_invalid_entry + SWSS_LOG_ERROR
- ソース: `qosorch.cpp` L179 — SAI object が NULL の場合 `"Object with name not found"` をログし `task_invalid_entry`。

### 5. SAI create/modify 失敗 → task_failed + SWSS_LOG_ERROR
- ソース: `qosorch.cpp` L977, L1032 — `sai_qos_map_api->create_qos_map()` が `SAI_STATUS_SUCCESS` 以外を返した場合。
- SAI オブジェクト ID として `SAI_NULL_OBJECT_ID` を返し、上位が `task_failed` を記録。

### 6. マップ名の長さ・文字制約
- ソース: `sonic-pfc-priority-queue-map.yang` — `name` は `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` 計 1-32 文字。
- 違反時は YANG バリデーションで拒否。

## デフォルト値

- YANG に `default` 定義なし。エントリが未設定の場合、当該マップ名は orchagent に登録されず、PORT_QOS_MAP からの参照が解決できない。
