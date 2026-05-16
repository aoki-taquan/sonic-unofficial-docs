# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP — Phase B 書込み順依存 中間ファイル

生成日: 2026-05-16 (Task F Phase B)

## 調査元

- `sonic-swss/orchagent/qosorch.cpp`

## PORT_QOS_MAP 参照順序（SET 方向）

`QosOrch::handlePortQosMapTable()` (qosorch.cpp:2118) には次のコメントと実装がある:

```cpp
/* Check all map instances are created before applying to ports */
ref_resolve_status status = resolveFieldRefValue(m_qos_maps, map_type_name,
    qos_to_ref_table_map.at(map_type_name), tuple, id, object_name);
if (status != ref_resolve_status::success)
{
    SWSS_LOG_INFO("Port QoS map %s is not yet created", map_name.c_str());
    return task_process_status::task_need_retry;  // qosorch.cpp:2129
}
```

`qos_to_ref_table_map` に `pfc_to_pg_map_name → CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME`
が登録されている (qosorch.cpp:107)。

つまり `PORT_QOS_MAP` に `pfc_to_pg_map` フィールドが含まれる場合、
**PFC_PRIORITY_TO_PRIORITY_GROUP_MAP エントリが先に存在しなければ task_need_retry** となる。

## doTask() 実行順序

`QosOrch::doTask()` (qosorch.cpp:2231) は次の順で drain する:

1. `PORT_QOS_MAP` と `QUEUE` 以外のすべての consumer（map 系テーブル）を先に drain
2. その後 `PORT_QOS_MAP` → `QUEUE` の順で drain

これにより PFC_PRIORITY_TO_PRIORITY_GROUP_MAP の処理が PORT_QOS_MAP より必ず先行する。

## SAI qos_map 制約

- `PfcPrioToPgHandler::addQosItem()` は `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP` 型で
  `sai_qos_map_api->create_qos_map()` を呼び出す (qosorch.cpp:973)。
- SAI object は `m_qos_maps` に登録され、PORT_QOS_MAP handler が `resolveFieldRefValue` で
  OID を lookup する。
- SAI 仕様上、port attribute `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` に
  有効な OID を渡す前に map object が存在している必要がある。

## DEL 時の順序制約

DEL 操作 (qosorch.cpp:181-189) では `isObjectBeingReferenced()` チェックを行い、
PORT_QOS_MAP から参照中の場合は `m_pendingRemove = true` をセットして `task_need_retry` を返す。
参照が解除（PORT_QOS_MAP DEL または NULL 設定）されるまで map の削除は保留される。

## 結論

| 方向 | 先行必須 | 後行 | 自動リトライ |
|------|---------|------|------------|
| SET | PFC_PRIORITY_TO_PRIORITY_GROUP_MAP 作成 | PORT_QOS_MAP.pfc_to_pg_map 設定 | task_need_retry |
| DEL | PORT_QOS_MAP.pfc_to_pg_map 解除 | PFC_PRIORITY_TO_PRIORITY_GROUP_MAP 削除 | task_need_retry（pendingRemove） |
