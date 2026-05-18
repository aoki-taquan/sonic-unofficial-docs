# DSCP_TO_PG_MAP — 副次 DB 書込分析 (Phase F)

生成日: 2026-05-18
ソース:
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.cpp`

---

## 概要

`DSCP_TO_PG_MAP` テーブル自体は存在しないため、実際の DSCP → PG マッピングを担う 2 段構成
（`DSCP_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP` → `PORT_QOS_MAP`）の副次 DB 書き込みを記述する。

CONFIG_DB → QosOrch (orchagent) 直結の構成であり、cfgmgr ステージ・APPL_DB ステージは存在しない。
STATE_DB / APPL_STATE_DB への書き込みも行わない。

---

## DSCP_TO_TC_MAP (段階 1) の副次書き込み

### SET (DSCP_TO_TC_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_DSCP_TO_TC, ...)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 新規エントリ (qosorch.cpp:265-276) |
| `sai_qos_map_api->set_qos_map_attribute(SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST, ...)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 既存マップの更新 (qosorch.cpp:207) |

SAI オブジェクトの in-place 更新 (`set_qos_map_attribute`) は既存の参照 OID を変えずに適用されるため、
PORT_QOS_MAP や TUNNEL_DECAP_TABLE が保持するバインドはそのまま有効となり、
**全参照先ポート・トンネルに即時反映される**。

### SET (PORT_QOS_MAP|<port>) — dscp_to_tc_map フィールドバインド

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | `<port_oid>` field=`SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | PORT_QOS_MAP.dscp_to_tc_map が指定された全ポートに対して (qosorch.cpp:2086, 2193) |

### SET (PORT_QOS_MAP|global) — スイッチレベル適用

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` | `<switch_oid>` field=`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | PORT_QOS_MAP\|global に dscp_to_tc_map フィールドがあり SAI capability あり (qosorch.cpp:1956-1975) |

### DEL (DSCP_TO_TC_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->remove_qos_map(sai_object)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` 削除 | `<qos_map_oid>` | PORT_QOS_MAP / TUNNEL_DECAP_TABLE 非参照時 |
| `m_pendingRemove=true` + `task_need_retry` | — | — | PORT_QOS_MAP または TUNNEL_DECAP_TABLE から参照中 (qosorch.cpp:181-186) |

---

## TC_TO_PRIORITY_GROUP_MAP (段階 2) の副次書き込み

### SET (TC_TO_PRIORITY_GROUP_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP, ...)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 新規エントリ (qosorch.cpp:913-925) |
| `sai_qos_map_api->set_qos_map_attribute(SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST, ...)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 既存マップの更新 (qosorch.cpp:207) |

DSCP_TO_TC_MAP と同様に in-place 更新であるため、既存バインドは変えずに全参照先ポートに即時反映。

### SET (PORT_QOS_MAP|<port>) — tc_to_pg_map フィールドバインド

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP, oid)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | `<port_oid>` field=`SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | PORT_QOS_MAP.tc_to_pg_map が指定された全ポートに対して (qosorch.cpp:2086, 2193) |

### PORT_QOS_MAP の PFC/PFCwd 副次書き込み（TC→PG バインド時の同時発生）

`handlePortQosMapTable()` は `tc_to_pg_map` だけでなく `pfc_enable` / `pfcwd_sw_enable` フィールドも処理し、
ポート SAI オブジェクトと PortsOrch 内部状態を同時変更する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `gPortsOrch->setPortPfc(port_id, pfc_enable)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | field=`SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL` | pfc_enable != 0 または旧値 != 0 (qosorch.cpp:2208-2216) |
| `gPortsOrch->setPortPfcWatchdogStatus(port_id, pfcwd_sw_enable)` | PortsOrch 内部 m_port.m_pfcwd_sw_bitmap (メモリのみ) | — | 無条件 (qosorch.cpp:2224) |
| `gPortsOrch->setPortPfc(port_id, 0)` (DEL 時) | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | field=`SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL` | PORT_QOS_MAP DEL 時 (qosorch.cpp:2100) |

### DEL (TC_TO_PRIORITY_GROUP_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->remove_qos_map(sai_object)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` 削除 | `<qos_map_oid>` | PORT_QOS_MAP / TUNNEL_DECAP_TABLE 非参照時 |
| `m_pendingRemove=true` + `task_need_retry` | — | — | PORT_QOS_MAP または TUNNEL_DECAP_TABLE から参照中 (qosorch.cpp:181-186) |

---

## TunnelDecapOrch (tunneldecaporch.cpp) からの参照

DSCP_TO_TC_MAP および TC_TO_PRIORITY_GROUP_MAP は TUNNEL_DECAP_TABLE からも
`decap_dscp_to_tc_map` / `decap_tc_to_pg_map` フィールドで参照され、SAI トンネルオブジェクトに適用される。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_tunnel_api->create_tunnel(..., SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL` | `<tunnel_oid>` field=`SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` | DSCP_TO_TC_MAP 指定かつ dscp_to_tc_map_id != SAI_NULL_OBJECT_ID (tunneldecaporch.cpp:832-834) |
| `sai_tunnel_api->create_tunnel(..., SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP, oid)` | ASIC_DB (syncd 経由) `ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL` | `<tunnel_oid>` field=`SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP` | TC_TO_PRIORITY_GROUP_MAP 指定かつ tc_to_pg_map_id != SAI_NULL_OBJECT_ID (tunneldecaporch.cpp:840-843) |

---

## 副次書き込みサマリ

| DB | 副次書き込みテーブル | SET 時 | DEL 時 | 備考 |
|----|---------------------|--------|--------|------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | create / set_attribute (syncd 経由) | remove (syncd 経由) | 両マップとも同様 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT` field=`SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | set_port_attribute (syncd 経由) | set SAI_NULL_OBJECT_ID (qosorch.cpp:2086) | PORT_QOS_MAP.dscp_to_tc_map バインド時 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT` field=`SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | set_port_attribute (syncd 経由) | set SAI_NULL_OBJECT_ID (qosorch.cpp:2086) | PORT_QOS_MAP.tc_to_pg_map バインド時 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT` field=`SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL` | set (PFC ビットマスク) | set 0 (DEL 時) | PORT_QOS_MAP.pfc_enable / setPortPfc (qosorch.cpp:2100, 2215) |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` field=`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | set_switch_attribute | set SAI_NULL_OBJECT_ID | PORT_QOS_MAP\|global 時のみ (qosorch.cpp:1963-1993) |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL` | create_tunnel (decap QoS 属性) | — | tunneldecaporch.cpp:832-843 |
| PortsOrch 内部 | m_port.m_pfcwd_sw_bitmap (メモリ) | setPortPfcWatchdogStatus | — | STATE_DB 書き込みなし; 無条件 (qosorch.cpp:2224) |
| APPL_DB | — | なし | なし | cfgmgr ステージなし |
| STATE_DB | — | なし | なし | QosOrch は STATE_DB に書き込まない |
| APPL_STATE_DB | — | なし | なし | QosOrch は APPL_STATE_DB に書き込まない |
| COUNTERS_DB | — | なし | なし | QoS map に対するカウンタは存在しない |

> **Evidence**: `qosorch.cpp:61,67,181-186,207,265-276,913-925,1956-1993,2086,2100,2193,2208-2224`; `tunneldecaporch.cpp:832-843`
