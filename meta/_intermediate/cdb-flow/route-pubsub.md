# ROUTE_TABLE (APPL_DB) — 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-15
対象ソース:
- `sonic-swss/fpmsyncd/routesync.h` (rev 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/fpmsyncd/routesync.cpp` (rev 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/routeorch.cpp` (rev 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/zmqorch.h` / `zmqorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/lib/orch_zmq_config.h` / `orch_zmq_config.cpp`
- `sonic-swss-common/common/schema.h` (rev 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-swss-common/common/zmqserver.h`

---

## 1. Producer/Consumer ペア（通常 Redis パス）

### fpmsyncd → APPL_DB (ProducerStateTable または ZmqProducerStateTable)

`RouteSync` コンストラクタ (`routesync.cpp:154-158`) で `m_routeTable` を初期化する:

```cpp
m_zmqClient(create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)),
m_routeTable(createProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, true, m_zmqClient)),
```

- `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が **false（デフォルト）** の場合: `ProducerStateTable` を使用
  - Lua EVALSHA で原子実行: `SADD ROUTE_TABLE_KEY_SET <key>` + `HSET _ROUTE_TABLE:<key> <fields>` + `PUBLISH ROUTE_TABLE_CHANNEL@0 G`
- `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が **true** の場合: `ZmqProducerStateTable` を使用
  - ZMQ TCP transport で orchagent に直接送信（Redis 書き込みをバイパスするのではなく、ZMQ ソケット経由で送信 + APPL_DB に永続化）

### APPL_DB → orchagent RouteOrch (ConsumerStateTable または ZmqConsumerStateTable)

orchagent (`orchdaemon.cpp:334-337`) にて:

```cpp
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;
gRouteOrch = new RouteOrch(m_applDb, route_tables, gSwitchOrch, gNeighOrch, gIntfsOrch,
                            vrf_orch, gFgNhgOrch, gSrv6Orch, route_zmq_sever);
```

`RouteOrch` は `ZmqOrch` を継承し (`routeorch.cpp:40-44`):

```cpp
RouteOrch::RouteOrch(..., swss::ZmqServer *zmqServer) :
    ZmqOrch(db, tableNames, zmqServer),
```

- **通常 Redis パス（ZMQ 無効）**: `ConsumerStateTable` が `ROUTE_TABLE_CHANNEL@0` を SUBSCRIBE し `consumer_state_table_pops.lua` でバッチ取得
- **ZMQ パス（ZMQ 有効）**: `ZmqConsumerStateTable` が ZMQ ソケット (`tcp://localhost:8100`) で受信し `ZmqConsumer::execute()` で処理

---

## 2. ZMQ トランスポート詳細

| 項目 | 値 |
|------|----|
| フィーチャーフラグ | `DEVICE_METADATA\|localhost` の `orch_northbond_route_zmq_enabled` フィールド |
| デフォルト | `false` (Redis ProducerStateTable パス) |
| ZMQ エンドポイント | `tcp://localhost:8100` (グローバル namespace)、namespace ごとに `8100+nsid+1` |
| Transport | ZeroMQ PUSH/PULL (TCP) |
| 永続化 | ZMQ パスでも APPL_DB (Redis) に書き込む (`dbPersistence=true`) |
| ZmqConsumerStateTable | `zmqorch.cpp:66` で `addExecutor(new ZmqConsumer(new ZmqConsumerStateTable(...)))` |

---

## 3. keyspace notification（ROUTE_TABLE は CONFIG_DB 不在）

`ROUTE_TABLE` は **APPL_DB** テーブルのため、CONFIG_DB keyspace notification は使用しない。`fpmsyncd` が FRR の FPM (Forwarding Plane Manager) プロトコルで受け取った netlink メッセージを直接 APPL_DB に書き込む構成。

FPM プロトコルフロー:
```
FRR zebra --[FPM/netlink socket]--> fpmsyncd --[ProducerStateTable/ZmqProducerStateTable]--> APPL_DB ROUTE_TABLE
```

---

## 4. ROUTE_TABLE に書き込まない経路フィルタ

`routesync.cpp` が APPL_DB に書き込まずにスキップする経路:

| 条件 | コード行 | 動作 |
|------|---------|------|
| 管理 VRF (`mgmt` プレフィックス) | `routesync.cpp:2125` | `memcmp(vrf, MGMT_VRF_PREFIX, ...)` で検出してスキップ |
| eth0 / docker0 / eth1-midplane nexthop | `routesync.cpp:2250,2268,2408,2566` | DEL メッセージに変換して送信（FRR バージョン 7.2→7.5 の挙動変化対策） |
| EVPN Multipath SRv6 | routesync.cpp 内コメント | サイレントスキップ |

---

## 5. RouteOrch 側の Consumer 登録

`orchdaemon.cpp:329-337`:

```cpp
vector<table_name_with_pri_t> route_tables = {
    { APP_ROUTE_TABLE_NAME,        routeorch_pri },
    { APP_LABEL_ROUTE_TABLE_NAME,  routeorch_pri },
    ...
};
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;
gRouteOrch = new RouteOrch(m_applDb, route_tables, ..., route_zmq_sever);
```

`ZmqOrch::addConsumer()` (`zmqorch.cpp:59-68`):

```cpp
void ZmqOrch::addConsumer(DBConnector *db, string tableName, int pri, ZmqServer *zmqServer, ...) {
    if (zmqServer) {
        addExecutor(new ZmqConsumer(new ZmqConsumerStateTable(db, tableName, *zmqServer, ...), ...));
    } else {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, ...), ...));
    }
}
```

---

## 6. STATE_DB 書き込み

RouteOrch は STATE_DB に **デフォルト経路ステータス** のみ書き込む:

```cpp
// routeorch.cpp:127
m_stateDefaultRouteTb = unique_ptr<swss::Table>(new Table(m_stateDb.get(), STATE_ROUTE_TABLE_NAME));
// routeorch.cpp:294
m_stateDefaultRouteTb->set(ip, tuples);
```

| テーブル | 定数 | TTL |
|---------|------|-----|
| `STATE_DB:ROUTE_TABLE` | `STATE_ROUTE_TABLE_NAME` | なし (DEFAULT_DB_TTL = -1) |

個別経路エントリのステータスは STATE_DB には書き込まれない（デフォルト経路の有無のみ）。

---

## 7. ZMQ フィールド送信の差異

`routesync.cpp:1003-1007`:

```cpp
// If Northbound ZMQ is enabled, simply send all the fields even if the value is
// empty. The duplication of code between ZMQ and non-ZMQ is deliberate. This way
// for the ZMQ case we can avoid an if check for every field attribute.
```

- **通常 Redis パス**: 空文字列フィールドは APPL_DB に書き込まない（フィールド不在 = デフォルト値）
- **ZMQ パス**: 全フィールドを常に送信（フィールド不在が発生しない）

---

## 8. 通信フロー全体図

```
FRR (zebra) --[FPM/netlink]--> fpmsyncd (RouteSync)
  ↓ [通常パス] ProducerStateTable::set/del
  ↓   EVALSHA: SADD ROUTE_TABLE_KEY_SET + HSET _ROUTE_TABLE:<key> + PUBLISH ROUTE_TABLE_CHANNEL@0 G
  ↓ [ZMQ パス] ZmqProducerStateTable::set/del
  ↓   ZMQ PUSH → tcp://localhost:8100 + APPL_DB への永続化

APPL_DB[ROUTE_TABLE|<prefix>]
  ↓ [通常] ConsumerStateTable (SUBSCRIBE ROUTE_TABLE_CHANNEL@0 → pops.lua)
  ↓ [ZMQ]  ZmqConsumerStateTable (ZMQ PULL ← tcp://localhost:8100)
RouteOrch::doTask(ConsumerBase&)
  ↓ SAI sai_route_api (create/remove/set route entry)
ASIC

STATE_DB[ROUTE_TABLE|<default-route-prefix>]
  ← RouteOrch::set() (デフォルト経路の有無のみ、TTL なし)
```
