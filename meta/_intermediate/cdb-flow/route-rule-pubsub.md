# DASH_ROUTE_RULE_TABLE — Phase G pubsub 調査ノート

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashrouteorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/zmqorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/zmqorch.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/orchdaemon.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/main.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss-common/common/zmqconsumerstatetable.cpp` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-swss-common/common/zmqconsumerstatetable.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c

## 1. 受信側: ZMQ 受信チャネル (コントローラ → orchagent)

### ZmqOrch / ZmqConsumerStateTable

`DashRouteOrch` は `ZmqOrch` を継承 (`dashrouteorch.cpp:52`):
```cpp
DashRouteOrch::DashRouteOrch(..., ZmqServer *zmqServer)
    : ZmqOrch(db, tableName, zmqServer),
```

`ZmqOrch::addConsumer()` が `ZmqConsumerStateTable` を生成し `ZmqServer` にハンドラ登録 (`zmqorch.cpp:66`):
```cpp
addExecutor(new ZmqConsumer(
    new ZmqConsumerStateTable(db, tableName, *zmqServer, gBatchSize, pri, dbPersistence),
    this, tableName, orderedQueue));
```

`ZmqConsumerStateTable` コンストラクタで `ZmqServer` にテーブル名ベースのハンドラ登録 (`zmqconsumerstatetable.cpp:47`):
```cpp
m_zmqServer.registerMessageHandler(m_db->getDbName(), tableName, this);
```

コントローラ側は `ZmqProducerStateTable` で同じエンドポイントに protobuf エンコード済みメッセージを push する。
`ZmqServer` がメッセージを受信し、テーブル名でルーティングして `handleReceivedData()` を呼び出す。

### ZMQ エンドポイント

`orchdaemon.cpp:1329`: DASH ZMQ は `ORCH_NORTHBOND_DASH_ZMQ_ENABLED` フィーチャーフラグが true のとき有効 (デフォルト有効):
```cpp
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
    dash_zmq_server = m_zmqServer;
```

ZMQ エンドポイントアドレスは `orchagent` の `-q` オプションで指定 (`main.cpp:114`):
```
-q zmq_server_address: ZMQ server address (default disable ZMQ)
```

### dbPersistence フラグ

`ZmqOrch` のデフォルト `dbPersistence = true` のため `AsyncDBUpdater` が有効 (`zmqorch.h:34,zmqorch.cpp:66`)。
受信メッセージは `ZmqConsumerStateTable` のキューに格納後、APPL_DB にも非同期で書き込まれる。これにより ZMQ パスと Redis keyspace の両方からエントリが参照可能。

### SELECT タイムアウト

`orchdaemon.cpp:23`: `SELECT_TIMEOUT = 1000` ms でメインループが `select()` を呼ぶ。ZMQ チャネルからのメッセージは `SelectableEvent` 経由で `Selectable` を fd-notify するため、タイムアウトを待たずに即時起動する。

## 2. 送信側: APPL_STATE_DB フィードバック (orchagent → コントローラ)

`DashRouteOrch` コンストラクタ (`dashrouteorch.cpp:57`):
```cpp
dash_route_rule_result_table_ = make_unique<Table>(app_state_db, APP_DASH_ROUTE_RULE_TABLE_NAME);
```

`app_state_db` (APPL_STATE_DB, DB index 14) に `Table` オブジェクトとして接続。
SAI プログラミング完了後に `writeResultToDB()` / `removeResultFromDB()` で書き込む。

Redis Pub/Sub の観点: `Table::set()` は APPL_STATE_DB に HSET + keyspace PUBLISH を行う。
コントローラは APPL_STATE_DB の `DASH_ROUTE_RULE_TABLE:<key>` に対して keyspace notification を購読することで SAI プログラミング結果を受け取れる。

## 3. 通信フロー概略

```
コントローラ (ZmqProducerStateTable)
    │  ZMQ ipc/tcp (protobuf バイナリ)
    ▼
ZmqServer (orchagent 内)
    │  ZmqConsumerStateTable::handleReceivedData()
    ▼
DashRouteOrch::doTaskRouteRuleTable()
    │  SAI API (DASH inbound routing)
    ▼
SAI / ASIC
    │
    ▼
DashRouteOrch::writeResultToDB / removeResultFromDB
    │  APPL_STATE_DB DASH_ROUTE_RULE_TABLE (Table::set/del)
    ▼
コントローラ (keyspace notification または polling)
```

## 4. Redis keyspace notification

APPL_STATE_DB (DB 14) は通常 keyspace notification が有効。
テーブル書き込み時は `__keyspace@14__:DASH_ROUTE_RULE_TABLE:<key>` チャネルに `set` / `del` イベントが PUBLISH される。
コントローラは PSUBSCRIBE `__keyspace@14__:DASH_ROUTE_RULE_TABLE\|*` で購読できる。

## 5. Redis keyspace notification (受信側 orchagent)

DashRouteOrch は ZMQ 受信のみで、CONFIG_DB / STATE_DB の keyspace notification は購読しない。
`ZmqConsumerStateTable` が `ZmqServer` ハンドラとして登録され、fd ベースの `SelectableEvent` で orchagent メインループに通知する。

## 証跡

- `zmqconsumerstatetable.cpp:47` — registerMessageHandler
- `zmqorch.cpp:66` — ZmqConsumerStateTable 生成
- `dashrouteorch.cpp:49-58` — コンストラクタ / result table 初期化
- `orchdaemon.cpp:1328-1368` — ZmqServer 有効化 + DashRouteOrch 生成
- `main.cpp:114,647-654` — ZMQ エンドポイント指定
