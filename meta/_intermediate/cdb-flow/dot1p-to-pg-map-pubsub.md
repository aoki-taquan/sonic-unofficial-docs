# dot1p-to-pg-map Phase G 調査メモ

## 調査対象

`docs/reference/config-db/dot1p-to-pg-map.md` (Phase G: pubsub / 通信メカニズム)

`DOT1P_TO_PG_MAP` テーブルは SONiC に存在しないため、等価な 2 段マッピング経路
(`DOT1P_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP` → `PORT_QOS_MAP`) を処理する `QosOrch` の
Redis 通信メカニズムを調査する。

## 調査ソース

- `sonic-swss/orchagent/orchdaemon.cpp:365-384` — QosOrch 初期化 (qos_tables vector)
- `sonic-swss/orchagent/qosorch.cpp:1313` — `QosOrch::QosOrch(DBConnector *db, vector<string> &tableNames)`
- `sonic-swss/orchagent/qosorch.cpp:2231-2252` — `QosOrch::doTask()` カスタム drain 順序
- `sonic-swss/orchagent/qosorch.cpp:2254-2258` — `allPortsReady()` チェック
- `sonic-swss/orchagent/qosorch.cpp:1331` — `handleDot1pToTcTable` handler 登録

## 主要な発見

### QosOrch は SubscriberStateTable を使用

`Orch(db, tableNames)` 基底クラスが `CFG_DOT1P_TO_TC_MAP_TABLE_NAME` 等を
`SubscriberStateTable` として登録する。keyspace PSUBSCRIBE で変化を検出。

### qos_tables に含まれるテーブル (orchdaemon.cpp:365-381)

```cpp
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    CFG_MPLS_TC_TO_TC_MAP_TABLE_NAME,
    CFG_DOT1P_TO_TC_MAP_TABLE_NAME,       // ← Phase G 対象
    CFG_QUEUE_TABLE_NAME,
    CFG_PORT_QOS_MAP_TABLE_NAME,           // ← Phase G 対象
    CFG_WRED_PROFILE_TABLE_NAME,
    CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, // ← Phase G 対象
    CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME,
    CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME,
    CFG_DSCP_TO_FC_MAP_TABLE_NAME,
    CFG_EXP_TO_FC_MAP_TABLE_NAME,
    CFG_TC_TO_DOT1P_MAP_TABLE_NAME,
    CFG_TC_TO_DSCP_MAP_TABLE_NAME
};
```

### doTask() カスタム drain 順序 (qosorch.cpp:2231-2252)

```cpp
void QosOrch::doTask()
{
    auto *port_qos_map_cfg_exec = getExecutor(CFG_PORT_QOS_MAP_TABLE_NAME);
    auto *queue_exec = getExecutor(CFG_QUEUE_TABLE_NAME);

    // pass 1: PORT_QOS_MAP と QUEUE を除く全テーブル
    for (const auto &it : m_consumerMap) {
        auto *exec = it.second.get();
        if (exec == port_qos_map_cfg_exec || exec == queue_exec) continue;
        exec->drain();
    }
    // pass 2: PORT_QOS_MAP
    port_qos_map_cfg_exec->drain();
    // pass 3: QUEUE
    queue_exec->drain();
}
```

これにより DOT1P_TO_TC_MAP / TC_TO_PRIORITY_GROUP_MAP は PORT_QOS_MAP より先に drain される。
task_need_retry の発生を最小化する設計。

### APPL_DB 中継なし

QosOrch は CONFIG_DB を直接購読し、SAI API を呼ぶ。APPL_DB への書き込みはない。
