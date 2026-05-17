# DASH_ACL_* — Phase G 通信メカニズム 証跡

## 調査ソース

- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashaclorch.h`
- `sonic-swss/orchagent/zmqorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/lib/orch_zmq_config.h`
- `sonic-swss/lib/orch_zmq_config.cpp`

## 購読方式: ZmqOrch（ZMQ / ConsumerStateTable 二系統）

`DashAclOrch` は `ZmqOrch` を継承する (`dashaclorch.h:33`)。

`ZmqOrch::addConsumer()` (`zmqorch.cpp:59-78`) は db ID が `APPL_DB` または `DPU_APPL_DB` の場合:
- `zmqServer != nullptr` → `ZmqConsumerStateTable` ベースの `ZmqConsumer` Executor を登録
- `zmqServer == nullptr` → `ConsumerStateTable` ベースの `Consumer` Executor を登録

どちらも 5 テーブル全てに対して一つずつ Executor を登録する。

購読テーブル一覧 (`orchdaemon.cpp:1371-1377`):

```cpp
vector<string> dash_acl_tables = {
    APP_DASH_PREFIX_TAG_TABLE_NAME,    // DASH_PREFIX_TAG_TABLE
    APP_DASH_ACL_IN_TABLE_NAME,        // DASH_ACL_IN_TABLE
    APP_DASH_ACL_OUT_TABLE_NAME,       // DASH_ACL_OUT_TABLE
    APP_DASH_ACL_GROUP_TABLE_NAME,     // DASH_ACL_GROUP_TABLE
    APP_DASH_ACL_RULE_TABLE_NAME       // DASH_ACL_RULE_TABLE
};
```

## ZMQ 有効化フラグ

`DpuOrchDaemon::init()` (`orchdaemon.cpp:1327-1333`):

```cpp
// Enable the gNMI service to send DASH events to orchagent via the ZMQ channel.
ZmqServer *dash_zmq_server = nullptr;
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
{
    SWSS_LOG_NOTICE("Enable the gNMI service to send DASH events to orchagent via the ZMQ channel.");
    dash_zmq_server = m_zmqServer;
}
```

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED = "orch_northbond_dash_zmq_enabled"` (`orch_zmq_config.h:21`)

`get_feature_status()` は `CONFIG_DB DEVICE_METADATA|localhost` の当該フィールドを読む。デフォルト `true`（ZMQ 有効）。

## ZMQ 有効時のデータフロー

```
gNMI / SDN コントローラ
  ↓ ZmqProducerStateTable (DPU_APPL_DB / APP_DB, tcp://localhost:<port>)
ZMQ チャネル (PUSH/PULL, tcp://localhost:<port>)
  ↓
ZmqServer (orchagent 内)
  ↓ ZmqConsumerStateTable.pops()
ZmqConsumer.execute() → addToSync(entries) → drain()
  ↓
DashAclOrch::doTask(ConsumerBase&)
  ↓ テーブル名分岐
  ├─ DASH_PREFIX_TAG_TABLE → taskUpdateDashPrefixTag / taskRemoveDashPrefixTag
  ├─ DASH_ACL_IN_TABLE    → taskUpdateDashAclIn / taskRemoveDashAclIn
  ├─ DASH_ACL_OUT_TABLE   → taskUpdateDashAclOut / taskRemoveDashAclOut
  ├─ DASH_ACL_GROUP_TABLE → taskUpdateDashAclGroup / taskRemoveDashAclGroup
  └─ DASH_ACL_RULE_TABLE  → taskUpdateDashAclRule
```

## ZMQ 無効時のデータフロー

```
gNMI / SDN コントローラ
  ↓ ProducerStateTable → Redis PUBLISH (DPU_APPL_DB keyspace 通知)
ConsumerStateTable (SubscriberStateTable ではなく channel ベース)
  ↓ Consumer.execute() → addToSync() → drain()
DashAclOrch::doTask(ConsumerBase&)
```

## ZmqConsumer::execute() の動作

`zmqorch.cpp:8-39`:
- `m_ordered_queue = false`（デフォルト）: `table->pops(entries)` → `addToSync(entries)` → `drain()`
- `m_ordered_queue = true`: ループで全エントリを `m_queue` に集約 → `drain()`

DASH ACL は `ZmqOrch` コンストラクタのデフォルト引数 `orderedQueue=false, dbPersistence=false` で呼ばれる。

## SELECT_TIMEOUT / ポーリング

`ZmqConsumerStateTable` はソケットイベント駆動。ZMQ PUSH/PULL ソケットが `zmqServer` のエンドポイント（`tcp://localhost:<port>`）で受信すると即座に `execute()` が呼ばれる。明示的な SELECT_TIMEOUT はない（SocketSelect ベース）。

## addOrchList 登録

`orchdaemon.cpp:1409`:
```cpp
addOrchList(dash_acl_orch);
```

`addOrchList` は `m_orchList.push_back(o)` (`orchdaemon.cpp:1248`)。DASH ACL orch は `DpuOrchDaemon` の `m_orchList` に登録される（`DpuOrchDaemon` 固有の `init()` 内、基底クラス `OrchDaemon::init()` の `m_orchList` とは別リスト）。
