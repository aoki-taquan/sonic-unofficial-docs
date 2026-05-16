# cross-refs: MAP_PFC_PRIORITY_TO_QUEUE

## 抽出元

ソース: `sonic-swss/orchagent/qosorch.cpp`

## PORT_QOS_MAP への暗黙参照

`MAP_PFC_PRIORITY_TO_QUEUE` テーブルで作成された SAI QoS map オブジェクトは、
`PORT_QOS_MAP` テーブルの `pfc_to_queue_map` フィールドから名前参照される。

### 参照連鎖

1. `qos_to_ref_table_map` (qosorch.cpp:108): `pfc_to_queue_map_name` → `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME`
2. `qos_to_attr_map` (qosorch.cpp:69): `pfc_to_queue_map_name` → `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP`
3. `handlePortQosMapTable` (qosorch.cpp:2046): PORT_QOS_MAP の各フィールドを解決する際、`pfc_to_queue_map` フィールドが存在すると `MAP_PFC_PRIORITY_TO_QUEUE` に登録済みの SAI object を `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` としてポートに適用する。
4. `m_qos_maps` (qosorch.cpp:87,91): `CFG_PORT_QOS_MAP_TABLE_NAME` と `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME` の両方が同一 `type_map` で管理され、object_reference_map による参照カウントが行われる。
5. DEL 保護 (qosorch.cpp:108,180-186): `isObjectBeingReferenced()` が true (= PORT_QOS_MAP から参照中) の間は `task_need_retry` を返し削除を保留する。

### SWITCH への暗黙参照

`MAP_PFC_PRIORITY_TO_QUEUE` は SWITCH レベルへ直接適用されない。
SWITCH レベル QoS map 適用は `DSCP_TO_TC_MAP` の `PORT_QOS_MAP|global` 経路のみ (qosorch.cpp:1956,1988-2032)。

## 要約

| 参照方向 | 参照元 | フィールド | SAI 属性 | evidence |
|---------|--------|-----------|---------|---------|
| MAP_PFC_PRIORITY_TO_QUEUE → PORT_QOS_MAP (被参照) | `PORT_QOS_MAP.pfc_to_queue_map` | `pfc_to_queue_map` (文字列: map 名) | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` | qosorch.cpp:69,108 |
| PORT_QOS_MAP → MAP_PFC_PRIORITY_TO_QUEUE (参照) | `handlePortQosMapTable` | DEL 時に参照解除、SET 時に object_id 解決 | — | qosorch.cpp:2046,2077,2108,2133 |
| SWITCH | なし | 直接 SWITCH 適用なし | — | qosorch.cpp:1956 (DSCP_TO_TC のみ) |
