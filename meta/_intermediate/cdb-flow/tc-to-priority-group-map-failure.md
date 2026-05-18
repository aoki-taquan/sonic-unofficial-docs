# TC_TO_PRIORITY_GROUP_MAP — Phase D 失敗挙動調査

## 調査対象

- `orchagent/qosorch.cpp` (sonic-swss): `TcToPgHandler::convertFieldValuesToAttributes()` (L884-902), `TcToPgHandler::addQosItem()` (L904-928), `QosMapHandler::processWorkItem()` (L124-201), `QosOrch::doTask(Consumer&)` (L2253-2300)
- `orchagent/tunneldecaporch.cpp` (sonic-swss): `doTask()` (L230-243)

## 起動ガード

`QosOrch::doTask()` 冒頭で `gPortsOrch->allPortsReady()` を確認する (`qosorch.cpp:2253-2258`)。ポート構成完了前は即時 `return` し `Consumer::m_toSync` のエントリが滞留したまま暗黙 retry される（ログなし・CONFIG_DB 変更なし）。

## SET 時の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| `allPortsReady() == false` | `doTask()` L2258-2261 | 早期 return、`m_toSync` 滞留 | ポート準備完了まで暗黙 retry |
| `tc` または `pg` が非数値・空文字列 | `convertFieldValuesToAttributes()` L894-895 `stoi()` | **例外が try/catch されない** → 呼び出しスタックを伝播（YANG バリデーションが通過した場合のみ到達） | なし（orchagent の上位で捕捉されるかはフレームワーク依存） |
| SAI `create_qos_map` 失敗（新規） | `addQosItem()` L921-924 | `SWSS_LOG_ERROR("Failed to create tc_to_pg map")` → `SAI_NULL_OBJECT_ID` 返却 → `task_failed` | なし（後続エントリもブロック） |
| SAI `set_qos_map_attribute` 失敗（既存上書き） | `modifyQosItem()` L207-210 | `SWSS_LOG_ERROR("Failed to modify map")` → `task_failed` | なし |
| `m_pendingRemove == true` (DEL pending 中に SET) | `processWorkItem()` L136-140 | `SWSS_LOG_NOTICE("Entry ... is pending remove")` → `task_need_retry` | PORT_QOS_MAP / TUNNEL 参照解除後に自動解消 |

**注意**: `TcToPgHandler::convertFieldValuesToAttributes()` は `stoi()` を try/catch なしで呼んでいる（`qosorch.cpp:894-895`）。`ExpToFcMapHandler` が try/catch で `task_invalid_entry` を返すのとは異なる実装。YANG バリデーションで `tc_type` (uint8 0..15) および `[0-7]?` パターンが強制されるため、通常は非数値が到達しないが、直接 DB 書き込みをした場合の挙動は未定義（例外伝播）。

## DEL 時の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| エントリ未登録（SAI oid なし） | `processWorkItem()` L177-181 | `SWSS_LOG_ERROR("Object with name:%s not found")` → `task_invalid_entry` → erase | なし |
| PORT_QOS_MAP または TUNNEL_DECAP_TABLE から参照中 | `isObjectBeingReferenced()` L182-187 | `m_pendingRemove=true` + `task_need_retry` → `it++` | 参照解除まで無制限 retry |
| SAI `remove_qos_map` 失敗 | `removeQosItem()` L218-222 | `SWSS_LOG_ERROR("Failed to remove map")` → `task_failed` → erase + `return` | なし |

## `task_failed` 時の特殊挙動

`doTask()` は `task_failed` で該当エントリを erase した後 `return` するため、同一 Consumer キュー内の**後続エントリも当該イテレーションでは未処理**となる（`qosorch.cpp:2284-2288`）。次の orchagent イベントループで再試行される。

## エラー通知先

- `SWSS_LOG_ERROR` / `SWSS_LOG_NOTICE` → syslog のみ
- `ERROR_TABLE` への書き込みなし
- STATE_DB への反映なし（`TC_TO_PRIORITY_GROUP_MAP` は STATE_DB を持たない）
- CONFIG_DB のエントリは失敗後も残存（`task_invalid_entry` の erase はメモリ上の `m_toSync` のみ）
