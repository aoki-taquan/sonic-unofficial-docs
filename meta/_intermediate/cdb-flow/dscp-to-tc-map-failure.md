# dscp-to-tc-map — Phase D: 失敗挙動

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 抽出した失敗パターン

### 1. 不正 DSCP / TC 値 → `task_invalid_entry`

`DscpToTcMapHandler::convertFieldValuesToAttributes()` (qosorch.cpp:235-253) は DSCP キーと TC 値を `stoi()` で uint8_t へ変換するだけで **範囲バリデーションがない**。

- DSCP フィールドに非数値文字列 → `std::invalid_argument` 例外 → ハンドラが `task_invalid_entry` を返す（qosorch.cpp:147）
- TC 値に `stoi()` 変換できない文字列も同様
- `#define DSCP_MAX_VAL 63` (qosorch.cpp:119) は `DscpToFcMapHandler` の検証に使われるが、**`DscpToTcMapHandler` では使われない**（qosorch.cpp:1062-1064 との対比）

未知オペレーション (SET でも DEL でもない) → `SWSS_LOG_ERROR("Unknown operation type %s", ...)` + `task_invalid_entry` (qosorch.cpp:198-199)

### 2. `sai_qos_map_api` 失敗 → `task_failed`

| 操作 | SAI API | エラーログ | 戻り値 |
|------|---------|-----------|--------|
| 新規作成 | `create_qos_map(&sai_object, gSwitchId, ...)` | `"Failed to create dscp_to_tc map. status:%d"` | `SAI_NULL_OBJECT_ID` → `task_failed` |
| 既存更新 | `set_qos_map_attribute(sai_object, &attributes[0])` | `"Failed to modify map. status:%d"` | false → `task_failed` |
| 削除 | `remove_qos_map(sai_object)` | `"Failed to remove DSCP_TO_TC map, status:%d"` | false → `task_failed` |

- `addQosItem()`: `sai_status != SAI_STATUS_SUCCESS` → `SWSS_LOG_ERROR` + `return SAI_NULL_OBJECT_ID` (qosorch.cpp:274-277)
- `DscpToTcMapHandler::removeQosItem()`: `sai_status != SAI_STATUS_SUCCESS` → `SWSS_LOG_ERROR` + `return false` (qosorch.cpp:290-293)
- `modifyQosItem()` は基底 `QosMapHandler::modifyQosItem()` を継承 (qosorch.cpp:204-213)
- `task_failed` は orchagent が再試行せずエラーとして記録する

### 3. MAP 削除時の参照存在チェック → `task_need_retry` (ロック)

DEL コマンド受信時 (qosorch.cpp:174-194):

1. `sai_object == SAI_NULL_OBJECT_ID` (MAP が存在しない) → `"Object with name:%s not found."` + `task_invalid_entry` (qosorch.cpp:176-179)
2. `gQosOrch->isObjectBeingReferenced(...)` が true の場合:
   - `m_pendingRemove = true` をセット (qosorch.cpp:185)
   - `"Can't remove object %s due to being referenced (%s)"` をログ
   - `task_need_retry` を返す → orchagent が後で再実行
3. pending_remove=true 中に SET が来ると → `task_need_retry` (qosorch.cpp:136-139)
4. 参照解除後の再試行で `removeQosItem()` が成功 → `task_success`

参照元: `PORT_QOS_MAP` の `dscp_to_tc_map` フィールド、`TUNNEL_DECAP_TABLE` の tunnel qos map

## ソース根拠

- `qosorch.cpp:119` — `DSCP_MAX_VAL 63` 定義（DscpToTcMapHandler では未使用）
- `qosorch.cpp:124-201` — `QosMapHandler::processWorkItem()`（共通フロー）
- `qosorch.cpp:147` — `convertFieldValuesToAttributes` 失敗 → `task_invalid_entry`
- `qosorch.cpp:153-155` — `modifyQosItem` 失敗 → `task_failed`
- `qosorch.cpp:164-166` — `addQosItem` 失敗 → `task_failed`
- `qosorch.cpp:176-179` — 存在しない MAP への DEL → `task_invalid_entry`
- `qosorch.cpp:181-186` — 参照中 MAP への DEL → `m_pendingRemove=true` + `task_need_retry`
- `qosorch.cpp:198-199` — 未知 op → `task_invalid_entry`
- `qosorch.cpp:235-253` — `DscpToTcMapHandler::convertFieldValuesToAttributes()`
- `qosorch.cpp:256-282` — `DscpToTcMapHandler::addQosItem()`
- `qosorch.cpp:284-296` — `DscpToTcMapHandler::removeQosItem()`
- `qosorch.cpp:298-303` — `QosOrch::handleDscpToTcTable()`
