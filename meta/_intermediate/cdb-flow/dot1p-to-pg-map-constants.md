# dot1p-to-pg-map: Phase E ハードコード定数 調査メモ

## 対象ページ

`docs/reference/config-db/dot1p-to-pg-map.md`

## 調査ソース

- `sonic-swss/orchagent/qosorch.h` — フィールド名定数
- `sonic-swss/orchagent/qosorch.cpp` — SAI 定数使用箇所
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2`

## 検出定数

### qosorch.h フィールド名

- L13: `dot1p_to_tc_field_name = "dot1p_to_tc_map"`
- L18: `tc_to_pg_map_field_name = "tc_to_pg_map"`

### qosorch.cpp SAI 定数

- L406: `SAI_QOS_MAP_TYPE_DOT1P_TO_TC` (addQosItem for DOT1P_TO_TC)
- L913: `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP`
- L63: `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` (qos_to_attr_map)
- L67: `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP`

### YANG 値域制約

- sonic-dot1p-tc-map.yang: `dot1p` key pattern `[0-7]?`; `name` pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`
- sonic-types.yang.j2: `tc_type` uint8 range 0..15
- SAI_QOS_MAP_TYPE_DOT1P_TO_PRIORITY_GROUP は SAI に存在しない → DOT1P_TO_PG_MAP が非実在の根拠の一つ
