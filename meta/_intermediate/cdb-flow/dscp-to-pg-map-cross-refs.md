# Phase C — DSCP_TO_PG_MAP 暗黙参照テーブル調査

調査日: 2026-05-18

## 調査結論

`DSCP_TO_PG_MAP` テーブルは存在しないため、参照関係は 2 段マッピングを構成する実在テーブル（`DSCP_TO_TC_MAP` および `TC_TO_PRIORITY_GROUP_MAP`）に対する参照として整理する。

## DSCP_TO_TC_MAP への参照元

### PORT_QOS_MAP (CONFIG_DB)

`PORT_QOS_MAP` の `dscp_to_tc_map` フィールドが `DSCP_TO_TC_MAP` をキー参照する。

- YANG leafref: `sonic-port-qos-map.yang` の `dscp_to_tc_map` リーフ → `DSCP_TO_TC_MAP` leafref
- 実装: `qosorch.cpp:100` `qos_to_ref_table_map` に `{dscp_to_tc_field_name, CFG_DSCP_TO_TC_MAP_TABLE_NAME}` が登録
- 未解決時: `resolveFieldRefValue()` が失敗し `task_need_retry` を返す (`qosorch.cpp:2021-2026`, `2124-2129`)

### TUNNEL_DECAP_TABLE (APPL_DB)

IPinIP / VXLAN デカプセルトンネルエントリの `decap_dscp_to_tc_map` フィールドが `DSCP_TO_TC_MAP` を参照する。

- 実装: `tunneldecaporch.cpp:213-220` — `resolveTunnelQosMap(table_name, key, decap_dscp_to_tc_field_name, t)`
- 未解決時: `"QoS map decap_dscp_to_tc_map is not ready yet"` + `task_need_retry`

## TC_TO_PRIORITY_GROUP_MAP への参照元

### PORT_QOS_MAP (CONFIG_DB)

`PORT_QOS_MAP` の `tc_to_pg_map` フィールドが `TC_TO_PRIORITY_GROUP_MAP` をキー参照する。

- YANG leafref: `sonic-port-qos-map.yang` の `tc_to_pg_map` リーフ → `TC_TO_PRIORITY_GROUP_MAP` leafref
- 実装: `qosorch.cpp:106` `qos_to_ref_table_map` に `{tc_to_pg_map_field_name, CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME}` が登録
- 未解決時: `resolveFieldRefValue()` が失敗し `task_need_retry` を返す (`qosorch.cpp:2124-2129`)

### TUNNEL_DECAP_TABLE (APPL_DB)

IPinIP / VXLAN デカプセルトンネルエントリの `decap_tc_to_pg_map` フィールドが `TC_TO_PRIORITY_GROUP_MAP` を参照する。

- 実装: `tunneldecaporch.cpp:230-235` — `resolveTunnelQosMap(table_name, key, decap_tc_to_pg_field_name, t)`
- 未解決時: `"QoS map decap_tc_to_pg_map is not ready yet"` + `task_need_retry`

## コード証跡

- `sonic-swss/orchagent/qosorch.cpp:99-107` — `qos_to_ref_table_map` 定義
- `sonic-swss/orchagent/qosorch.cpp:2021-2026` — global PORT_QOS_MAP での resolveFieldRefValue
- `sonic-swss/orchagent/qosorch.cpp:2124-2129` — per-port PORT_QOS_MAP での resolveFieldRefValue
- `sonic-swss/orchagent/tunneldecaporch.cpp:213-235` — TUNNEL_DECAP_TABLE での QoS マップ解決
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang` — leafref 定義
