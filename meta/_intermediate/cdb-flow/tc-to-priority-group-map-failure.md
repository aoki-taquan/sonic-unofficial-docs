# TC_TO_PRIORITY_GROUP_MAP — 失敗挙動調査 (Phase D)

調査対象: `sonic-swss/orchagent/qosorch.cpp`

## 処理エントリーポイント

`QosOrch::handleTcToPgTable` (qosorch.cpp:930-934) が `TcToPgHandler::processWorkItem` に委譲。
実体は基底クラス `QosMapHandler::processWorkItem` (qosorch.cpp:124-201)。

## SET 失敗パターン

### 1. pending remove 中の SET
- 条件: 同名エントリが `m_pendingRemove = true` の状態に SET が来た場合
- ログ: `SWSS_LOG_NOTICE "Entry TC_TO_PRIORITY_GROUP_MAP <name> is pending remove, need retry"`
- 結果: `task_need_retry`（自動リトライ）
- ソース: `qosorch.cpp:136-140`

### 2. `convertFieldValuesToAttributes` 失敗 = stoi() 例外
- 条件: `tc` フィールド（key）または `pg` フィールド（value）が数値に変換不可（空文字列、非数値文字列）
- 挙動: `stoi()` が例外をスロー → `convertFieldValuesToAttributes` が false を返す
- 注意: 例外をキャッチするコードは存在しない。C++ の未捕捉例外として propagate する
- 実際の動作: orchagent プロセスで std::exception を catch する上位コードがあれば task_invalid_entry に相当する動作となる
- ソース: `qosorch.cpp:884-901`（`TcToPgHandler::convertFieldValuesToAttributes`）

### 3. SAI create_qos_map 失敗（新規エントリ）
- 条件: `sai_qos_map_api->create_qos_map()` が `SAI_STATUS_SUCCESS` 以外を返す
- ログ: `SWSS_LOG_ERROR "Failed to create tc_to_pg map. status:%d"`
- 結果: `SAI_NULL_OBJECT_ID` 返却 → `addQosItem` 失敗 → `SWSS_LOG_ERROR "Failed to create [TC_TO_PRIORITY_GROUP_MAP:<name>]"` → `task_failed`
- ソース: `qosorch.cpp:920-924` (addQosItem), `qosorch.cpp:162-166` (processWorkItem)

### 4. SAI set_qos_map_attribute 失敗（既存エントリ更新）
- 条件: `sai_qos_map_api->set_qos_map_attribute()` が `SAI_STATUS_SUCCESS` 以外を返す
- ログ: `SWSS_LOG_ERROR "Failed to modify map. status:%d"`
- 結果: `modifyQosItem` false → `SWSS_LOG_ERROR "Failed to set [TC_TO_PRIORITY_GROUP_MAP:<name>]"` → `task_failed`
- ソース: `qosorch.cpp:204-213` (modifyQosItem), `qosorch.cpp:151-155` (processWorkItem)

## DEL 失敗パターン

### 5. 存在しないエントリへの DEL
- 条件: `m_qos_maps["TC_TO_PRIORITY_GROUP_MAP"]` に該当名が存在しない
- ログ: `SWSS_LOG_ERROR "Object with name:<name> not found."`
- 結果: `task_invalid_entry`
- ソース: `qosorch.cpp:176-179`

### 6. 参照中エントリの DEL
- 条件: PORT_QOS_MAP または TUNNEL_DECAP_TABLE が本マップを参照中
- ログ: `SWSS_LOG_NOTICE "Can't remove object <name> due to being referenced (<hint>)"`
- 結果: `m_pendingRemove = true` → `task_need_retry`（参照解放まで自動リトライ）
- ソース: `qosorch.cpp:181-186`

### 7. SAI remove_qos_map 失敗
- 条件: `sai_qos_map_api->remove_qos_map()` が失敗
- ログ: `SWSS_LOG_ERROR "Failed to remove QoS map. db name:<name> sai object:<oid>"`
- 結果: `task_failed`
- ソース: `qosorch.cpp:188-191`

### 8. 未知の operation
- 条件: SET でも DEL でもない op 文字列
- ログ: `SWSS_LOG_ERROR "Unknown operation type <op>"`
- 結果: `task_invalid_entry`
- ソース: `qosorch.cpp:197-199`

## 回復挙動まとめ

| パターン | task 結果 | 自動回復 | ログレベル |
|---------|----------|---------|----------|
| pending remove 中 SET | `task_need_retry` | ✅ 参照解放後に自動解消 | NOTICE |
| stoi() 例外 | プロセス例外 or `task_invalid_entry` | ❌ | (exception) |
| SAI create 失敗 | `task_failed` | ❌ | ERROR |
| SAI modify 失敗 | `task_failed` | ❌ | ERROR |
| 存在しない DEL | `task_invalid_entry` | ❌ | ERROR |
| 参照中 DEL | `task_need_retry` | ✅ 参照解放後に自動解消 | NOTICE |
| SAI remove 失敗 | `task_failed` | ❌ | ERROR |
| 未知 op | `task_invalid_entry` | ❌ | ERROR |

## 部分適用に関する注意

`TcToPgHandler::convertFieldValuesToAttributes` は全 TC→PG エントリを一括で SAI map list に変換し、1 回の `create_qos_map` / `set_qos_map_attribute` で適用する。個別エントリの部分失敗は発生しない（全件成功か全件失敗）。

ただし、既存マップの更新（SET）で `modifyQosItem` が失敗した場合、旧値が SAI に残る（rollback なし）。

## STATE_DB / ERROR_TABLE への記録

なし。`QosOrch` は `TC_TO_PRIORITY_GROUP_MAP` の処理結果を STATE_DB や ERROR_TABLE に書き出さない。失敗の確認は orchagent ログまたは `sonic-db-cli ASIC_DB` での直接確認が必要。
