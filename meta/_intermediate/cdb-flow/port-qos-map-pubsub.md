# PORT_QOS_MAP — 通信メカニズム (Phase G)

## 概要

CONFIG_DB の `PORT_QOS_MAP` テーブルに対する Consumer 登録・イベント伝搬・SAI 呼び出し経路を示す。

## Consumer 登録

**登録箇所**: `sonic-swss/orchagent/orchdaemon.cpp:367-384`

```cpp
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    ...
    CFG_PORT_QOS_MAP_TABLE_NAME,   // ← PORT_QOS_MAP
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`QosOrch` は `Orch` 基底クラスを継承し、`CONFIG_DB` の全 QoS テーブルに対して
**SubscriberStateTable** ベースの Consumer を一括登録する。`PORT_QOS_MAP` 専用に
独立した SubscriberStateTable を持つのではなく、QoS orch 全体で共有される
`DBConnector(m_configDb)` + 複数テーブル名の配列として登録される。

**ハンドラ登録**: `qosorch.cpp:1335`

```cpp
m_qos_handler_map.insert(
    qos_handler_pair(CFG_PORT_QOS_MAP_TABLE_NAME,
                     &QosOrch::handlePortQosMapTable));
```

`initTableHandlers()` 内で `CFG_PORT_QOS_MAP_TABLE_NAME` → `handlePortQosMapTable`
のマッピングが登録される。

## イベント伝搬フロー

```
CONFIG_DB
  PORT_QOS_MAP|<port>  (SET / DEL)
       │
       │  SubscriberStateTable (swss::Consumer)
       ▼
  QosOrch::doTask()                          (qosorch.cpp:2231-2251)
       │  port_qos_map_cfg_exec->drain() を最後に呼ぶ
       │  (他の QoS テーブルより優先度低く drain)
       ▼
  QosOrch::doTask(Consumer&)                 (qosorch.cpp:2254-2295)
       │  consumer.getTableName() == CFG_PORT_QOS_MAP_TABLE_NAME
       │  → m_qos_handler_map[...] = &handlePortQosMapTable
       ▼
  QosOrch::handlePortQosMapTable(Consumer&, tuple)  (qosorch.cpp:2046-2229)
       │
       ├─ key == "global"  → handleGlobalQosMap()
       │
       ├─ op == DEL
       │     ├─ gPortsOrch->getPort()  でポート取得
       │     ├─ sai_port_api->set_port_attribute(SAI_NULL_OBJECT_ID) で全 map を unset
       │     └─ gPortsOrch->setPortPfc(port_id, 0)
       │
       └─ op == SET
             ├─ resolveFieldRefValue()  で各 map OID を解決
             │    └─ 未解決 → task_need_retry (qosorch.cpp:2129)
             ├─ pfc_enable / pfcwd_sw_enable ビットマスク計算
             ├─ sai_port_api->set_port_attribute(port_id, &attr)
             │    各 SAI 属性 (SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP 等)
             ├─ gPortsOrch->setPortPfc(port_id, pfc_enable)    [条件付き]
             └─ gPortsOrch->setPortPfcWatchdogStatus(port_id, pfcwd_sw_enable) [無条件]
```

## SAI 呼び出し詳細

| CONFIG_DB フィールド | SAI API | SAI 属性 | ソース |
|---------------------|---------|----------|--------|
| `dscp_to_tc_map` | `sai_port_api->set_port_attribute` | `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | `qosorch.cpp:60-73` |
| `tc_to_queue_map` | `sai_port_api->set_port_attribute` | `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` | `qosorch.cpp:60-73` |
| `tc_to_pg_map` | `sai_port_api->set_port_attribute` | `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | `qosorch.cpp:60-73` |
| `pfc_to_pg_map` | `sai_port_api->set_port_attribute` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` | `qosorch.cpp:60-73` |
| `pfc_to_queue_map` | `sai_port_api->set_port_attribute` | `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` | `qosorch.cpp:60-73` |
| `dscp_to_tc_map` (global) | `sai_switch_api->set_switch_attribute` | `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` | `qosorch.cpp:2030` |
| `pfc_enable` | `gPortsOrch->setPortPfc` | (PFC bitmap) | `qosorch.cpp:2215` |
| `pfcwd_sw_enable` | `gPortsOrch->setPortPfcWatchdogStatus` | (PFC watchdog bitmap) | `qosorch.cpp:2224` |

## APPL_DB 経由なし

`PORT_QOS_MAP` の処理は **CONFIG_DB → orchagent → SAI** の直結経路であり、
APPL_DB への書き込みは行われない。master には `qosmgrd` は存在せず、
中間翻訳プロセスは不在。

## doTask 実行順序の特殊性

`QosOrch::doTask()` (qosorch.cpp:2231) では、`port_qos_map_cfg_exec` と
`queue_exec` を他の QoS テーブルの drain より後に処理する。これは PORT_QOS_MAP
が参照する各 QoS map (DSCP→TC, TC→Queue 等) が先に作成されてから
ポートバインドを行う必要があるため。参照解決失敗時は `task_need_retry` で
キューに残り自動再処理される。
