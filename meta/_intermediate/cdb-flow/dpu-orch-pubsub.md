# dpu-orch — Phase F ZMQ 購読方式 調査メモ

## 調査対象

`DpuOrchDaemon` が `DPU_APPL_DB` DASH テーブル群を受信するための ZMQ 購読方式。
`ZmqServer` / `ZmqConsumerStateTable` の連携を解析する。

## 1. ZmqOrch::addConsumer() — DPU_APPL_DB 判別と購読生成

`sonic-swss/orchagent/zmqorch.cpp:59-80`

```cpp
void ZmqOrch::addConsumer(DBConnector *db, string tableName, int pri, ZmqServer *zmqServer, bool orderedQueue, bool dbPersistence)
{
    if (db->getDbId() == APPL_DB || db->getDbId() == DPU_APPL_DB)
    {
        if (zmqServer != nullptr)
        {
            addExecutor(new ZmqConsumer(
                new ZmqConsumerStateTable(db, tableName, *zmqServer, gBatchSize, pri, dbPersistence),
                this, tableName, orderedQueue));
        }
        else
        {
            addExecutor(new Consumer(
                new ConsumerStateTable(db, tableName, gBatchSize, pri),
                this, tableName));
        }
    }
}
```

- `db->getDbId() == DPU_APPL_DB` を明示的にチェックし、`zmqServer != nullptr` ならば `ZmqConsumerStateTable` を生成。
- `zmqServer == nullptr`（`orch_northbond_dash_zmq_enabled = false`）の場合は通常の `ConsumerStateTable` にフォールバックする。

## 2. ZmqConsumerStateTable コンストラクタ

`sonic-swss-common/common/zmqconsumerstatetable.cpp:20-47`

```cpp
ZmqConsumerStateTable::ZmqConsumerStateTable(...)
{
    ...
    m_zmqServer.registerMessageHandler(m_db->getDbName(), tableName, this);
}
```

- `m_db->getDbName()` は `"DPU_APPL_DB"` 文字列となる。
- `ZmqServer::registerMessageHandler("DPU_APPL_DB", tableName, this)` でメッセージハンドラを登録。
- `dbPersistence = false`（ZmqOrch がデフォルト渡し）のため、`AsyncDBUpdater` は生成されない。

## 3. ZmqServer 生成 (main.cpp:646-654)

```cpp
shared_ptr<ZmqServer> zmq_server = nullptr;
if (zmq_server_address.empty())
{
    SWSS_LOG_NOTICE("The ZMQ channel on the northbound side of orchagent has been disabled.");
}
else
{
    zmq_server = create_zmq_server(zmq_server_address);
}
```

`create_zmq_server()`（`orch_zmq_config.cpp:64-80`）:
- アドレスにポートが含まれていなければ `get_zmq_port()` が返す `ORCH_ZMQ_PORT`（8100 + NAMESPACE_ID）を付加する。
- `ZmqServer(zmq_address, vrf, true)` — 第 3 引数 `lazy=true` で bind を遅延し、全ハンドラ登録後に `zmq_server->bind()` が呼ばれる。

## 4. ZMQ サーバアドレス決定 (orchagent.sh:105-117)

`switch_type = "dpu"` のとき `orchagent.sh` が `-q` 引数を付与する経路:

| 条件 | アドレス |
|------|---------|
| `LOCALHOST_SUBTYPE = SmartSwitch` かつ `eth0-midplane UP` | `tcp://eth0-midplane` |
| `LOCALHOST_SUBTYPE = SmartSwitch` かつ midplane DOWN | `tcp://127.0.0.1` |
| それ以外 | `tcp://127.0.0.1` |

DPU は `SmartSwitchDPU` の subtype を持ちうるが、実際には `LOCALHOST_SUBTYPE` の取得元は `DEVICE_METADATA|localhost.subtype` であり、DPU 側は通常 `SmartSwitchDPU` ではなく空か別値となる。ポートは `get_zmq_port()` → `8100`（DPU は単一 namespace のため NAMESPACE_ID = ""）。

## 5. 遅延バインド (lazy bind) とメッセージロスト防止

`main.cpp:1032-1037`:
```cpp
if (zmq_server)
{
    // To prevent message loss between ZmqServer's bind operation and the creation of ZmqProducerStateTable,
    // use lazy binding and call bind() only after the handler has been registered.
    zmq_server->bind();
}
```

- `DpuOrchDaemon::init()` 内で全 DASH Orch の `ZmqConsumerStateTable` が `registerMessageHandler()` を完了した後に `bind()` を呼ぶことで、クライアント側 `ZmqProducerStateTable` が bind 前にメッセージを送ってもロストしないよう設計されている。

## 6. ZmqConsumerStateTable::execute() / drain()

`zmqorch.cpp:8-36`:
- orchdaemon の select ループが ZmqConsumerStateTable の `SelectableEvent` を検出すると `ZmqConsumer::execute()` が呼ばれる。
- `pops()` でキューからエントリを取り出し `addToSync()` → `drain()` → `ZmqOrch::doTask(*this)` の順で各 DASH Orch の `doTask()` へ転送する。

## 7. ZMQ 無効時フォールバック

`dash_zmq_server = nullptr` のとき `ZmqOrch::addConsumer()` は `ConsumerStateTable`（Redis SUBSCRIBE 方式）を生成する。この場合 DASH イベントは gNMI の `ZmqProducerStateTable` 経由ではなく、`dashd` 等が `ProducerStateTable` で Redis に書き込む経路になる。

## 結論

- `DpuOrchDaemon` の全 DASH Orch は `ZmqOrch` を継承し、`DPU_APPL_DB` に対して `ZmqConsumerStateTable` を生成して `ZmqServer` にハンドラ登録する。
- ZMQ 有効時: gNMI サービス → ZMQ wire → `ZmqServer` → `ZmqConsumerStateTable::handleReceivedData()` → `SelectableEvent` 通知 → select ループ → `doTask()`
- ZMQ 無効時: `ProducerStateTable`（Redis PUBLISH/SUBSCRIBE）→ `ConsumerStateTable` → select ループ → `doTask()` にフォールバック。
- bind はハンドラ登録後に遅延実行されるためメッセージロストが発生しない。
