# APPL_DB LABEL_ROUTE_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: `APPL_DB` の `LABEL_ROUTE_TABLE`（MPLS incoming-label / inseg ルート）。
ソース: `sonic-net/sonic-swss` (master, HEAD 時点)。

## 1. 購読者と購読 API

`LABEL_ROUTE_TABLE` の購読者は `orchagent` 内の `RouteOrch` 単一（`doLabelTask()` ハンドラ）。

`RouteOrch` のクラス階層は `class RouteOrch : public ZmqOrch`（`routeorch.h`）であり、コンストラクタで:

```cpp
// sonic-swss/orchagent/routeorch.cpp:40-44
RouteOrch::RouteOrch(DBConnector *db, vector<table_name_with_pri_t> &tableNames, ..., swss::ZmqServer *zmqServer) :
        gRouteBulker(sai_route_api, gMaxBulkSize),
        gLabelRouteBulker(sai_mpls_api, gMaxBulkSize),
        gNextHopGroupMemberBulker(sai_next_hop_group_api, gSwitchId, gMaxBulkSize),
        ZmqOrch(db, tableNames, zmqServer),
```

`tableNames` は `orchdaemon.cpp` で以下の 2 テーブルが渡される:

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:327-331
const int routeorch_pri = 5;
vector<table_name_with_pri_t> route_tables = {
    { APP_ROUTE_TABLE_NAME,        routeorch_pri },
    { APP_LABEL_ROUTE_TABLE_NAME,  routeorch_pri }
};
```

`ZmqOrch::addConsumer` は DB ID と `zmqServer` の有無で executor を分岐させる:

```cpp
// sonic-swss/orchagent/zmqorch.cpp:59-72
void ZmqOrch::addConsumer(DBConnector *db, string tableName, int pri, ZmqServer *zmqServer, ...)
{
    if (db->getDbId() == APPL_DB || db->getDbId() == DPU_APPL_DB)
    {
        if (zmqServer != nullptr)
        {
            addExecutor(new ZmqConsumer(new ZmqConsumerStateTable(db, tableName, *zmqServer, gBatchSize, pri, dbPersistence), this, tableName, orderedQueue));
        }
        else
        {
            addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
        }
    }
```

→ `LABEL_ROUTE_TABLE` は **APPL_DB 上**で、`fpmsyncd` からの ZMQ 経路 (`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` feature) が有効なら **`swss::ZmqConsumerStateTable`**、無効なら **`swss::ConsumerStateTable`** が executor として登録される (`orchdaemon.cpp:333-337`)。デフォルトでは feature 無効＝`ConsumerStateTable`（channel ベース PUBLISH/SUBSCRIBE）。

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:333-337
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;

gRouteOrch = new RouteOrch(m_applDb, route_tables, gSwitchOrch, gNeighOrch, gIntfsOrch, vrf_orch, gFgNhgOrch, gSrv6Orch, route_zmq_sever);
```

CONFIG_DB / STATE_DB のような `SubscriberStateTable`（keyspace 通知 `__keyspace@<dbId>__:*` ベース）は **APPL_DB 経路では使われない**。書込側 `fpmsyncd` は `ProducerStateTable::set()`（`routesync.cpp` の `m_routeTable`）で `_LABEL_ROUTE_TABLE:<key>` を `HSET` し、`LABEL_ROUTE_TABLE_CHANNEL@<dbId>` に `PUBLISH "G"` を発行する。

## 2. バッチサイズ・優先度

| 項目 | 値 | 出処 |
|---|---|---|
| バッチ最大件数 | `gBatchSize` (default `DEFAULT_BATCH_SIZE = 128`) | `sonic-swss/orchagent/main.cpp:459`、`-b <n>` で上書き (`main.cpp:478`) |
| 購読優先度 | `routeorch_pri = 5` | `orchdaemon.cpp:327` |
| TTL | なし（APPL_DB エントリは永続） | — |

`gBatchSize` は `ConsumerStateTable::pops()` 1 回あたりの取得上限。同一 select サイクルで複数 `LABEL_ROUTE_TABLE|<label>` が PUBLISH された場合は単一の `m_toSync` バッチに集約され、`doLabelTask()` 内で `gLabelRouteBulker` (`mplsrouteorch.cpp:34` 付近) を介して SAI INSEG エントリへ一括反映される。

## 3. channel PUBLISH → ハンドラ呼び出しの流れ

```
FRR / zebra → kernel netlink (RTM_NEWROUTE family=MPLS)
  ↓
fpmsyncd::RouteSync::onLabelRouteMsg()
  ↓ ProducerStateTable::set(<label>, fvs)  (routesync.cpp:2728-)
APPL_DB: HSET "_LABEL_ROUTE_TABLE:<label>" <fields>
  ↓ Redis PUBLISH "LABEL_ROUTE_TABLE_CHANNEL@0" "G"
OrchDaemon main loop: m_select->select(&s, SELECT_TIMEOUT=1000ms)
  ↓ Consumer::execute() → ConsumerStateTable::pops() (max gBatchSize)
RouteOrch::doTask(consumer)  (orch routing)
  ↓ table_name == APP_LABEL_ROUTE_TABLE_NAME で分岐 (routeorch.cpp:616-618)
RouteOrch::doLabelTask(consumer)
  ↓ doLabelTask(): addLabelRoute / removeLabelRoute を bulker に登録
  ↓ gLabelRouteBulker.flush()        (mplsrouteorch.cpp:335)
  ↓ addLabelRoutePost / removeLabelRoutePost で m_syncdLabelRoutes 反映 + CRM_MPLS_INSEG inc/dec
SAI: sai_mpls_api->create_inseg_entry / set_inseg_entry_attribute / remove_inseg_entry
```

`RouteOrch::doTask` の分岐:

```cpp
// sonic-swss/orchagent/routeorch.cpp:614-619
if (table_name == APP_LABEL_ROUTE_TABLE_NAME)
{
    doLabelTask(consumer);
    return;
}
```

IPv4/IPv6 ルート（`APP_ROUTE_TABLE_NAME`）と排他的に分岐し、その後 `return;` するため、IP route 用の `m_publisher.flush()`（`routeorch.cpp:1231`、ResponsePublisher）には **到達しない**。

## 4. ResponsePublisher (APPL_STATE_DB) の有無

| 項目 | IP route (`APP_ROUTE_TABLE_NAME`) | MPLS route (`APP_LABEL_ROUTE_TABLE_NAME`) |
|---|---|---|
| `m_publisher.publish(...)` 呼出 | あり (`routeorch.cpp:3185-3201`、`publishRouteState()`) | **なし** |
| `m_publisher.flush()` 呼出 | あり (`routeorch.cpp:1231`、IP route doTask 末尾) | **なし**（MPLS は `doLabelTask` 内で publisher 参照ゼロ） |
| APPL_STATE_DB ミラー | `ROUTE_TABLE` キー固定 (`routeorch.cpp:3201` `m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, ...)`) | なし |

`mplsrouteorch.cpp` / `nhgorch.cpp` の全行 grep:

```
grep -n "m_publisher\|ResponsePublisher\|APPL_STATE_DB" orchagent/mplsrouteorch.cpp orchagent/nhgorch.cpp
→ 一致ゼロ
```

`m_publisher` は `RouteOrch` のメンバ（基底 `Orch::m_publisher`、`ResponsePublisher`）として存在するが、MPLS パスは一切利用しない。`LABEL_ROUTE_TABLE` の SET/DEL 結果を APPL_STATE_DB に書き戻す経路はなく、上位（fpmsyncd / 外部 FPM クライアント）への ack channel も存在しない。これは Phase B Side-effects（副次 DB 書込なし）と整合する。

## 5. サービス再起動トリガー

なし。`RouteOrch::doLabelTask` は同一 orchagent プロセス内ハンドラで、APPL_DB エントリの SET/DEL は SAI `inseg_entry` のライブ操作のみで反映される。systemd unit の restart / プロセス再起動は伴わない。

## 6. ZMQ 経路（feature 有効時）

`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` feature が有効なら、`ZmqConsumerStateTable` が channel PUBLISH ではなく **ZMQ TCP 経路** で `fpmsyncd` から直接 binary protobuf 形式のバッチを受信する。デフォルト（`get_feature_status(..., false)` の第二引数 `false`）では無効、`ConsumerStateTable` パス。

| 経路 | 通信媒体 | 購読クラス | デフォルト |
|---|---|---|---|
| 通常 | Redis APPL_DB + channel PUBLISH | `swss::ConsumerStateTable` | 有効 |
| ZMQ | ZMQ TCP socket（Redis をバイパス） | `swss::ZmqConsumerStateTable` | 無効 |

ZMQ 経路でも `RouteOrch::doLabelTask` ハンドラは共通。差異は executor が PUBLISH/SUBSCRIBE 経由か ZMQ recv 経由かのみ。

## 7. Evidence

- `sonic-swss/orchagent/orchdaemon.cpp:315-337` (`route_tables` 定義 / ZMQ feature 切替 / `RouteOrch` 生成)
- `sonic-swss/orchagent/routeorch.cpp:40-58` (`ZmqOrch` 継承コンストラクタ / `m_publisher.setBuffered(true)` — IP route 限定)
- `sonic-swss/orchagent/routeorch.cpp:614-619` (`doTask` で `APP_LABEL_ROUTE_TABLE_NAME` を `doLabelTask` に分岐し `return;`)
- `sonic-swss/orchagent/routeorch.cpp:3185-3201` (`publishRouteState` は `APP_ROUTE_TABLE_NAME` 固定)
- `sonic-swss/orchagent/zmqorch.cpp:41-72` (`ZmqOrch::addConsumer` の DB ID / `zmqServer` 分岐)
- `sonic-swss/orchagent/mplsrouteorch.cpp:34-417` (`doLabelTask` / `addLabelRoute` / `gLabelRouteBulker.flush()`、`m_publisher` 参照ゼロ)
- `sonic-swss/orchagent/main.cpp:59-60, 459, 478` (`DEFAULT_BATCH_SIZE = 128`、`-b` オプション、`gBatchSize`)
- `sonic-swss/fpmsyncd/routesync.cpp:2674-2732` (`onLabelRouteMsg`、`ProducerStateTable` への `set`)
- `sonic-swss-common/common/schema.h:48` (`APP_LABEL_ROUTE_TABLE_NAME = "LABEL_ROUTE_TABLE"`)
