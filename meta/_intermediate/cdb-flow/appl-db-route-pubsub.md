# appl-db-route — Phase G 通信メカニズム調査メモ

対象: APPL_DB `ROUTE_TABLE` の購読側 (`orchagent` / `RouteOrch`) と応答パブリッシュ。
ソース: `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`,
`sonic-net/sonic-swss-common` @ `158de8d3463ff4b841653f6d57190bb142b80d9c`。

## 1. RouteOrch は `ZmqOrch` を継承する

`orchagent/routeorch.h` の class 宣言と `routeorch.cpp:40-44`:

```cpp
RouteOrch::RouteOrch(DBConnector *db,
                     vector<table_name_with_pri_t> &tableNames,
                     ...,
                     swss::ZmqServer *zmqServer) :
        gRouteBulker(sai_route_api, gMaxBulkSize),
        gLabelRouteBulker(sai_mpls_api, gMaxBulkSize),
        gNextHopGroupMemberBulker(sai_next_hop_group_api, gSwitchId, gMaxBulkSize),
        ZmqOrch(db, tableNames, zmqServer),
        ...
```

つまり `RouteOrch` のコンストラクタは APPL_DB の `DBConnector*`、
`(table_name, pri)` ペアのベクタ、`ZmqServer*` を受け取り、ベースクラス
`ZmqOrch` に渡す。

`orchagent/orchdaemon.cpp:327-337`:

```cpp
const int routeorch_pri = 5;
vector<table_name_with_pri_t> route_tables = {
    { APP_ROUTE_TABLE_NAME,        routeorch_pri },
    { APP_LABEL_ROUTE_TABLE_NAME,  routeorch_pri }
};

// Enable the fpmsyncd service to send Route events to orchagent via the ZMQ channel.
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;

gRouteOrch = new RouteOrch(m_applDb, route_tables, ..., route_zmq_sever);
```

priority `5` で `APP_ROUTE_TABLE_NAME` (= `"ROUTE_TABLE"`) と
`APP_LABEL_ROUTE_TABLE_NAME` の 2 テーブルを購読。ZMQ サーバは
`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` フィーチャフラグの値で
有効/無効が切り替わる（無効時は `nullptr`）。

## 2. `ZmqOrch::addConsumer` が ZMQ / 非 ZMQ を分岐

`orchagent/zmqorch.cpp:59-72`:

```cpp
void ZmqOrch::addConsumer(DBConnector *db, string tableName, int pri,
                          ZmqServer *zmqServer, bool orderedQueue, bool dbPersistence)
{
    if (zmqServer != nullptr)
    {
        SWSS_LOG_DEBUG("ZmqConsumer initialize for: %s", tableName.c_str());
        addExecutor(new ZmqConsumer(
            new ZmqConsumerStateTable(db, tableName, *zmqServer,
                                      gBatchSize, pri, dbPersistence),
            this, tableName, orderedQueue));
    }
    else
    {
        addExecutor(new Consumer(
            new ConsumerStateTable(db, tableName, gBatchSize, pri),
            this, tableName));
    }
}
```

- ZMQ 有効: `ZmqConsumerStateTable` + `ZmqConsumer` Executor。
  fpmsyncd から ZMQ ソケット経由で `KeyOpFieldsValuesTuple` を受信。
- ZMQ 無効: 通常の `ConsumerStateTable` + `Consumer`。
  APPL_DB の Redis pub/sub (`__keyspace@*__`) で SET/DEL を受ける。

どちらも `gBatchSize` (= `orch.cpp:17` `int gBatchSize = 0;`、起動引数で上書き) を pop バッチサイズに使用。
`ZmqConsumerStateTable::DEFAULT_POP_BATCH_SIZE = 128`（`sonic-swss-common/common/zmqconsumerstatetable.h:20`）。

## 3. ConsumerStateTable による SET 合体

`routeorch.cpp:1085-1092` のコメント:

```
/* The bulker is flushed once for each loop of doTask. There can be cases when
 * the same route is set multiple times in the same doTask iteration. Those updates
 * may have been consolidated by ConsumerStateTable leading to orchagent receiving
 * only the last SET update. */
```

`ConsumerStateTable` は同一 key の連続 SET を最終値のみ配信する
（Redis Lua スクリプトで `_KEYS_` セットに登録 → 値は HSET で上書き）。
DEL は `_DELS_` に積まれて配信される。

## 4. Batch / Bulker

`RouteOrch::doTask(Consumer&)` (routeorch.cpp:605-1103) は 1 ループ内で:

1. `m_toSync` から SET/DEL を抜き出して bulker (`gRouteBulker` / `gLabelRouteBulker` / `gNextHopGroupMemberBulker`) に積む。
2. ループ末尾 (`routeorch.cpp:1117` `gRouteBulker.flush();`) で一括 SAI 呼び出し。
3. `m_publisher.flush()` (`routeorch.cpp:1231`) で APPL_STATE_DB への応答も
   1 batch で送出。コメント: *"Flush response publisher so route notifications
   reach fpmsyncd every batch."*

`gMaxBulkSize` (`orch.cpp` 由来) が bulker のチャンクサイズ。

## 5. ResponsePublisher による APPL_STATE_DB 応答

`routeorch.cpp:57-58`:

```cpp
m_publisher.setBuffered(true);
m_publisher.m_directDbWrite = true;
```

`routeorch.cpp:3185-3201` `publishRouteState()`:

```cpp
m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
```

- `setBuffered(true)`: 個々の publish はリングバッファに溜め、`flush()` で
  まとめて Redis に書き出す。
- `m_directDbWrite = true`: notification チャネルではなく APPL_STATE_DB へ
  直接 HSET / DEL を発行（書き込み主体パスを fpmsyncd と分離）。
- 呼び出し箇所: `routeorch.cpp:923 / 1050 / 1090 / 2729 / 2970`。
- DEL のとき空 `fvs` で APPL_STATE_DB からエントリを除去。

## 6. Retry キャッシュ

`routeorch.cpp:192`:

```cpp
createRetryCache(APP_ROUTE_TABLE_NAME);
```

`orch.cpp:149-152` で `m_retryCaches[APP_ROUTE_TABLE_NAME] = RetryCache(...)`
を確保。失敗 task は doTask の retry 状態に置かれ、次回イベントで
再投入される。これは pub/sub 層ではなく Orch 層のリトライ機構。

## まとめ

| 軸 | 実装 |
|----|------|
| Consumer クラス | ZMQ 有効: `ZmqConsumer` + `ZmqConsumerStateTable` / ZMQ 無効: `Consumer` + `ConsumerStateTable` |
| 切替フラグ | `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` フィーチャ (`orchdaemon.cpp:334`) |
| Priority | `5` (`routeorch_pri`) |
| Batch | `gBatchSize` (pop batch) + `gMaxBulkSize` (SAI bulker) |
| SET 合体 | `ConsumerStateTable` が同一 key の連続 SET を最終値に圧縮 |
| 応答 publish | `ResponsePublisher::publish` を APPL_STATE_DB に `setBuffered(true)` + `m_directDbWrite=true` で発行、ループ末尾で `flush()` |
| Retry | `createRetryCache(APP_ROUTE_TABLE_NAME)` |
