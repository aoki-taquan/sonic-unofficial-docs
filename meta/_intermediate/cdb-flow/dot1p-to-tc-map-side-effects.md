# dot1p-to-tc-map side-effects 調査証跡

## 対象テーブル

`DOT1P_TO_TC_MAP`

## 調査ソース

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/qosorch.h`

## 副次 DB 書き込み分析

### CONFIG_DB → orchagent 直結

`DOT1P_TO_TC_MAP` は `QosOrch` が CONFIG_DB を直接購読する。cfgmgr ステージは存在しない。
APPL_DB 中継なし。STATE_DB / APPL_STATE_DB への書き込みなし。

### SET 時の副次書き込み

1. **新規マップ作成**: `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_DOT1P_TO_TC, ...)` → ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` に新規エントリ生成 (`qosorch.cpp:399-416`)
2. **既存マップ更新**: `sai_qos_map_api->set_qos_map_attribute(oid, SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST, ...)` → ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` エントリ更新 (`qosorch.cpp:207`)

### PORT_QOS_MAP 経由のポートバインド時

`PORT_QOS_MAP|<port>` に `dot1p_to_tc_map` フィールドを書いた際:
- `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP, oid)` → ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_PORT` 更新 (`qosorch.cpp:2086,2193`)

### スイッチレベル適用: なし

`DSCP_TO_TC_MAP` とは異なり、`DOT1P_TO_TC_MAP` は `PORT_QOS_MAP|global` 経由のスイッチレベル適用が未実装。
`handleGlobalQosMap()` は `dot1p_to_tc_field_name` を受け取ると `"Qos map type %s is not supported at global level"` (WARN) でスキップ (`qosorch.cpp:2012`)。

### DEL 時の副次書き込み

1. **非参照時**: `sai_qos_map_api->remove_qos_map(sai_object)` → ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` エントリ削除 (`qosorch.cpp:188-191`)
2. **参照中**: `pending_remove=true` + `task_need_retry` — ASIC_DB 変更なし (`qosorch.cpp:181-186`)

## 結論

副次書き込みは ASIC_DB のみ。APPL_DB / STATE_DB / APPL_STATE_DB / COUNTERS_DB への書き込みなし。
スイッチレベルバインドなし（ポートバインドのみ）。
