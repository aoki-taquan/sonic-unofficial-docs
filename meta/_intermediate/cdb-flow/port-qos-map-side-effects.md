# PORT_QOS_MAP — 副次 DB 書込 (Phase F)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 概要

`QosOrch::handlePortQosMapTable` / `handleGlobalQosMap` が PORT_QOS_MAP エントリを処理する際に発生する副次的な DB 書込・SAI 操作を網羅する。

---

## 1. per-port キー (key != "global") — SET

### 1-1. SAI ポート属性 bind (ASIC_DB 経由)

`sai_port_api->set_port_attribute(port.m_port_id, &attr)` を全マップフィールドに対して呼び出す。  
syncd が SAI 呼び出しを ASIC_DB の `ASIC_STATE:SAI_OBJECT_TYPE_PORT:<oid>` に書き込む（syncd による間接書込）。

| フィールド | SAI 属性 | evidence |
|---|---|---|
| `dscp_to_tc_map` | `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | `qosorch.cpp:60-100` |
| `tc_to_queue_map` | `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` | `qosorch.cpp:64,103` |
| `tc_to_pg_map` | `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | `qosorch.cpp:67,106` |
| `pfc_to_queue_map` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` | `qosorch.cpp:69,108` |
| `scheduler` | `SAI_PORT_ATTR_QOS_SCHEDULER_PROFILE_ID` | `qosorch.cpp:70,109` |
| (削除されたマップ) | 上記対応属性、値 `SAI_NULL_OBJECT_ID` | `qosorch.cpp:2171` |

### 1-2. PFC bitmask の SAI 書込

`gPortsOrch->setPortPfc(port.m_port_id, pfc_enable)` — `pfc_enable || old_pfc_enable` が true の場合のみ呼び出される。  
内部で `sai_port_api->set_port_attribute()` を `SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL` (または per-port PFC 属性) に発行 → ASIC_DB に間接書込。

evidence: `qosorch.cpp:2213-2221`

### 1-3. PFC Watchdog bitmask の内部状態更新

`gPortsOrch->setPortPfcWatchdogStatus(port.m_port_id, pfcwd_sw_enable)` — **無条件**に呼び出される。  
PortsOrch 内部の `m_port_list` エントリの `m_pfc_bitmask` を更新する（CONFIG_DB / APPL_DB / ASIC_DB への直接書込なし）。PfcWdOrch がポーリングして参照する。

evidence: `qosorch.cpp:2224`

### 1-4. m_qos_maps 参照カウント更新

`setObjectReference(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, key, map_type_name, object_name)` — QosOrch の in-process object_reference_map を更新。DB 書込なし。  
DEL 時: `removeMeFromObjsReferencedByMe(...)` で逆参照を解除し、参照先マップ OID の削除ブロックを回避。

evidence: `qosorch.cpp:2133, 2170`

---

## 2. per-port キー (key != "global") — DEL

- 全マップフィールドに `SAI_NULL_OBJECT_ID` を `sai_port_api->set_port_attribute()` で書き込み → ASIC_DB 間接書込。
- `gPortsOrch->setPortPfc(port.m_port_id, 0)` で PFC を全無効化 → ASIC_DB 間接書込。
- `removeObject(m_qos_maps, ...)` で参照カウントを削除。

evidence: `qosorch.cpp:2060-2110`

---

## 3. global キー (key == "global") — SET

`PORT_QOS_MAP|global` では `dscp_to_tc_map` フィールドのみが有効。他フィールドは `SWSS_LOG_WARN` でスキップ。

### 3-1. Switch レベル SAI 属性 bind

`sai_switch_api->set_switch_attribute(gSwitchId, &attr)` を `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` に発行。  
syncd が `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH:<switch_oid>` を ASIC_DB に書き込む。

事前に `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` で capability を確認し、非対応 ASIC では SAI 呼び出しをスキップ（戻り値 false → early return true、エラーなし）。

evidence: `qosorch.cpp:1951-1976, 2030`

### 3-2. m_qos_maps 参照カウント更新

`setObjectReference(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, PORT_NAME_GLOBAL, ...)` — in-process のみ。

evidence: `qosorch.cpp:2032`

---

## 4. global キー (key == "global") — DEL

`sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, SAI_NULL_OBJECT_ID)` → ASIC_DB 間接書込。  
`removeObject(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, PORT_NAME_GLOBAL)` — in-process のみ。

evidence: `qosorch.cpp:1993-1995`

---

## 5. 副次書込先サマリ

| 書込先 | 操作 | トリガ条件 |
|---|---|---|
| ASIC_DB (`SAI_OBJECT_TYPE_PORT`) | SAI ポート属性 set/clear (syncd 経由) | per-port SET / DEL |
| ASIC_DB (`SAI_OBJECT_TYPE_SWITCH`) | SAI switch 属性 set/clear (syncd 経由) | global SET / DEL |
| PortsOrch 内部状態 | `m_pfc_bitmask` 更新 | `pfcwd_sw_enable` 省略時も含む無条件書込 |
| QosOrch in-process (`m_qos_maps`) | 参照カウント更新 | SET / DEL 両方 |
| APPL_DB | なし (QosOrch は直接 APPL_DB を書かない) | — |
| CONFIG_DB | なし | — |

---

## 6. 注意点

- APPL_DB への書込経路なし — QosOrch は CONFIG_DB を直接購読し SAI に即反映する。
- `pfcwd_sw_enable` は **省略時も 0 として無条件に** PortsOrch 内部状態へ書込まれる（`pfc_enable` の条件付きスキップと非対称）。
- global キーは `dscp_to_tc_map` 以外のフィールドを無視する（capability 確認あり）。
