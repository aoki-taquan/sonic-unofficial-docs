# TC_TO_DSCP_MAP — Phase B 書込み順依存 中間ファイル

生成日: 2026-05-16 (Task F Phase B)

## 調査元

- `sonic-swss/orchagent/qosorch.cpp`

## PORT_QOS_MAP 参照順序（SET 方向）

`QosOrch::handlePortQosMapTable()` (qosorch.cpp:2124) は各フィールドを `resolveFieldRefValue` で解決する:

```cpp
ref_resolve_status status = resolveFieldRefValue(m_qos_maps, map_type_name,
    qos_to_ref_table_map.at(map_type_name), tuple, id, object_name);
if (status != ref_resolve_status::success)
{
    SWSS_LOG_INFO("Port QoS map %s is not yet created", map_name.c_str());
    return task_process_status::task_need_retry;  // qosorch.cpp:2129
}
```

`qos_to_ref_table_map` に `tc_to_dscp_field_name → CFG_TC_TO_DSCP_MAP_TABLE_NAME`
が登録されている (qosorch.cpp:105)。

つまり `PORT_QOS_MAP` に `tc_to_dscp_map` フィールドが含まれる場合、
**TC_TO_DSCP_MAP エントリが先に存在しなければ task_need_retry** となる。

## TUNNEL 参照順序（SET 方向）

`QosOrch::resolveTunnelQosMap()` (qosorch.cpp:2318) は `encap_tc_to_dscp_field_name` を
`qos_to_ref_table_map` 経由で `CFG_TC_TO_DSCP_MAP_TABLE_NAME` へ解決する (qosorch.cpp:115)。

解決失敗時は `SAI_NULL_OBJECT_ID` を返し、tunnel handler が `task_need_retry` を返す。
→ **TUNNEL.encap_tc_to_dscp_map を設定する前に TC_TO_DSCP_MAP が存在しなければならない**。

## doTask() 実行順序

`QosOrch::doTask()` (qosorch.cpp:2231) は次の順で drain する:

1. `PORT_QOS_MAP` と `QUEUE` 以外のすべての consumer（map 系テーブル）を先に drain
2. その後 `PORT_QOS_MAP` → `QUEUE` の順で drain

これにより TC_TO_DSCP_MAP の処理が PORT_QOS_MAP より必ず先行する。
（TUNNEL は別 orch。同一サイクルではないが、TUNNEL.encap_tc_to_dscp_map 設定時に map が存在すれば即時解決される。）

## DEL 時の順序制約

DEL ハンドラ (qosorch.cpp:181-189) は `isObjectBeingReferenced()` でチェックし、
PORT_QOS_MAP または TUNNEL から参照中の場合は `m_pendingRemove = true` をセットして `task_need_retry` を返す。
参照が解除（PORT_QOS_MAP DEL または TUNNEL から参照解除）されるまで SAI remove は保留される。

## 結論

| 方向 | 先行必須 | 後行 | 自動リトライ |
|------|---------|------|------------|
| SET | TC_TO_DSCP_MAP 作成 | PORT_QOS_MAP.tc_to_dscp_map 設定 | task_need_retry |
| SET | TC_TO_DSCP_MAP 作成 | TUNNEL.encap_tc_to_dscp_map 設定 | task_need_retry |
| DEL | PORT_QOS_MAP.tc_to_dscp_map 解除 | TC_TO_DSCP_MAP 削除 | task_need_retry（pendingRemove） |
| DEL | TUNNEL.encap_tc_to_dscp_map 解除 | TC_TO_DSCP_MAP 削除 | task_need_retry（pendingRemove） |
