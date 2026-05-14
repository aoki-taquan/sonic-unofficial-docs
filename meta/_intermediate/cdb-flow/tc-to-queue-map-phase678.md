# TC_TO_QUEUE_MAP — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`QosOrch` が `TC_TO_QUEUE_MAP` テーブルを読み、SAI の QoS map オブジェクトを作成する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI map type | テーブル名 `TC_TO_QUEUE_MAP` | `SAI_QOS_MAP_TYPE_TC_TO_QUEUE` として map 作成 | `qosorch.cpp` |
| SAI map エントリ | key の TC 値 (0-7) | 対応するキュー番号へのマッピングエントリを生成 | `qosorch.cpp` |

**CONFIG_DB 内フィールド間の自動付与なし**: key の TC 値とフィールドのキュー番号が 1:1 で SAI map エントリに変換される。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `QosOrch` は常時登録 | `TC_TO_QUEUE_MAP` テーブルは無条件購読 | `orchdaemon.cpp` |
| `PORT.tc_to_queue_map` から参照 | SAI port QoS map として bind される | `qosorch.cpp` / `portsorch.cpp` |
| 未参照の場合 | map オブジェクトは作成されるが port に適用されない | `qosorch.cpp` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `QosOrch` | map エントリ追加 | SAI `sai_qos_map_api->create_qos_map()` 呼び出し | `qosorch.cpp` |
| `QosOrch` | map エントリ更新 | SAI qos map attribute を set (既存 map OID に対して) | `qosorch.cpp` |
| `QosOrch` | del_handler | SAI qos map 削除、port 参照を解除してから削除 | `qosorch.cpp` |
| `QosOrch` | TC 値が範囲外 (0-7 以外) | ログエラー + スキップ | `qosorch.cpp` |

> **スキャン証跡**: `TC_TO_QUEUE_MAP` は Traffic Class からキュー番号へのマッピングテーブル。QosOrch が SAI QoS map として管理。CONFIG_DB 内フィールド間の自動付与はなし。
