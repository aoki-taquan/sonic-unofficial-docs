# DSCP_TO_TC_MAP — 副次 DB 書込分析 (Phase F)

生成日: 2026-05-16
ソース:
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.cpp`

---

## QosOrch (orchagent/qosorch.cpp)

QosOrch は CONFIG_DB の `DSCP_TO_TC_MAP` テーブルを直接購読し、SAI QoS map オブジェクトを生成する。
cfgmgr 経由の APPL_DB ステージは存在しない（CONFIG_DB → orchagent 直結）。
STATE_DB / APPL_STATE_DB への書き込みも行わない。

### SET (DSCP_TO_TC_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_DSCP_TO_TC, ...)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 常時 (新規マップ作成) |
| `sai_qos_map_api->set_qos_map_attribute(...)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` field=`SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | 既存マップ更新時 |

※ SAI 呼び出しは syncd 経由で ASIC_DB の `ASIC_STATE` テーブルに自動反映される。QosOrch が直接 ASIC_DB へ書き込むわけではない。

### SET (PORT_QOS_MAP|<port>) — dscp_to_tc_map フィールド

DSCP_TO_TC_MAP 作成後に PORT_QOS_MAP でポートへバインドした場合の副次書き込み:

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | `<port_oid>` field=`SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | PORT_QOS_MAP.dscp_to_tc_map が指定されたポートに対して |

### SET (PORT_QOS_MAP|global) — スイッチレベル適用

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` | `<switch_oid>` field=`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | PORT_QOS_MAP\|global の dscp_to_tc_map フィールドかつ SAI capability あり (qosorch.cpp:1956-1975) |

### DEL (DSCP_TO_TC_MAP|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->remove_qos_map(sai_object)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` 削除 | `<qos_map_oid>` | PORT_QOS_MAP / TUNNEL 非参照時 |
| pending_remove=true → `task_need_retry` | — | — | PORT_QOS_MAP または TUNNEL_DECAP_TABLE から参照中 (qosorch.cpp:181-186) |

### DEL (PORT_QOS_MAP|global) — スイッチレベル解除

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, SAI_NULL_OBJECT_ID)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` | `<switch_oid>` field=`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | PORT_QOS_MAP\|global の dscp_to_tc_map フィールド存在時 (qosorch.cpp:1993) |

---

## TunnelDecapOrch (orchagent/tunneldecaporch.cpp)

DSCP_TO_TC_MAP は TUNNEL_DECAP_TABLE からも参照される。tunneldecaporch は TUNNEL_DECAP_TABLE を購読し、SAI トンネルオブジェクトのプロパティとして DSCP_TO_TC MAP を適用する。

### SET (TUNNEL_DECAP_TABLE|<name>) — dscp_to_tc_map フィールド参照

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_tunnel_api->create_tunnel(..., SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP, oid)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL` | `<tunnel_oid>` field=`SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` | DSCP_TO_TC_MAP 指定かつ dscp_to_tc_map_id != SAI_NULL_OBJECT_ID (tunneldecaporch.cpp:831-834) |

dscp_to_tc_map_id == SAI_NULL_OBJECT_ID の場合はトンネル作成時に属性をスキップ（silent skip, tunneldecaporch.cpp:832）。

---

## 副次書き込みサマリ

| DB | 副次書き込みテーブル | SET 時 | DEL 時 | 備考 |
|----|---------------------|--------|--------|------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | create / set_attribute (syncd 経由) | remove (syncd 経由) | qosorch.cpp:265-276, 207, 289-293 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT` field=`SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | set_port_attribute (syncd 経由) | set SAI_NULL_OBJECT_ID (DEL 時) | qosorch.cpp:2086, 2193; PORT_QOS_MAP handler |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` field=`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | set_switch_attribute (syncd 経由) | set SAI_NULL_OBJECT_ID (PORT_QOS_MAP\|global DEL 時) | qosorch.cpp:1963-1971, 1993 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_TUNNEL` field=`SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` | create_tunnel (syncd 経由) | — | tunneldecaporch.cpp:831-834, 1084 |
| APPL_DB | — | なし | なし | cfgmgr ステージなし |
| STATE_DB | — | なし | なし | QosOrch は STATE_DB に書き込まない |
| APPL_STATE_DB | — | なし | なし | QosOrch は APPL_STATE_DB に書き込まない |
| COUNTERS_DB | — | なし | なし | QoS map に対するカウンタは存在しない |

> **Evidence**: `sonic-swss/orchagent/qosorch.cpp:61,181-186,265-276,289-293,1956-1975,1988-2030,2086,2193`; `sonic-swss/orchagent/tunneldecaporch.cpp:831-834,1084`
