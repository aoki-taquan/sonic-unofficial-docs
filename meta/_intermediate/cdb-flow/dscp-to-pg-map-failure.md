# dscp-to-pg-map — Phase D 失敗挙動調査 (failure)

date: 2026-05-18
target: docs/reference/config-db/dscp-to-pg-map.md

## 調査対象

`DSCP_TO_PG_MAP` テーブルは存在しないため、DSCP→PG 機能を実現する 2 段構成テーブル
（`DSCP_TO_TC_MAP`・`TC_TO_PRIORITY_GROUP_MAP`）の失敗挙動を記述する。

## 参照ソース

- `sonic-swss/orchagent/qosorch.cpp:124-201` — `QosMapHandler::processWorkItem()`（共通マップハンドラ）
- `sonic-swss/orchagent/qosorch.cpp:235-254` — `DscpToTcMapHandler::convertFieldValuesToAttributes()`
- `sonic-swss/orchagent/qosorch.cpp:256-282` — `DscpToTcMapHandler::addQosItem()`
- `sonic-swss/orchagent/qosorch.cpp:284-296` — `DscpToTcMapHandler::removeQosItem()`
- `sonic-swss/orchagent/qosorch.cpp:884-934` — `TcToPgHandler::convertFieldValuesToAttributes()` / `addQosItem()`
- `sonic-swss/orchagent/qosorch.cpp:2046-2170` — `QosOrch::handlePortQosMapTable()`
- `sonic-swss/orchagent/qosorch.cpp:2253-2300` — `QosOrch::doTask()`

## 主な発見

### 起動ガード

`QosOrch::doTask()` (L2258-2261) で `gPortsOrch->allPortsReady()` を確認。false の間は全 QosOrch
処理が early return し、`m_toSync` に滞留（暗黙 retry）。

### DscpToTcMapHandler — 例外処理なし

`convertFieldValuesToAttributes()` L245-246 で dscp 値（key）と tc 値（value）の両方に
`stoi()` を例外処理なしで呼ぶ。非整数文字列が CONFIG_DB に書かれると `std::invalid_argument`
が投げられ、`processWorkItem()` で未捕捉のまま orchagent がクラッシュする可能性がある。
（EXP_TO_FC_MAP ハンドラは L1181-1185 で try/catch あり — 対称的な設計ではない）

### TcToPgHandler — 例外処理なし

`convertFieldValuesToAttributes()` L894-895 で tc 値（key）と pg 値（value）の両方に
`stoi()` を例外処理なしで呼ぶ。同様に非整数文字列で `std::invalid_argument` が伝播。

### SAI 作成失敗

- `DscpToTcMapHandler::addQosItem()`: `create_qos_map` が失敗すると `SWSS_LOG_ERROR("Failed to create dscp_to_tc map. status:%d")` → `SAI_NULL_OBJECT_ID` → `processWorkItem()` で `task_failed`
- `TcToPgHandler::addQosItem()`: `create_qos_map` が失敗すると `SWSS_LOG_ERROR("Failed to create tc_to_pg map. status:%d")` → `SAI_NULL_OBJECT_ID` → `task_failed`

### SAI 削除失敗

- `DscpToTcMapHandler::removeQosItem()`: `remove_qos_map` 失敗 → `SWSS_LOG_ERROR("Failed to remove DSCP_TO_TC map, status:%d")` → `false` → `task_failed`
- `TcToPgHandler::removeQosItem()`: `remove_qos_map` 失敗 → `SWSS_LOG_ERROR("Failed to remove tc_to_pg map")` → `false` → `task_failed`

### PORT_QOS_MAP — 参照未解決

`handlePortQosMapTable()` (L2124-2129): `resolveFieldRefValue()` が `dscp_to_tc_map` または
`tc_to_pg_map` の参照先を解決できない場合 `task_need_retry` → 自動リトライ。

### エラー通知先

- `SWSS_LOG_ERROR` / `SWSS_LOG_NOTICE` → syslog のみ
- `ERROR_TABLE` 書き込みなし
- STATE_DB 書き込みなし
- CONFIG_DB エントリは残存（`m_toSync` からの erase のみ）
