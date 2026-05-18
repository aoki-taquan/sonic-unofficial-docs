# ROUTE_TABLE (APPL_DB) / fpmsyncd RouteSync handler — Phase G: 通信メカニズム調査メモ

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/route-handler.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/fpmsyncd/routesync.cpp` | コンストラクタ L154-158 | ProducerStateTable 生成・ZMQ 判定 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `fieldValueTupleVector()` L1001-1055 | ZMQ/非ZMQ フィールド送信差異 |
| `sonic-swss/fpmsyncd/fpmsyncd.cpp` | `main()` L78-143 | FPM ソケット + RESPONSE_CHANNEL 購読 |
| `sonic-swss/orchagent/routeorch.cpp` | コンストラクタ L40-44 | ZmqOrch 継承 |
| `sonic-swss/orchagent/orchdaemon.cpp` | L329-337 | RouteOrch 生成 + ZMQ Server 設定 |
| `sonic-swss/orchagent/zmqorch.cpp` | `addConsumer()` L59-68 | ConsumerStateTable / ZmqConsumerStateTable 登録 |

## 検出した通信方式

### 1. 入力 — FPM プロトコル (FRR zebra → fpmsyncd)

- FPM (Forwarding Plane Manager) は TCP ソケット上の netlink メッセージストリーム
- Redis keyspace 通知は使用しない
- `FpmLink::accept()` が接続確立までブロック (fpmsyncd.cpp:139-143)
- RTM_NEWROUTE / RTM_DELROUTE / RTM_NEWNEXTHOP 等の netlink メッセージを受信

evidence: `fpmsyncd.cpp:78-143`

### 2. APPL_DB 書き込み — ProducerStateTable / ZmqProducerStateTable

`createProducerStateTable()` (routesync.cpp:157) が `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` フラグで分岐:

- **false（デフォルト）**: `ProducerStateTable` → Lua EVALSHA でアトミック書き込み
  - `SADD ROUTE_TABLE_KEY_SET <key>` + `HSET _ROUTE_TABLE:<key> <fields>` + `PUBLISH ROUTE_TABLE_CHANNEL@0 G`
- **true**: `ZmqProducerStateTable` → ZMQ PUSH (`tcp://localhost:8100`) + APPL_DB 永続化

evidence: `routesync.cpp:154-158`

### 3. APPL_DB 消費 — ConsumerStateTable / ZmqConsumerStateTable

orchagent `RouteOrch` は `ZmqOrch` を継承し、ZMQ フラグで分岐:

- **ZMQ 無効**: `ConsumerStateTable` が `ROUTE_TABLE_CHANNEL@0` を SUBSCRIBE
- **ZMQ 有効**: `ZmqConsumerStateTable` が ZMQ PULL (`tcp://localhost:8100`) で受信

evidence: `orchdaemon.cpp:329-337`, `zmqorch.cpp:59-68`

### 4. 応答チャネル — APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL

route suppression (`suppress-fib-pending = enabled`) 有効時のみ:

```python
routeResponseChannelName = "APPL_DB_" + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL"
routeResponseChannel = NotificationConsumer(&applStateDb, routeResponseChannelName)
```

- 発行者: orchagent `ResponsePublisher::publish()`
- 購読者: fpmsyncd `RouteSync::onRouteResponse()`
- 用途: SAI 操作完了後に FRR zebra へ RTM_F_OFFLOAD 通知を送る

evidence: `fpmsyncd.cpp:78-121`, `routesync.cpp:3165-3269`

### 5. ZMQ フィールド送信差異

| パス | 空フィールド | コード |
|-----|------------|--------|
| 通常 Redis | フィールド不在（条件付き emit） | routesync.cpp:1022-1023 |
| ZMQ | 全フィールド常時送信 | routesync.cpp:1006-1017 |

evidence: `routesync.cpp:1001-1055`

## 通信フロー全体図

```
FRR (zebra) ──[FPM/netlink]──▶ fpmsyncd (RouteSync)
  │ [通常] ProducerStateTable::set/del → APPL_DB + PUBLISH ROUTE_TABLE_CHANNEL@0
  │ [ZMQ]  ZmqProducerStateTable::set/del → ZMQ PUSH + APPL_DB 永続化
  ▼
APPL_DB [ROUTE_TABLE|<prefix>]
  │ [通常] ConsumerStateTable (SUBSCRIBE ROUTE_TABLE_CHANNEL@0)
  │ [ZMQ]  ZmqConsumerStateTable (ZMQ PULL tcp://localhost:8100)
  ▼
RouteOrch::doTask()
  │ SAI sai_route_api
  │ ResponsePublisher::publish() → APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL (suppression 有効時)
  ▼
ASIC / APPL_STATE_DB ROUTE_TABLE
  │ NotificationConsumer → fpmsyncd onRouteResponse()
  ▼
FRR zebra (RTM_NEWROUTE + RTM_F_OFFLOAD)
```
