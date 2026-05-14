# QUEUE — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`QosOrch::doQueueTask()` が `QUEUE` テーブルを処理する。

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI queue type | `scheduler.type==STRICT` | `SAI_QUEUE_TYPE_ALL` (strict priority) | `qosorch.cpp` |
| SAI queue type | `scheduler.type==DWRR` | `SAI_QUEUE_TYPE_ALL` (weighted round-robin) | `qosorch.cpp` |
| `wred_profile` OID | `QUEUE.wred_profile` フィールド参照 | `WRED_PROFILE` テーブルから OID 取得して SAI に設定 | `qosorch.cpp` |
| `scheduler` OID | `QUEUE.scheduler` フィールド参照 | `SCHEDULER` テーブルから OID 取得して SAI に設定 | `qosorch.cpp` |
| `dscp_to_tc_map` OID | `QUEUE.dscp_to_tc_map` フィールド参照 | 対応マップテーブルから OID 取得 | `qosorch.cpp` |

**BUFFER_PG への間接依存**: `QUEUE` 更新後に `BUFFER_QUEUE` が参照するポート・キュー番号を解決する。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `QosOrch` は常時登録 | `QUEUE` テーブルは無条件購読 | `orchdaemon.cpp` |
| `SCHEDULER` / `WRED_PROFILE` が未作成の場合 | 対応 OID 未解決 → 設定がペンディング状態 | `qosorch.cpp` |
| port 未初期化 | `Port` オブジェクト未取得 → エラーログ + スキップ | `qosorch.cpp` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `QosOrch` | `wred_profile` フィールドあり | `WRED_PROFILE` OID 参照 → `SAI_QUEUE_ATTR_WRED_PROFILE_ID` 設定 | `qosorch.cpp` |
| `QosOrch` | `scheduler` フィールドあり | `SCHEDULER` OID 参照 → `SAI_QUEUE_ATTR_SCHEDULER_PROFILE_ID` 設定 | `qosorch.cpp` |
| `QosOrch` | `dscp_to_tc_map` フィールドあり | マップ OID 参照 → `SAI_QUEUE_ATTR_QOS_MAP` 設定 | `qosorch.cpp` |
| `QosOrch` | port のキュー番号が範囲外 | ERROR ログ + スキップ | `qosorch.cpp` |
| `QosOrch` | del_handler: `wred_profile` あり | SAI attribute を NULL OID に設定して解除 | `qosorch.cpp` |

> **スキャン証跡**: QUEUE は SAI キューオブジェクトの属性 (scheduler, wred_profile) を束ねる。Phase 6 派生はフィールドから OID 解決への変換。自動付与はなし。
