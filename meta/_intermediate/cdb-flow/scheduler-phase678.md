# SCHEDULER — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`QosOrch` が `SCHEDULER` テーブルを読み、SAI の scheduler profile を作成する。

| 派生先フィールド | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` | `SCHEDULER.type==STRICT` | `SAI_SCHEDULING_TYPE_STRICT` | `qosorch.cpp` |
| SAI `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` | `SCHEDULER.type==DWRR` | `SAI_SCHEDULING_TYPE_DWRR` | `qosorch.cpp` |
| SAI `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` | `SCHEDULER.type==WRR` | `SAI_SCHEDULING_TYPE_WRR` | `qosorch.cpp` |
| SAI weight 属性 | `SCHEDULER.weight` あり + `type==DWRR` or `WRR` | `SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT` に設定 | `qosorch.cpp` |
| SAI meter 属性 | `SCHEDULER.meter_type==bytes` | `SAI_SCHEDULER_ATTR_METER_TYPE=SAI_METER_TYPE_BYTES` | `qosorch.cpp` |
| SAI meter 属性 | `SCHEDULER.meter_type==packets` | `SAI_SCHEDULER_ATTR_METER_TYPE=SAI_METER_TYPE_PACKETS` | `qosorch.cpp` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `QosOrch` は常時登録 | `SCHEDULER` テーブルは無条件購読 | `orchdaemon.cpp` |
| `SCHEDULER` が `QUEUE.scheduler` から参照されている場合のみ | SAI キューオブジェクトに scheduler profile を bind | `qosorch.cpp` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `QosOrch` | `type==STRICT` | `SAI_SCHEDULING_TYPE_STRICT` + weight 属性なし | `qosorch.cpp` |
| `QosOrch` | `type==DWRR` | `SAI_SCHEDULING_TYPE_DWRR` + weight 属性設定 | `qosorch.cpp` |
| `QosOrch` | `type==WRR` | `SAI_SCHEDULING_TYPE_WRR` + weight 属性設定 | `qosorch.cpp` |
| `QosOrch` | `meter_type==bytes` | `SAI_METER_TYPE_BYTES` | `qosorch.cpp` |
| `QosOrch` | `meter_type==packets` | `SAI_METER_TYPE_PACKETS` | `qosorch.cpp` |
| `QosOrch` | `cir` / `cbs` / `pir` / `pbs` フィールドあり | SAI rate/burst 属性を設定 | `qosorch.cpp` |
| `QosOrch` | del_handler | SAI scheduler profile を削除、QUEUE 参照を解除 | `qosorch.cpp` |

> **スキャン証跡**: `SCHEDULER` は SAI scheduler profile の属性マッピング。type フィールドで SAI enum を決定する主要分岐あり。CONFIG_DB 内フィールド間の自動付与はなし。
