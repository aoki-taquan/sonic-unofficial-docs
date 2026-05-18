# dscp-to-pg-map — Phase C 調査証跡 (cross-refs)

date: 2026-05-18
target: docs/reference/config-db/dscp-to-pg-map.md

## 調査対象

`DSCP_TO_PG_MAP` テーブルは存在しないため、DSCP→PG 機能を実現する 2 段構成テーブルの参照関係を調査。

## 参照ソース

- `sonic-swss/orchagent/qosorch.cpp:80-116` — m_qos_maps 初期化、qos_to_ref_table_map 定義
- `sonic-swss/orchagent/qosorch.cpp:2124-2133` — handlePortQosMapTable の resolveFieldRefValue 呼び出し
- `sonic-swss/orchagent/qosorch.cpp:2258-2261` — allPortsReady ガード
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang:85-91` — tc_to_pg_map leafref
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang:129-135` — dscp_to_tc_map leafref

## 主な発見

1. YANG leafref: `PORT_QOS_MAP.dscp_to_tc_map` → `DSCP_TO_TC_MAP_LIST.name` (leafref あり)
2. YANG leafref: `PORT_QOS_MAP.tc_to_pg_map` → `TC_TO_PRIORITY_GROUP_MAP_LIST.name` (leafref あり)
3. `DSCP_TO_PG_MAP` 用の leafref / YANG モジュールは存在しない（テーブル非実在のため）
4. `m_qos_maps` では両テーブルが独立した object_reference_map を持つ（参照カウンタ独立）
5. `allPortsReady()` が false の間は全 QoS テーブル処理がブロック（`qosorch.cpp:2258-2261`）
