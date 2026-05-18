# exp-to-fc-map — 失敗挙動調査 (Phase D)

調査対象: `EXP_TO_FC_MAP` テーブル  
Consumer: `QosOrch::handleExpToFcTable()` / `QosOrch::doTask()` (`orchagent/qosorch.cpp`)

## 失敗パターン一覧

### SET 時

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| `allPortsReady() == false` | `doTask()` L2258-2261 | 早期 return、`m_toSync` 滞留 | ポート準備完了まで暗黙 retry |
| EXP 値が負数 | `convertFieldValuesToAttributes()` L1152-1155 | `SWSS_LOG_ERROR` → `return false` → `task_invalid_entry` → erase | なし（silent drop） |
| EXP 値 > 7 (`EXP_MAX_VAL`) | `convertFieldValuesToAttributes()` L1157-1161 | `SWSS_LOG_ERROR` → `return false` → `task_invalid_entry` → erase | なし |
| EXP 値が非整数 / 空文字列 | `convertFieldValuesToAttributes()` L1181-1185 (`stoi()` throw) | catch → `return false` → `task_invalid_entry` → erase | なし |
| FC 値が負数 or `>= max_num_fcs` | `convertFieldValuesToAttributes()` L1166-1170 | `SWSS_LOG_ERROR` → `return false` → `task_invalid_entry` → erase | なし |
| FC 未サポートスイッチ (`max_num_fcs=0`) | `NhgMapOrch::getMaxNumFcs()` L308-321 | 全 FC 値が `>= 0 (max_num_fcs=0)` で reject → `task_invalid_entry` | なし |
| SAI `create_qos_map` 失敗 | `addQosItem()` L1206-1210 | `SWSS_LOG_ERROR("Failed to create exp_to_fc map")` → `SAI_NULL_OBJECT_ID` → `task_failed` → erase + return | なし（`doTask` で `return`） |
| SAI `set_qos_map_attribute` 失敗 (modify) | `modifyQosItem()` | `SWSS_LOG_ERROR` → `task_failed` → erase + return | なし |
| `m_pendingRemove == true` (pending DEL 中に SET) | `processWorkItem()` L136-140 | `SWSS_LOG_NOTICE` → `task_need_retry` → `it++` | PORT_QOS_MAP 参照解除後に自動解消 |

### DEL 時

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| エントリが存在しない (SAI oid が SAI_NULL_OBJECT_ID) | `processWorkItem()` L177-181 | `SWSS_LOG_ERROR("Object with name:%s not found")` → `task_invalid_entry` → erase | なし |
| `PORT_QOS_MAP` から参照中 | `isObjectBeingReferenced()` L182-187 | `m_pendingRemove=true` + `task_need_retry` → `it++` | PORT_QOS_MAP 参照解除まで無制限 retry |
| SAI `remove_qos_map` 失敗 | `removeQosItem()` | `SWSS_LOG_ERROR` → `task_failed` → erase + return | なし |

## task_failed 時の特殊挙動

`doTask()` では `task_failed` ケースで `return` しているため、同一 Consumer キューの後続エントリも全てブロックされる:

```cpp
case task_process_status::task_failed:
    SWSS_LOG_ERROR("Failed to process QOS task, drop it");
    it = consumer.m_toSync.erase(it);
    return;  // ← Consumer を抜ける（後続エントリも未処理）
```

これは SAI 障害時に QoS map 全体の処理が停止する設計。次の orchagent イベントループで再試行される。

## エラー通知先

- `SWSS_LOG_ERROR` / `SWSS_LOG_NOTICE` → syslog のみ
- `ERROR_TABLE` への書き込みなし
- STATE_DB への反映なし（EXP_TO_FC_MAP 自体は STATE_DB に書かない）
- CONFIG_DB からエントリは削除されない（`task_invalid_entry` でも erase はメモリ上のみ）

## Evidence

- `qosorch.cpp:2253-2300` — `QosOrch::doTask()` task_status 分岐
- `qosorch.cpp:124-201` — `QosMapHandler::processWorkItem()` pendingRemove / DEL ロジック
- `qosorch.cpp:1132-1213` — `ExpToFcMapHandler::convertFieldValuesToAttributes()` / `addQosItem()`
- `nhgmaporch.cpp:299-325` — `NhgMapOrch::getMaxNumFcs()` 静的キャッシュ
