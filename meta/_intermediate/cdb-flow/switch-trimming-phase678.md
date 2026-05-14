# SWITCH_TRIMMING — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`SwitchOrch` が `SWITCH_TRIMMING` テーブルを読み、SAI のパケットトリミング設定を行う。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI trim size 属性 | `size` フィールド | `SAI_SWITCH_ATTR_PACKET_TRIM_SIZE` に設定 | `switchorch.cpp` |
| SAI trim DSCP モード | `dscp_value` フィールドあり | `SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_RESOLUTION_MODE=SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_ASSIGN` | `switchorch.cpp` |
| SAI trim DSCP モード | `dscp_value` フィールドなし | `SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_RESOLUTION_MODE=SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_PRESERVE` | `switchorch.cpp` |
| SAI trim queue モード | `queue` フィールドあり | `SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_RESOLUTION_MODE=SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_STATIC` | `switchorch.cpp` |

**自動派生**: `dscp_value` と `queue` フィールドの有無が SAI resolution mode を自動決定する。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `SwitchOrch` は常時登録 | `SWITCH_TRIMMING` テーブルは無条件購読 | `orchdaemon.cpp` |
| SAI trim capability 未サポート | SAI 属性設定がエラー → ログのみ | `switchorch.cpp` |
| `SWITCH_TRIMMING|GLOBAL` エントリのみ有効 | シングルトン制約 | `sonic-switch-trimming.yang` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `SwitchOrch` | `size` フィールドあり | `SAI_SWITCH_ATTR_PACKET_TRIM_SIZE` 設定 | `switchorch.cpp` |
| `SwitchOrch` | `dscp_value` フィールドあり | ASSIGN モード + 指定 DSCP 値を SAI に設定 | `switchorch.cpp` |
| `SwitchOrch` | `dscp_value` フィールドなし | PRESERVE モード (元パケットの DSCP を保持) | `switchorch.cpp` |
| `SwitchOrch` | `queue` フィールドあり | STATIC モード + 指定キュー番号を SAI に設定 | `switchorch.cpp` |
| `SwitchOrch` | del_handler | SAI trim 設定を解除 | `switchorch.cpp` |

> **スキャン証跡**: `SWITCH_TRIMMING` はパケットトリミング機能の設定。`dscp_value` / `queue` の有無が SAI resolution mode の自動決定分岐を引き起こす点が Phase 6/7/8 の主要ポイント。
