# EXP_TO_FC_MAP — Phase F 副作用調査

## 調査対象

- `orchagent/qosorch.cpp` (sonic-swss@4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/cbf/nhgmaporch.cpp`

## MAP SET/DEL の直接副作用

### SET (新規) — create_qos_map

`ExpToFcMapHandler::addQosItem()` が `sai_qos_map_api->create_qos_map()` を呼ぶ。
SAI QoS map オブジェクト (`SAI_QOS_MAP_TYPE_MPLS_EXP_TO_FORWARDING_CLASS`) が生成され、
OID が `m_qos_maps[CFG_EXP_TO_FC_MAP_TABLE_NAME][<name>]` にキャッシュされる。

Evidence: `qosorch.cpp:1189-1213`

### SET (既存) — set_qos_map_attribute

エントリが既に SAI に登録済みの場合 (`sai_object != SAI_NULL_OBJECT_ID`)、
`QosMapHandler::modifyQosItem()` が `sai_qos_map_api->set_qos_map_attribute(sai_object, ...)` を呼ぶ。
同一 SAI oid を**in-place で更新**するため、この SAI oid を参照している全ポート
(`SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP`) に変更が即時反映される。
PORT_QOS_MAP を再設定する必要はない。

Evidence: `qosorch.cpp:151-155`, `qosorch.cpp:204-211`

### DEL (参照なし) — remove_qos_map

参照がない場合 `QosMapHandler::removeQosItem()` が `sai_qos_map_api->remove_qos_map()` を呼ぶ。
`m_qos_maps` のエントリも erase される。

Evidence: `qosorch.cpp:188-198`

### DEL (参照あり) — pendingRemove

PORT_QOS_MAP で `exp_to_fc_map` を参照中の場合 `m_pendingRemove = true` がセットされ、
`task_need_retry` を返す。SAI 操作は発生しない。
後続の同名 SET も `m_pendingRemove` が解消されるまで即 `task_need_retry` で defer される。

Evidence: `qosorch.cpp:181-186`, `qosorch.cpp:136-139`

## STATE_DB / APPL_DB への書き込み

なし。`QosOrch` は `EXP_TO_FC_MAP` の処理で STATE_DB / APPL_DB へ書き込まない。CONFIG_DB → SAI 直結。

## PORT_QOS_MAP 経由の間接副作用

MAP OID が確定したことで `PORT_QOS_MAP.exp_to_fc_map` の参照解決が完了し、
`handlePortQosMapTable` が `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP` を
各ポートに適用する。MAP 未作成の間は `task_need_retry` で保留、MAP 作成完了後の
`doTask()` サイクルで自動再処理。

Evidence: `qosorch.cpp:2124-2133`, `qosorch.cpp:2185-2204`

## CBF / NHG への副作用

`EXP_TO_FC_MAP` の変更は `NhgMapOrch` / CBF テーブルへの直接副作用はない。
`NhgMapOrch::getMaxNumFcs()` は FC 値の検証のみに使用（マップ内容の変更を契機として
NHG が更新されるパスはない）。
