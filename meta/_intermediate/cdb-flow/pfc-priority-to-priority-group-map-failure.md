# Phase D: 失敗挙動 — PFC_PRIORITY_TO_PRIORITY_GROUP_MAP

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 抽出した失敗パターン

### 1. invalid_entry: priority/queue 値不正

`PfcPrioToPgHandler::convertFieldValuesToAttributes()` (qosorch.cpp:937-954) では
フィールド名 (pfc_priority) とフィールド値 (pg) をそれぞれ `stoi()` で変換する。
非数値文字列を渡すと `std::invalid_argument` 例外が上位の `processWorkItem` に伝播し、
`task_invalid_entry` が返される (qosorch.cpp:147)。

- トリガー: `pfc_priority` フィールド名または `pg` 値が数値以外 (空文字・アルファベット等)
- ログ: なし (例外による変換失敗)
- 結果: `task_invalid_entry` → エントリ破棄、再キューなし

同様に DEL 操作で該当 map 名が SAI に存在しない場合:
- ログ: `"Object with name:%s not found."` (qosorch.cpp:178)
- 結果: `task_invalid_entry`

不明な op (SET/DEL 以外):
- ログ: `"Unknown operation type %s"` (qosorch.cpp:198)
- 結果: `task_invalid_entry`

### 2. failed: SAI create/modify/remove 失敗

SET 操作で SAI オブジェクト未作成時 (`addQosItem` 失敗):
- 実装: `sai_qos_map_api->create_qos_map()` が `SAI_STATUS_SUCCESS` 以外を返す
- ログ: `"Failed to create pfc_priority_to_queue map. status:%d"` (qosorch.cpp:977)
  ※ ログ文字列はコピー由来で "pfc_priority_to_queue" と記載されるが実際は PG map
- 結果: `SAI_NULL_OBJECT_ID` 返却 → `task_failed` (qosorch.cpp:166)

SET 操作で SAI オブジェクト更新時 (`modifyQosItem` 失敗):
- ログ: `"Failed to set [%s:%s]"` (qosorch.cpp:153)
- 結果: `task_failed` (qosorch.cpp:155)

DEL 操作で SAI remove 失敗 (`removeQosItem` 失敗):
- ログ: `"Failed to remove QoS map. db name:%s sai object:%"PRIx64` (qosorch.cpp:190)
- 結果: `task_failed` (qosorch.cpp:191)

### 3. need_retry: 参照中エントリの DEL

DEL 操作時に `isObjectBeingReferenced()` が true の場合
(= PORT_QOS_MAP 等から参照が残っている):
- ログ: `"Can't remove object %s due to being referenced (%s)"` (qosorch.cpp:184)
- 副作用: `m_pendingRemove = true` フラグがセットされる
- 結果: `task_need_retry` → Consumer キューへ戻し、参照解除後に再処理

SET 操作時に `m_pendingRemove == true` の場合 (前回 DEL 保留中に SET が来た):
- ログ: `"Entry %s %s is pending remove, need retry"` (qosorch.cpp:138)
- 結果: `task_need_retry`

## コード行証跡

| パターン | ファイル | 行 |
|---------|---------|-----|
| `convertFieldValuesToAttributes` (stoi) | qosorch.cpp | 947-948 |
| SET convertFieldValues 失敗 → invalid_entry | qosorch.cpp | 145-147 |
| SAI create 失敗 ログ | qosorch.cpp | 977 |
| addQosItem SAI NULL → task_failed | qosorch.cpp | 162-166 |
| modifyQosItem 失敗 → task_failed | qosorch.cpp | 151-155 |
| removeQosItem 失敗 → task_failed | qosorch.cpp | 188-191 |
| isObjectBeingReferenced DEL → need_retry | qosorch.cpp | 181-186 |
| pendingRemove SET → need_retry | qosorch.cpp | 136-139 |
| Object not found DEL → invalid_entry | qosorch.cpp | 178-179 |
| Unknown op → invalid_entry | qosorch.cpp | 198-199 |
