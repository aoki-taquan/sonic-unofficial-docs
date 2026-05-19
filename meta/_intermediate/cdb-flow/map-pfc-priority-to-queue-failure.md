# MAP_PFC_PRIORITY_TO_QUEUE — 失敗挙動調査 (Phase D)

調査日: 2026-05-19
調査対象:
- `sonic-swss/orchagent/qosorch.cpp` (master)
- `sonic-swss/orchagent/qosorch.h` (master)

## 起動ガード

`QosOrch::doTask(Consumer&)` (`qosorch.cpp:2254-2261`) の冒頭で
`gPortsOrch->allPortsReady()` を確認する。false の場合は即時 `return`。
`Consumer::m_toSync` のエントリが滞留したまま暗黙 retry される（ログなし・CONFIG_DB 変更なし）。

## SET 時の失敗パターン

### allPortsReady() == false (L2254-2261)

全ポート初期化が完了するまで doTask が早期 return し m_toSync が滞留する。
ポート準備完了後の次回イベントで再処理される。

### m_pendingRemove == true かつ SET (L136-140)

同名エントリが DEL pending 中に SET が来た場合:
`SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry", ...)` を出力して `task_need_retry` を返す。
PORT_QOS_MAP からの参照が解除されると DEL が完了し、その後 SET が処理される。

### convertFieldValuesToAttributes() 失敗

`PfcToQueueHandler::convertFieldValuesToAttributes()` (`qosorch.cpp:991-1009`) は `stoi()` を
try/catch なしで呼ぶ。`pfc_priority` または `qindex` フィールドに非数値・空文字が来ると
`std::invalid_argument` が伝播する。YANG pattern `[0-7]?` が正規 API では保護するが、
`sonic-db-cli` 等でバイパスした場合は例外が呼び出し元まで伝播する。

convertFieldValuesToAttributes が `false` を返した場合は `task_invalid_entry` でエントリ破棄。

### SAI create_qos_map 失敗（新規 SET）(L1029-1033)

`addQosItem()` 内で `sai_qos_map_api->create_qos_map()` が
`SAI_STATUS_SUCCESS` 以外を返した場合:
- `SWSS_LOG_ERROR("Failed to create pfc_priority_to_queue map. status:%d", sai_status)`
- `addQosItem()` が `SAI_NULL_OBJECT_ID` を返す
- `processWorkItem()` は `SWSS_LOG_ERROR("Failed to create [%s:%s]", ...)` を出力して `task_failed`
- `doTask()` は `task_failed` で erase + `return`（後続エントリもブロック）

### SAI set_qos_map_attribute 失敗（既存 SET/上書き）(L207-210)

`modifyQosItem()` が `sai_qos_map_api->set_qos_map_attribute()` で失敗した場合:
- `SWSS_LOG_ERROR("Failed to modify map. status:%d", sai_status)`
- `modifyQosItem()` が `false` を返す
- `processWorkItem()` は `SWSS_LOG_ERROR("Failed to set [%s:%s]", ...)` を出力して `task_failed`
- retry なし

## DEL 時の失敗パターン

### エントリ未登録（SAI OID = NULL）(L177-181)

対象エントリが `m_qos_maps` に存在しない場合:
- `SWSS_LOG_ERROR("Object with name:%s not found.", qos_object_name.c_str())`
- `task_invalid_entry` でエントリを erase（m_toSync から削除）
- retry なし

### PORT_QOS_MAP から参照中 (L182-187)

`isObjectBeingReferenced()` が true を返した場合:
- `SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)", ...)`
- `m_pendingRemove = true` をセット
- `task_need_retry` を返す
- PORT_QOS_MAP から `pfc_to_queue_map` 参照が解除されるまで無制限 retry

### SAI remove_qos_map 失敗 (L218-222)

`removeQosItem()` が `sai_qos_map_api->remove_qos_map()` で失敗した場合:
- `SWSS_LOG_ERROR("Failed to remove QoS map. db name:%s sai object:%" PRIx64, ...)`
- `task_failed` → erase + `return`
- retry なし

## task_failed 時の特殊挙動

`doTask(Consumer&)` (`qosorch.cpp:2280-2288`) は `task_failed` で該当エントリを erase した後
`return` するため、同一 Consumer キュー内の後続エントリも当該イテレーションでは未処理となる。
次の orchagent イベントループで残エントリが再処理される。

## エラー通知先

- `SWSS_LOG_ERROR` / `SWSS_LOG_NOTICE` → syslog のみ
- `ERROR_TABLE` への書き込みなし
- STATE_DB への反映なし（`MAP_PFC_PRIORITY_TO_QUEUE` は STATE_DB テーブルを持たない）
- CONFIG_DB のエントリは失敗後も残存（`task_invalid_entry` の erase はメモリ上の `m_toSync` のみ）
