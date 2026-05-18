# TC_TO_PRIORITY_GROUP_MAP — 暗黙参照テーブル調査 (Phase C)

## 調査対象ファイル

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## 参照関係まとめ

TC_TO_PRIORITY_GROUP_MAP は「被参照側」テーブル。他テーブルが本テーブルのマップ名を
leafref として持つ。本テーブル自体が他テーブルを参照する leafref は YANG 上存在しない。

### 参照元 1: PORT_QOS_MAP

- フィールド: `PORT_QOS_MAP|<port>.tc_to_pg_map`
- 参照方向: PORT_QOS_MAP → TC_TO_PRIORITY_GROUP_MAP（マップ名解決）
- 解決関数: `resolveFieldRefValue(m_qos_maps, tc_to_pg_map_field_name, CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, ...)`
  (qosorch.cpp:2118-2134)
- 未解決時: `task_need_retry`（マップ SAI 登録完了まで待機）
- 参照カウント: `setObjectReference(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, key, ...)` で記録
  → `isObjectBeingReferenced()` が TC_TO_PRIORITY_GROUP_MAP DEL を阻止

### 参照元 2: TUNNEL_DECAP_TABLE (APPL_DB)

- フィールド: `TUNNEL_DECAP_TABLE|<name>.decap_tc_to_pg_map`
- 参照方向: TunnelDecapOrch → TC_TO_PRIORITY_GROUP_MAP（OID 解決）
- 解決関数: `gQosOrch->resolveTunnelQosMap(table_name, key, decap_tc_to_pg_field_name, t)`
  (tunneldecaporch.cpp:232)
- 未解決時: "QoS map decap_tc_to_pg_map is not ready yet" LOG_NOTICE → `task_need_retry`
  (tunneldecaporch.cpp:235-237)
- 参照カウント: `qos_to_ref_table_map[decap_tc_to_pg_field_name] = CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME`
  (qosorch.cpp:114) により同一参照追跡マップで管理

## DEL ブロック証跡

```
qosorch.cpp:181-186:
  if (gQosOrch->isObjectBeingReferenced(QosOrch::getTypeMap(), qos_map_type_name, qos_object_name))
  {
      ...
      (*(QosOrch::getTypeMap()[qos_map_type_name]))[qos_object_name].m_pendingRemove = true;
      return task_process_status::task_need_retry;
  }
```
