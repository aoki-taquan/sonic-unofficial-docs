# TC_TO_DSCP_MAP — 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/qosorch.cpp`, `sonic-swss/orchagent/tunneldecaporch.cpp`

## QosOrch (orchagent/qosorch.cpp)

CONFIG_DB の `TC_TO_DSCP_MAP` を直接購読し、`handleTcToDscpTable()` → `TcToDscpMapHandler::processWorkItem()` で処理する。cfgmgr 中間層はない（CONFIG_DB → orchagent 直結）。

**STATE_DB / APPL_DB への書き込みはない。** QosOrch は`gCrmOrch` をインクルードしているが、TC_TO_DSCP_MAP の SET/DEL で CRM カウンタを更新するコードは存在しない（`gCrmOrch->` の呼び出しなし）。FlexCounter も使用しない。

---

## ASIC_DB 書込み (SAI 経由)

`TcToDscpMapHandler::addQosItem()` が `sai_qos_map_api->create_qos_map()` を呼び出し、syncd が ASIC_DB に QoS map オブジェクトを記録する。

### SET — TC_TO_DSCP_MAP 作成・更新

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP, ...)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` | 新規マップ作成 (qosorch.cpp:1271-1285) |
| `sai_qos_map_api->set_qos_map_attribute(SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST, ...)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | `<qos_map_oid>` field=`SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | 既存マップ更新時 (qosorch.cpp:204-215) |

### SET — PORT_QOS_MAP によるポートバインド

`PORT_QOS_MAP|<port>` の `tc_to_dscp_map` フィールドが TC_TO_DSCP_MAP を参照した際の副次書き込み:

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP, oid)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_PORT` | `<port_oid>` field=`SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` | 参照先 TC_TO_DSCP_MAP が SAI 解決済みの各ポート (qosorch.cpp:66, L2077-2133) |

`qos_to_attr_map`（qosorch.cpp:66）に `{tc_to_dscp_field_name, SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP}` が登録されており、`PORT_QOS_MAP` の SET 時に `resolveFieldRefValue()` が TC_TO_DSCP_MAP の OID を解決してポートに適用する。

### TUNNEL 経由の副次書き込み

`TUNNEL.encap_tc_to_dscp_map` フィールドで TC_TO_DSCP_MAP を参照した際:

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `tunnelTable[key].encap_tc_to_dscp_map_id = tc_to_dscp_map_id` | メモリのみ（ASIC_DB 直接書込みなし） | — | `resolveTunnelQosMap()` で OID 解決後 (tunneldecaporch.cpp:257) |

`encap_tc_to_dscp_map_id` は tunnelTable の in-memory struct に格納されるのみで、トンネル作成時の `addDecapTunnel()` には渡されない（qosorch.cpp:301 参照: `dscp_to_tc_map_id` と `tc_to_pg_map_id` のみ SAI create_tunnel に渡す）。
TUNNEL の `encap_tc_to_dscp_map_id` は `setDecapTunnelStatus()` での STATE_DB 書き込みにも含まれない（tunneldecaporch.cpp:1526-1531）。

### DEL — TC_TO_DSCP_MAP 削除

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `sai_qos_map_api->remove_qos_map(sai_object)` | ASIC_DB (syncd 経由) / `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` 削除 | `<qos_map_oid>` | PORT_QOS_MAP / TUNNEL 非参照時 (qosorch.cpp:188-201) |
| pending_remove=true → task_need_retry（削除スキップ） | — | — | PORT_QOS_MAP または TUNNEL から参照中 (qosorch.cpp:181-186) |

---

## STATE_DB 書込み

**TC_TO_DSCP_MAP の SET/DEL で STATE_DB への書き込みは発生しない。**
`QosOrch` は `StateTable` を保持しない。`tunneldecaporch` の `setDecapTunnelStatus()` はトンネル状態（tunnel_type, dscp_mode, ecn_mode 等）を STATE_DB に書き込むが、`encap_tc_to_dscp_map_id` フィールドは対象外（tunneldecaporch.cpp:1526-1531）。

---

## 副次書き込みサマリ

| DB | テーブル / 属性 | SET 時 | DEL 時 |
|----|----------------|--------|--------|
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP` | create / update (syncd 経由) | remove (syncd 経由, 非参照時のみ) |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT` field=`SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` | set_port_attribute (PORT_QOS_MAP 経由, syncd 経由) | SAI_NULL_OBJECT_ID (PORT_QOS_MAP DEL 時) |
| STATE_DB | — | なし | なし |
| APPL_DB | — | なし | なし |
| COUNTERS_DB | — | なし | なし |

---

## 確認コマンド

```bash
# SAI QoS map の ASIC_DB エントリ確認
sonic-db-cli ASIC_DB keys 'ASIC_STATE:SAI_OBJECT_TYPE_QOS_MAP:*'

# ポートへの TC→DSCP マップ bind 確認 (PORT_QOS_MAP 経由)
sonic-db-cli ASIC_DB hgetall 'ASIC_STATE:SAI_OBJECT_TYPE_PORT:<port_oid>'
```
