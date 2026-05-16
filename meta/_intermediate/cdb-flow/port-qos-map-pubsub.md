# PORT_QOS_MAP — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `PORT_QOS_MAP` テーブル。購読者は `orchagent` 内 `QosOrch` (`sonic-swss/orchagent/qosorch.cpp`)。

## 1. 購読 API — `SubscriberStateTable` (Redis keyspace 通知)

`QosOrch` は `Orch` 基底クラスを介して `PORT_QOS_MAP` を購読する。`orchdaemon.cpp` の `qos_tables` ベクタに `CFG_PORT_QOS_MAP_TABLE_NAME` を含め、`QosOrch(m_configDb, qos_tables)` コンストラクタに転送する:

```cpp
// orchdaemon.cpp:367-384
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    ...
    CFG_PORT_QOS_MAP_TABLE_NAME,
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`Orch::addConsumer()` が DB 種別で購読クラスを切り替える:

```cpp
// orchagent/orch.cpp (Orch::addConsumer)
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
{
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
        TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
}
else
{
    addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

- `CONFIG_DB` 起源の `PORT_QOS_MAP` は **`SubscriberStateTable`** が選ばれる。
- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:PORT_QOS_MAP|*` の PSUBSCRIBE) を購読する。channel ベースの publisher (`PUBLISH`) は使わない。
- CONFIG_DB の writer (`sonic-cfggen` / `config` CLI / `db_migrator.py`) は `HSET PORT_QOS_MAP|<ifname> <field> <value>` を行うのみで、Redis サーバの keyspace 通知機能が変更を購読者に伝達する。

## 2. POP_BATCH_SIZE

`SubscriberStateTable` のコンストラクタ第3引数は `TableConsumable::DEFAULT_POP_BATCH_SIZE`:

```cpp
// sonic-swss-common/common/table.h:164
static constexpr int DEFAULT_POP_BATCH_SIZE = 128;
```

- 1 回の `pops()` 呼び出しで **最大 128 件** の keyspace イベントをまとめて取り出す。
- `orchagent -b <batch_size>` オプションは APPL_DB 側 `ConsumerStateTable` のみに作用し、`SubscriberStateTable` のバッチサイズには影響しない。

## 3. Keyspace パターン

- Redis Key パターン: `PORT_QOS_MAP|<ifname>` (区切り文字は `|` — `swsscommon` の `TableNameSeparator` 既定値)。
- keyspace event 名前空間: `__keyspace@4__:PORT_QOS_MAP:*` (CONFIG_DB の dbId は通常 4)。
- `SubscriberStateTable` は内部で `psubscribe __keyspace@<id>__:<table><sep>*` を発行する。

## 4. ディスパッチ — `doTask(Consumer &)` への合流

`QosOrch::initTableHandlers()` が `m_qos_handler_map` にエントリを登録し、`doTask(Consumer&)` が `consumer.getTableName()` でハンドラを選択する:

```cpp
// qosorch.cpp:1335
m_qos_handler_map.insert(qos_handler_pair(CFG_PORT_QOS_MAP_TABLE_NAME, &QosOrch::handlePortQosMapTable));

// qosorch.cpp:2254-2275 (doTask)
void QosOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady())
        return;

    auto qos_map_type_name = consumer.getTableName();
    if (m_qos_handler_map.find(qos_map_type_name) == m_qos_handler_map.end())
    {
        SWSS_LOG_ERROR("Task %s handler is not initialized", qos_map_type_name.c_str());
        it = consumer.m_toSync.erase(it);
        continue;
    }
    auto task_status = (this->*(m_qos_handler_map[qos_map_type_name]))(consumer, it->second);
    ...
}
```

- すなわち CONFIG_DB の `PORT_QOS_MAP` 変更は `SubscriberStateTable` → `Consumer::execute()` → `QosOrch::doTask(Consumer&)` → `QosOrch::handlePortQosMapTable()` の経路で処理される。

## 5. PORT_QOS_MAP 専用の drain 順序制御

`QosOrch::doTask()` (引数なし版) は `PORT_QOS_MAP` Consumer を**最後に drain** する特別な順序制御を持つ:

```cpp
// qosorch.cpp:2231-2252
void QosOrch::doTask()
{
    auto *port_qos_map_cfg_exec = getExecutor(CFG_PORT_QOS_MAP_TABLE_NAME);
    auto *queue_exec = getExecutor(CFG_QUEUE_TABLE_NAME);

    for (const auto &it : m_consumerMap)
    {
        auto *exec = it.second.get();
        if (exec == port_qos_map_cfg_exec || exec == queue_exec)
            continue;
        exec->drain();
    }
    port_qos_map_cfg_exec->drain();
    queue_exec->drain();
}
```

- `DSCP_TO_TC_MAP` / `TC_TO_QUEUE_MAP` 等の map テーブルが先に drain されてから `PORT_QOS_MAP` が処理される。
- これにより、`PORT_QOS_MAP` が参照する map が先に SAI に登録された状態で binding 処理が行われる。
- `task_need_retry` で残置されたエントリは次サイクルで自動再処理される。

## 6. SAI 経路

```
QosOrch::handlePortQosMapTable()
  → key == PORT_NAME_GLOBAL ("global"):
      handleGlobalQosMap()
        → sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, ...)
  → key == <port-name>:
      gPortsOrch->getPort(port_name, port)
        → sai_port_api->set_port_attribute(port.m_port_id, {.id=SAI_PORT_ATTR_QOS_*_MAP, .value.oid=...})
      gPortsOrch->setPortPfc() / setPortPfcWatchdogStatus()
```

## 7. 起動時スナップショット

`SubscriberStateTable` は購読開始時に `HGETALL` 相当のスキャンで既存エントリを `m_buffer` に流し込み、その後に keyspace 通知へ切り替える設計のため、`orchagent` 起動時に CONFIG_DB に既に存在する `PORT_QOS_MAP|*` エントリも一度 `SET` イベントとして配信される。これにより冷起動と動的変更が同じハンドラ経路に乗る。

## 8. TTL / 永続性

- CONFIG_DB の `PORT_QOS_MAP` エントリには TTL は設定されない（CONFIG_DB は永続前提）。
- `notify-keyspace-events` は `redis.conf` 側で有効化されている前提（SONiC では `database_config.json` の CONFIG_DB エントリで `K` を含む）。

## 9. allPortsReady ガード

`doTask(Consumer&)` の先頭で `gPortsOrch->allPortsReady()` を確認し、全ポートが初期化済みでない場合は処理をスキップする（`qosorch.cpp:2258`）。これは PORT_QOS_MAP が実際のポートオブジェクトを参照するため、ポート初期化前の適用を防ぐ安全機構。

## 10. 関連リファレンス

- `sonic-swss/orchagent/orchdaemon.cpp:367-384` (qos_tables ベクタ + QosOrch 生成)
- `sonic-swss/orchagent/qosorch.cpp:1313-1318` (QosOrch::QosOrch コンストラクタ)
- `sonic-swss/orchagent/qosorch.cpp:1326-1345` (initTableHandlers)
- `sonic-swss/orchagent/qosorch.cpp:1335` (CFG_PORT_QOS_MAP_TABLE_NAME → handlePortQosMapTable 登録)
- `sonic-swss/orchagent/qosorch.cpp:2046-2229` (handlePortQosMapTable 実装)
- `sonic-swss/orchagent/qosorch.cpp:2231-2252` (doTask drain 順序制御)
- `sonic-swss/orchagent/qosorch.cpp:2254-2295` (doTask(Consumer&))
- `sonic-swss-common/common/table.h:164` (DEFAULT_POP_BATCH_SIZE = 128)
