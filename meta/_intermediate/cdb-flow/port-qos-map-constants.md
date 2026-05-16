# PORT_QOS_MAP — ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/qosorch.h`, `sonic-swss/orchagent/qosorch.cpp`

## フィールド名定数 (qosorch.h:11–37)

| 定数名 | 値 (文字列) | 用途 |
|--------|------------|------|
| `dscp_to_tc_field_name` | `"dscp_to_tc_map"` | DSCP → TC map フィールド名 |
| `mpls_tc_to_tc_field_name` | `"mpls_tc_to_tc_map"` | MPLS EXP → TC map フィールド名 |
| `dot1p_to_tc_field_name` | `"dot1p_to_tc_map"` | 802.1p → TC map フィールド名 |
| `pfc_to_pg_map_name` | `"pfc_to_pg_map"` | PFC priority → PG map フィールド名 |
| `pfc_to_queue_map_name` | `"pfc_to_queue_map"` | PFC priority → queue map フィールド名 |
| `pfc_enable_name` | `"pfc_enable"` | PFC enable bitmap フィールド名 |
| `pfcwd_sw_enable_name` | `"pfcwd_sw_enable"` | PFC watchdog SW enable bitmap フィールド名 |
| `tc_to_pg_map_field_name` | `"tc_to_pg_map"` | TC → PG map フィールド名 |
| `tc_to_queue_field_name` | `"tc_to_queue_map"` | TC → queue map フィールド名 |
| `tc_to_dot1p_field_name` | `"tc_to_dot1p_map"` | TC → 802.1p map フィールド名 |
| `tc_to_dscp_field_name` | `"tc_to_dscp_map"` | TC → DSCP remarking map フィールド名 |
| `scheduler_field_name` | `"scheduler"` | scheduler profile フィールド名 |
| `dscp_to_fc_field_name` | `"dscp_to_fc_map"` | DSCP → forwarding class map フィールド名 |
| `exp_to_fc_field_name` | `"exp_to_fc_map"` | MPLS EXP → forwarding class map フィールド名 |
| `decap_dscp_to_tc_field_name` | `"decap_dscp_to_tc_map"` | トンネル decap DSCP → TC map フィールド名 |
| `decap_tc_to_pg_field_name` | `"decap_tc_to_pg_map"` | トンネル decap TC → PG map フィールド名 |
| `encap_tc_to_queue_field_name` | `"encap_tc_to_queue_map"` | トンネル encap TC → queue map フィールド名 |
| `encap_tc_to_dscp_field_name` | `"encap_tc_to_dscp_map"` | トンネル encap TC → DSCP map フィールド名 |

## global キー定数 (qosorch.cpp:122)

| 定数名 | 値 | 用途 |
|--------|---|------|
| `PORT_NAME_GLOBAL` | `"global"` | global デフォルトエントリのキー文字列。`sai_switch_api` 経由で Switch レベルに適用 |

## SAI ポート属性名マッピング (qosorch.cpp:60–73)

`qos_to_attr_map` — CONFIG_DB フィールド名 → SAI port attribute ID:

| フィールド名 | SAI 属性 |
|------------|---------|
| `dscp_to_tc_map` | `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` |
| `mpls_tc_to_tc_map` | `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_TC_MAP` |
| `dot1p_to_tc_map` | `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` |
| `tc_to_queue_map` | `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` |
| `tc_to_dot1p_map` | `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DOT1P_MAP` |
| `tc_to_dscp_map` | `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` |
| `tc_to_pg_map` | `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` |
| `pfc_to_pg_map` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` |
| `pfc_to_queue_map` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` |
| `scheduler` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` |
| `dscp_to_fc_map` | `SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP` |
| `exp_to_fc_map` | `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP` |

global キー (`"global"`) 専用: `dscp_to_tc_map` のみ `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` 経由で Switch レベルに適用 (qosorch.cpp:2030)。

## スカラー定数 (qosorch.cpp:119–122)

| 定数名 | 値 | 用途 |
|--------|---|------|
| `DSCP_MAX_VAL` | `63` | DSCP 値の最大値 |
| `EXP_MAX_VAL` | `7` | MPLS EXP 値の最大値 |

## CFG テーブル名定数 (qosorch.cpp:80–97, 99–117)

`QosOrch::m_qos_maps` に登録される CONFIG_DB テーブル名と `qos_to_ref_table_map` の参照先:

| CONFIG_DB フィールド | 参照先テーブル定数 |
|--------------------|-----------------|
| `dscp_to_tc_map` | `CFG_DSCP_TO_TC_MAP_TABLE_NAME` |
| `mpls_tc_to_tc_map` | `CFG_MPLS_TC_TO_TC_MAP_TABLE_NAME` |
| `dot1p_to_tc_map` | `CFG_DOT1P_TO_TC_MAP_TABLE_NAME` |
| `tc_to_queue_map` | `CFG_TC_TO_QUEUE_MAP_TABLE_NAME` |
| `tc_to_dot1p_map` | `CFG_TC_TO_DOT1P_MAP_TABLE_NAME` |
| `tc_to_dscp_map` | `CFG_TC_TO_DSCP_MAP_TABLE_NAME` |
| `tc_to_pg_map` | `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` |
| `pfc_to_pg_map` | `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` |
| `pfc_to_queue_map` | `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME` |
| `scheduler` | `CFG_SCHEDULER_TABLE_NAME` |
| `wred_profile` | `CFG_WRED_PROFILE_TABLE_NAME` |
| `dscp_to_fc_map` | `CFG_DSCP_TO_FC_MAP_TABLE_NAME` |
| `exp_to_fc_map` | `CFG_EXP_TO_FC_MAP_TABLE_NAME` |
| `decap_dscp_to_tc_map` | `CFG_DSCP_TO_TC_MAP_TABLE_NAME` |
| `decap_tc_to_pg_map` | `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` |
| `encap_tc_to_dscp_map` | `CFG_TC_TO_DSCP_MAP_TABLE_NAME` |
| `encap_tc_to_queue_map` | `CFG_TC_TO_QUEUE_MAP_TABLE_NAME` |
