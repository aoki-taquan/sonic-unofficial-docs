# PORT_QOS_MAP 暗黙参照 (Phase C)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 抽出した暗黙参照

`QosOrch` は `PORT_QOS_MAP` エントリの各フィールドを解決する際に、以下のテーブルを **暗黙的に参照** する（YANG leafref 宣言とは別に、実装側で `m_qos_maps` 参照カウントマップへ登録する形で依存が発生）。

| PORT_QOS_MAP フィールド | 参照先テーブル | qosorch.cpp 行 |
|---|---|---|
| `dscp_to_tc_map` | `DSCP_TO_TC_MAP` | 61, 81, 100, 113 |
| `tc_to_queue_map` | `TC_TO_QUEUE_MAP` | 64, 84, 103, 116 |
| `tc_to_pg_map` | `TC_TO_PRIORITY_GROUP_MAP` | 67, 89, 106, 114 |
| `pfc_to_queue_map` | `PFC_PRIORITY_TO_QUEUE_MAP` | 69, 91, 108 |
| `scheduler` | `SCHEDULER` | 70, 85, 109 |
| `wred_profile` | `WRED_PROFILE` | 86, 110 |

### 補足: MAP_PFC_PRIORITY_TO_PRIORITY_GROUP

`MAP_PFC_PRIORITY_TO_PRIORITY_GROUP` (= `pfc_to_pg_map` フィールド) は `m_qos_maps` の key として独立登録されていないが、`TC_TO_PRIORITY_GROUP_MAP` を通じて間接的に依存する。YANG では `pfc_to_pg_map` フィールドが `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` への leafref として宣言されており、`QosOrch` はこれを `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` にマップしている（行 106, 114）。

## 暗黙参照の仕組み

`QosOrch` コンストラクタ（`qosorch.cpp:81-116`）で `m_qos_maps` を初期化する際、各 QoS テーブルに対応する `object_reference_map` を登録する。`PortQosMapHandler` が `SET` を受け取ると、`setObjectReference()` / `doesObjectExist()` を通じてこれらのテーブルの OID を解決し、参照カウントを管理する。

参照先テーブルが存在しない（OID 未解決）場合は `task_need_retry` を返してリトライキューへ積む（`qosorch.cpp:2077-2133`）。DEL 時は `removeMeFromObjsReferencedByMe()` で逆参照を解除（`qosorch.cpp:2165-2170`）。

## ソース証跡

```
sonic-swss/orchagent/qosorch.cpp:
  61: {dscp_to_tc_field_name, SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP}
  64: {tc_to_queue_field_name, SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP}
  67: {tc_to_pg_map_field_name, SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP}
  69: {pfc_to_queue_map_name, SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP}
  70: {scheduler_field_name, SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID}
  81: {CFG_DSCP_TO_TC_MAP_TABLE_NAME, make_shared<object_reference_map>()}
  84: {CFG_TC_TO_QUEUE_MAP_TABLE_NAME, make_shared<object_reference_map>()}
  85: {CFG_SCHEDULER_TABLE_NAME, make_shared<object_reference_map>()}
  86: {CFG_WRED_PROFILE_TABLE_NAME, make_shared<object_reference_map>()}
  89: {CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, make_shared<object_reference_map>()}
  91: {CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME, make_shared<object_reference_map>()}
 100: {dscp_to_tc_field_name, CFG_DSCP_TO_TC_MAP_TABLE_NAME}
 103: {tc_to_queue_field_name, CFG_TC_TO_QUEUE_MAP_TABLE_NAME}
 106: {tc_to_pg_map_field_name, CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME}
 108: {pfc_to_queue_map_name, CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME}
 109: {scheduler_field_name, CFG_SCHEDULER_TABLE_NAME}
 110: {wred_profile_field_name, CFG_WRED_PROFILE_TABLE_NAME}
```
