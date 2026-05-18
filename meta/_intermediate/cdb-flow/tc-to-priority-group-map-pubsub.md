# TC_TO_PRIORITY_GROUP_MAP — 通信メカニズム調査 (Phase G)

## 調査対象
- slug: tc-to-priority-group-map
- daemon: qosorch (sonic-swss/orchagent/qosorch.cpp)
- phase: pubsub (G)

## Subscription 経路

QosOrch は `Orch(db, tableNames)` 基底クラスの `addConsumer()` を通じて
`CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` に対する `SubscriberStateTable` を生成する。

CONFIG_DB の keyspace notification でエントリ変化を検出し `pops()` で現在値を読む。
APPL_DB への中継は一切行わない（直接 SAI 呼び出し）。

## doTask() 実行順序 (qosorch.cpp:2231-2252)

```cpp
void QosOrch::doTask() {
    auto *port_qos_map_cfg_exec = getExecutor(CFG_PORT_QOS_MAP_TABLE_NAME);
    auto *queue_exec = getExecutor(CFG_QUEUE_TABLE_NAME);

    // 1. PORT_QOS_MAP / QUEUE 以外の全テーブル（TC_TO_PRIORITY_GROUP_MAP を含む）を先 drain
    for (const auto &it : m_consumerMap) {
        if (exec == port_qos_map_cfg_exec || exec == queue_exec) continue;
        exec->drain();
    }
    // 2. PORT_QOS_MAP drain（マップ登録済みを前提）
    port_qos_map_cfg_exec->drain();
    // 3. QUEUE drain（ポート QoS マップ適用済みを前提）
    queue_exec->drain();
}
```

TC_TO_PRIORITY_GROUP_MAP は **step 1** で処理される（PORT_QOS_MAP/QUEUE より先）。

## STATE_DB / APPL_DB 書き込み

なし。SAI 操作結果は syslog のみ。

## evidence
- sonic-swss/orchagent/qosorch.cpp L1342 (handler 登録)
- sonic-swss/orchagent/qosorch.cpp L2231-2252 (doTask 実行順序)
- sonic-swss/orchagent/qosorch.cpp L2254-2261 (allPortsReady チェック)
- sonic-swss/orchagent/qosorch.cpp L930-934 (handleTcToPgTable)
