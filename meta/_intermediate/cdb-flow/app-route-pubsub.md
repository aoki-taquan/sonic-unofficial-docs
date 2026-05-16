# app-route — Phase G 通信メカニズム (ConsumerStateTable / ZmqConsumerStateTable / ResponsePublisher)

対象ページ: `docs/reference/config-db/app-route.md`
対象テーブル: `APPL_DB:ROUTE_TABLE` (`APP_ROUTE_TABLE_NAME`)

調査日: 2026-05-15
Evidence:
- `sonic-swss/orchagent/routeorch.cpp:40-70,57-58,3185-3201`
- `sonic-swss/orchagent/orchdaemon.cpp:84,327-337`
- `sonic-swss/orchagent/zmqorch.cpp` (全文)
- `sonic-swss/orchagent/orch.h:382` (`ResponsePublisher m_publisher{"APPL_STATE_DB"}`)
- `sonic-swss/orchagent/response_publisher.cpp:67-204`
- `sonic-swss/fpmsyncd/routesync.cpp:156-162` (`m_routeTable` 生成)
- `sonic-swss/lib/orch_zmq_config.cpp:117-145` (`createProducerStateTable`)

---

## 概要

`APPL_DB:ROUTE_TABLE` は CONFIG_DB ではなく **APPL_DB (db 0)** 上にある。よって CONFIG_DB の keyspace PSUBSCRIBE (`SubscriberStateTable`) は使われない。書き込み側 `fpmsyncd` は `ProducerStateTable` (LPUSH + PUBLISH モデル) 経由で書き、購読側 `routeorch` は `ZmqOrch` 基底クラスを使い、**ZMQ 無効時は通常の `ConsumerStateTable` (channel = `<TABLE_NAME>_CHANNEL`)**、**ZMQ 有効時は `ZmqConsumerStateTable` (TCP socket 経由)** に切替わる。応答パスは `ResponsePublisher` を介して APPL_STATE_DB へ書き込みつつ、APPL_DB の `<TABLE>_RESPONSE_CHANNEL` に NotificationProducer で結果を返す（条件付き）。

| 役割 | クラス | 経路 | 根拠 |
|---|---|---|---|
| 購読 (ZMQ 無効) | `swss::ConsumerStateTable` | Redis LPOP + `<TABLE>_CHANNEL` PUBLISH | `zmqorch.cpp:62-73` (`zmqServer == nullptr` 枝) |
| 購読 (ZMQ 有効) | `swss::ZmqConsumerStateTable` | TCP ZMQ socket (`tcp://127.0.0.1:8100` 既定) | `zmqorch.cpp:62-68` (`zmqServer != nullptr` 枝) |
| 応答 publish | `ResponsePublisher` (`APPL_STATE_DB`) | NotificationProducer ＋ APPL_STATE_DB 直接 HSET | `orch.h:382`, `response_publisher.cpp:96-134` |

`NotificationConsumer` 経路は本テーブルでは不使用。

---

## 1. RouteOrch は `ZmqOrch` 派生

`RouteOrch` のコンストラクタ初期化リスト (routeorch.cpp:40-55):

```cpp
RouteOrch::RouteOrch(DBConnector *db, vector<table_name_with_pri_t> &tableNames, ...,
                     swss::ZmqServer *zmqServer) :
        gRouteBulker(sai_route_api, gMaxBulkSize),
        gLabelRouteBulker(sai_mpls_api, gMaxBulkSize),
        gNextHopGroupMemberBulker(sai_next_hop_group_api, gSwitchId, gMaxBulkSize),
        ZmqOrch(db, tableNames, zmqServer),
        ...
{
    m_publisher.setBuffered(true);
    m_publisher.m_directDbWrite = true;
    ...
}
```

`ZmqOrch::ZmqOrch(...)` は受け取った `tableNames`（`APP_ROUTE_TABLE_NAME` 優先度 5 と `APP_LABEL_ROUTE_TABLE_NAME` 優先度 5、orchdaemon.cpp:327-330）と `zmqServer` を順に `addConsumer()` する。

## 2. `ZmqOrch::addConsumer` の DB / ZMQ 分岐

`zmqorch.cpp:61-79`:

```cpp
void ZmqOrch::addConsumer(DBConnector *db, string tableName, int pri,
                          ZmqServer *zmqServer, bool orderedQueue, bool dbPersistence)
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
    else
    {
        SWSS_LOG_WARN("ZmqOrch does not support create consumer for db: %d, table: %s", ...);
    }
}
```

`routeorch` は `m_applDb` (DB 0 = APPL_DB) を渡されるので **APPL_DB 経路**に入る。`zmqServer` の有無で 2 系統に分岐:

| 条件 | Consumer | 通知プリミティブ |
|---|---|---|
| `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED=false` (既定) → `zmqServer = nullptr` (orchdaemon.cpp:334-335) | `swss::ConsumerStateTable` | Redis `<TABLE>_CHANNEL` PUBLISH |
| `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED=true` → `zmqServer = m_zmqServer` | `swss::ZmqConsumerStateTable` | ZMQ TCP socket |

`orchdaemon.cpp:334-337`:

```cpp
auto enable_route_zmq = get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false);
auto route_zmq_sever = enable_route_zmq ? m_zmqServer : nullptr;
gRouteOrch = new RouteOrch(m_applDb, route_tables, ..., route_zmq_sever);
```

ZMQ 有効時のみ書き込み側 fpmsyncd も `ZmqProducerStateTable` に切り替わり (`lib/orch_zmq_config.cpp:117-145`)、Redis を介さず orchagent との間で **直接 ZMQ TCP** で SET/DEL ペイロードを送る (route が大量に流れたときの Redis LIST 飽和回避が動機)。

## 3. ZMQ 無効時の Redis チャネル

`ConsumerStateTable` (sonic-swss-common) は ProducerStateTable と対になる:

- Producer 側 (`fpmsyncd::m_routeTable->set()`): Redis LUA で `<TABLE>:<key>` を `_TEMP_TABLE` の hash に push → `<TABLE>_KEY_SET` (Redis SET) に key 追加 → `PUBLISH <TABLE>_CHANNEL G`。
- Consumer 側 (`ConsumerStateTable`): `SUBSCRIBE <TABLE>_CHANNEL` で受信し `pops()` の LUA で `<TABLE>_KEY_SET` から SPOP しつつ `<TABLE>:<key>` を HGETALL → `Consumer::execute()` → `RouteOrch::doTask(Consumer&)`。

つまり keyspace 通知ではなく **明示的な `<TABLE>_CHANNEL` PUBLISH**（チャネル名は ProducerStateTable がハードコード）。本テーブルでの実チャネル名:

| チャネル | 用途 |
|---|---|
| `ROUTE_TABLE_CHANNEL` | `APP_ROUTE_TABLE_NAME` 用 PUBLISH (sonic-swss-common `ProducerStateTable::DEFAULT_CHANNEL_NAME = <table>_CHANNEL`) |
| `LABEL_ROUTE_TABLE_CHANNEL` | `APP_LABEL_ROUTE_TABLE_NAME` 用 (同一 RouteOrch が消費) |

書き込み元 `fpmsyncd::RouteSync` (`routesync.cpp:156`):

```cpp
m_routeTable(createProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, /*buffered=*/true, m_zmqClient)),
```

`createProducerStateTable` (lib/orch_zmq_config.cpp:117-145) は:

- `zmqClient != nullptr` → `ZmqProducerStateTable` (ZMQ tcp 経路)
- `zmqClient == nullptr` → 通常 `ProducerStateTable` (Redis 経路)

を返す。`m_zmqClient` は `create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)` で生成され、ZMQ 有効時のみ非 null となるため orchagent 側と必ず歩調が合う。

## 4. ZMQ 有効時の TCP 経路

ZMQ 経路では Redis の PUBSUB / LIST を経由せず、`ZmqConsumerStateTable` が `ZmqServer` を介して PAIR socket で受信する。`ZmqServer` は `OrchDaemon` で `tcp://127.0.0.1:8100` 既定 (zmqserver.cpp 既定値) に bind。利点は (a) Redis を経由しないので大規模 BGP コンバージェンス時の LPUSH/SPOP オーバヘッドが消える、(b) ペイロードがそのまま渡るため fvVector の全フィールド (空文字列含む) を維持できる。**ZMQ 有効時は fpmsyncd が全フィールドを常に送信** (空文字列 default も省略しない) する挙動と一致する (Phase D の `<!-- defaults -->` で言及済み)。

## 5. 応答パス: `ResponsePublisher` (APPL_STATE_DB)

`Orch` 基底クラスで `m_publisher` が宣言される (orch.h:382):

```cpp
ResponsePublisher m_publisher{"APPL_STATE_DB"};
```

これは `APPL_STATE_DB` (db 14) への `DBConnector` を持つ。RouteOrch ctor で:

```cpp
m_publisher.setBuffered(true);
m_publisher.m_directDbWrite = true;
```

を設定。`directDbWrite=true` のため `writeToDBInternal` (response_publisher.cpp:172-184) は `applStateTable.set(key, attrs)` を**直書き**（`get`→差分→`del` の通常パスをスキップ）。

`RouteOrch::publishRouteState(ctx, status)` (routeorch.cpp:3185-3201):

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }
    const bool replace = false;
    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

呼び出し箇所: `routeorch.cpp:923, 1050, 1090, 2729, 2970` (bulk 完了後 + 各 ECMP 経路で 1 回ずつ)。`m_publisher.flush()` が `doTask` ループ末尾の `routeorch.cpp:1231` で叩かれる。

### publish 内部 (response_publisher.cpp:96-134)

```cpp
std::string response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL";
if (m_enable_db_write_and_notify) {
    if (m_zmqServer != nullptr) {
        responses[table].push_back(swss::KeyOpFieldsValuesTuple{key, SET_COMMAND, intent_attrs_zmq_copy});
    } else {
        swss::NotificationProducer notificationProducer{
            m_ntf_pipe.get(), response_channel, m_buffered};
        notificationProducer.send(status.codeStr(), key, intent_attrs_copy);
    }
}
```

`m_enable_db_write_and_notify` は既定で **false** (response_publisher.h で初期化、有効化は P4Orch 等が個別に行う)。RouteOrch ではこのフラグを立てていない。よって RouteOrch 経由では **APPL_DB の `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` への NotificationProducer 通知は走らない**。`writeToDB` 側だけが動き、APPL_STATE_DB に `ROUTE_TABLE|<key>` を書く / 消す。

| publish 引数 | RouteOrch での値 |
|---|---|
| `table` | `APP_ROUTE_TABLE_NAME` (`"ROUTE_TABLE"`) |
| `key` | `<vrf>:<prefix>` または `<prefix>` (orchagent 内のフルキー) |
| `intent_attrs` | SET 時: `[("protocol", ctx.protocol)]`, DEL 時: `[]` |
| `status` | bulk 結果の `ReturnCode` (SAI 成功時 ok、失敗時 SAI status code) |
| `replace` | `false` |
| `state_attrs` (内部派生) | `status.ok() == true` のとき `intent_attrs` と同一、それ以外は空 (response_publisher.cpp:136-150) |

結果として APPL_STATE_DB に書かれる KV:

| 操作 | APPL_STATE_DB エントリ |
|---|---|
| 成功 SET | `HSET ROUTE_TABLE\|<key> protocol <value>` |
| 成功 DEL | `DEL ROUTE_TABLE\|<key>` (empty fvs + directDbWrite=true は `applStateTable.del`) |
| 失敗 SET/DEL | (`state_attrs` 空のため) `applStateTable.set(key, {NULL:NULL})` または書込スキップ |

詳細は本ページ既存の `<!-- side-effects -->` (Phase F) と一致。

## 6. 書き込み元の通知粒度

`fpmsyncd::RouteSync` は netlink からのバッチを `m_routeTable` に逐次 `set()`/`del()` する。`ProducerStateTable` は内部で `_TEMP` hash に積み、`PUBLISH <TABLE>_CHANNEL G` を 1 メッセージで投げる (Redis LUA `producer_state_set`)。orchagent の `ConsumerStateTable::pops()` は SPOP で keyset を消費しつつ HGETALL するため、**1 publish に対して複数 key をまとめて pop** することがある (バッチサイズ `gBatchSize` 既定 128)。

ZMQ 有効時の `ZmqProducerStateTable` は KOFV ペイロードをそのまま PAIR socket に送り、ZmqServer 側 `ZmqConsumerStateTable` がキューする (`dbPersistence=true` の場合は同時に Redis にも書く)。

## 7. 起動時スナップショット

- ZMQ 無効: `ConsumerStateTable` ctor は psubscribe 直後に存在する全エントリを `<TABLE>_KEY_SET` から SPOP する。fpmsyncd が起動前から残っている `ROUTE_TABLE|*` (warm restart 残存) はそのまま流れる。
- warm restart: `routesync.cpp:162` の `m_warmStartHelper` がスナップショット同期を制御。`WarmStartHelper` は `bgp` コンポーネント名で `<TABLE>_TMP` 経由の二段階適用 (詳細は Phase D 失敗・retry 参照)。

## 8. 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 (ZMQ off) | Redis `<TABLE>_CHANNEL` PUBLISH (keyspace 通知ではない、ProducerStateTable channel) |
| 通知種別 (ZMQ on) | ZMQ tcp socket (`tcp://127.0.0.1:8100` 既定) |
| 切替 feature flag | `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` (CONFIG_DB `FEATURE` テーブル、既定 false) |
| Consumer クラス | `ConsumerStateTable` または `ZmqConsumerStateTable` (`ZmqOrch::addConsumer` 分岐) |
| Producer クラス | `ProducerStateTable` または `ZmqProducerStateTable` (`createProducerStateTable` 分岐) |
| SubscriberStateTable | **不使用** (APPL_DB は CONFIG_DB と違い ProducerStateTable channel 方式) |
| NotificationConsumer | **不使用** (read path) |
| 応答 publish | `ResponsePublisher m_publisher{"APPL_STATE_DB"}` (orch.h:382) を `m_publisher.publish(APP_ROUTE_TABLE_NAME, key, fvs, status, replace=false)` で叩く |
| Notification 応答 channel | `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` (RouteOrch では `m_enable_db_write_and_notify=false` のため**送信されない**、DB 書込のみ) |
| `directDbWrite` | `true` (routeorch.cpp:58) → `applStateTable.set/del` 直接書込 |
| `setBuffered` | `true` (routeorch.cpp:57) → pipeline 経由 |
| flush タイミング | `RouteOrch::doTask` の bulker flush 後 `m_publisher.flush()` (routeorch.cpp:1231) |
| 優先度 (pri) | `routeorch_pri = 5` (orchdaemon.cpp:327) — 他 orch より高い |
| batch サイズ | `gBatchSize` (orchagent 既定 128) |
| 同期実行 | orchagent 単一 `Select` ループ |
| TTL | APPL_DB `ROUTE_TABLE` に TTL なし。APPL_STATE_DB 側にも TTL なし (永続) |

## 9. シーケンス図 (テキスト)

ZMQ 無効 (既定):

```
zebra (FRR)
  │  FPM netlink (RTM_NEWROUTE)
  ▼
fpmsyncd::RouteSync::onRouteMsg()
  │  m_routeTable->set("<prefix>", fvVector)
  ▼
swss::ProducerStateTable (APP_ROUTE_TABLE_NAME)
  │  Redis LUA: HSET _TEMP_ROUTE_TABLE:<key>, SADD ROUTE_TABLE_KEY_SET <key>
  │  PUBLISH ROUTE_TABLE_CHANNEL "G"
  ▼
Redis APPL_DB (db 0)
  │
  │  SUBSCRIBE ROUTE_TABLE_CHANNEL
  ▼
orchagent Select ループ
  │  ConsumerStateTable.pops() → SPOP + HGETALL
  ▼
RouteOrch::doTask(Consumer&)
  ├─ bulk SAI route_entry create/set/remove
  ├─ publishRouteState(ctx, status)
  │     └─ m_publisher.publish("ROUTE_TABLE", key, [(protocol,X)], status, false)
  │             └─ writeToDBInternal: APPL_STATE_DB.HSET ROUTE_TABLE|<key> protocol X
  ├─ updateDefRouteState("0.0.0.0/0" / "::/0") → STATE_DB
  └─ gCrmOrch->incCrmResUsedCounter(CRM_IPV4_ROUTE | CRM_IPV6_ROUTE)
```

ZMQ 有効 (`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED=true`):

```
fpmsyncd::RouteSync::onRouteMsg()
  │  m_routeTable (= ZmqProducerStateTable)->set(...)
  ▼
ZMQ PAIR tcp://127.0.0.1:8100
  ▼
ZmqServer (orchagent)
  ▼
ZmqConsumerStateTable (registered by ZmqOrch::addConsumer)
  │  ZmqConsumer::execute() → addToSync(entries)
  ▼
RouteOrch::doTask(ConsumerBase&) (zmqorch.cpp:81-85: 同じ仮想 doTask へ流す)
  └─ 以下同上
```

## 10. 競合 / レース

| 競合 | 影響 | 対策 |
|---|---|---|
| 連続 SET の合体 (ProducerStateTable channel) | 同 key への高頻度 SET は ConsumerStateTable 側で `last write wins` (HGETALL で再取得) | routeorch.cpp:1089 のコメントが言及。`publishRouteState` 自体は最終状態に対して走るので問題なし |
| ZMQ 有効時の fpmsyncd / orchagent 起動順 | orchagent (ZmqServer) が先に bind していないと fpmsyncd の ZmqClient が接続失敗 → リトライ | swss-common ZmqClient が再接続ロジックあり |
| bulk flush 中の `m_publisher.flush()` 漏れ | flush 前にプロセス停止すると APPL_STATE_DB に書かれない | 次回 cold start で `directDbWrite=true` により再書込 |
| `m_enable_db_write_and_notify=false` のため通知 channel が無い | P4Orch 等と違い RouteOrch は `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` を rendre しない。GenericConfigUpdater / sonic-mgmt-common は本 channel に依存しない | 設計通り |

## 11. 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/orchagent/orchdaemon.cpp` | 327-337 | `routeorch_pri=5`、`route_tables` 構築、`enable_route_zmq` feature 判定、`RouteOrch` 生成 |
| `sonic-swss/orchagent/routeorch.cpp` | 40-58 | `RouteOrch::RouteOrch` — `ZmqOrch(db, tableNames, zmqServer)` 派生、`m_publisher.setBuffered(true)` / `m_directDbWrite=true` |
| `sonic-swss/orchagent/routeorch.cpp` | 923, 1050, 1090, 2729, 2970 | `publishRouteState(ctx)` 呼び出しサイト |
| `sonic-swss/orchagent/routeorch.cpp` | 1231 | `m_publisher.flush()` (bulk doTask 末尾) |
| `sonic-swss/orchagent/routeorch.cpp` | 3185-3201 | `publishRouteState` 実装 |
| `sonic-swss/orchagent/zmqorch.cpp` | 41-79 | `ZmqOrch::ZmqOrch` / `ZmqOrch::addConsumer` APPL_DB 分岐 |
| `sonic-swss/orchagent/zmqorch.cpp` | 8-32 | `ZmqConsumer::execute` (`ZmqConsumerStateTable::pops` → `addToSync`) |
| `sonic-swss/orchagent/orch.h` | 382 | `ResponsePublisher m_publisher{"APPL_STATE_DB"}` |
| `sonic-swss/orchagent/response_publisher.cpp` | 67-80 | ctor (RedisPipeline x2, 書込スレッド任意) |
| `sonic-swss/orchagent/response_publisher.cpp` | 96-134 | `publish` 5 引数版 — `APPL_DB_<table>_RESPONSE_CHANNEL` NotificationProducer (`m_enable_db_write_and_notify` ガード) |
| `sonic-swss/orchagent/response_publisher.cpp` | 136-150 | `publish` 4 引数版 — status.ok() で `state_attrs = intent_attrs` |
| `sonic-swss/orchagent/response_publisher.cpp` | 172-204 | `writeToDBInternal` — `directDbWrite=true` の直書きパス |
| `sonic-swss/fpmsyncd/routesync.cpp` | 156-162 | `m_routeTable = createProducerStateTable(pipeline, APP_ROUTE_TABLE_NAME, true, m_zmqClient)` |
| `sonic-swss/lib/orch_zmq_config.cpp` | 117-145 | `createProducerStateTable` の ZMQ 分岐 |
| `sonic-swss/lib/orch_zmq_config.cpp` | 106-115 | `create_local_zmq_client` (feature true で `tcp://127.0.0.1:8100` 接続) |
