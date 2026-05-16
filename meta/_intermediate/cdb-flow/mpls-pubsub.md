# MPLS LABEL_ROUTE_TABLE — 通信メカニズム (Phase G) 解析メモ

対象ページ: `docs/reference/config-db/appl-mpls-route.md`
ソース: `sonic-net/sonic-swss` (master, HEAD 時点)
解析ファイル: `orchagent/mplsrouteorch.cpp`, `orchagent/orchdaemon.cpp`

> 詳細解析は `meta/_intermediate/cdb-flow/appl-mpls-route-pubsub.md` に収録済み。
> 本ファイルは slug `mpls` 向けの Phase G サマリ。

---

## 1. APPL_DB Consumer 登録経路

`orchdaemon.cpp` が `RouteOrch` に渡す `route_tables` に `APP_LABEL_ROUTE_TABLE_NAME` を含める:

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:327-331
const int routeorch_pri = 5;
vector<table_name_with_pri_t> route_tables = {
    { APP_ROUTE_TABLE_NAME,        routeorch_pri },
    { APP_LABEL_ROUTE_TABLE_NAME,  routeorch_pri }
};
```

`RouteOrch : ZmqOrch` のコンストラクタが `ZmqOrch::addConsumer` を通じて executor を登録する。
`APPL_DB` テーブルであるため DB ID 分岐により `ConsumerStateTable`（または ZMQ 有効時は
`ZmqConsumerStateTable`）が選択される:

```cpp
// sonic-swss/orchagent/zmqorch.cpp:59-72
if (db->getDbId() == APPL_DB || db->getDbId() == DPU_APPL_DB)
{
    if (zmqServer != nullptr)
        addExecutor(new ZmqConsumer(...));
    else
        addExecutor(new Consumer(new ConsumerStateTable(...), this, tableName));
}
```

デフォルト (`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` = false) では `ConsumerStateTable` が使われ、
Redis PUBLISH/SUBSCRIBE チャネルで通知を受信する。

---

## 2. SAI mpls_api 呼び出し経路

`mplsrouteorch.cpp` の `doLabelTask()` が `gLabelRouteBulker`（`EntityBulker<sai_mpls_api_t>`）
経由で SAI MPLS API を一括発行する:

```
ConsumerStateTable::pops()
  → RouteOrch::doTask()
      if (table_name == APP_LABEL_ROUTE_TABLE_NAME) → doLabelTask(consumer); return;
  → doLabelTask():
      addLabelRoute() / removeLabelRoute()
        → gLabelRouteBulker.create_entry / set_entry_attribute / remove_entry
      gLabelRouteBulker.flush()          // mplsrouteorch.cpp:335
        → sai_mpls_api->create_inseg_entry
        → sai_mpls_api->set_inseg_entry_attribute
        → sai_mpls_api->remove_inseg_entry
      addLabelRoutePost / removeLabelRoutePost
        → m_syncdLabelRoutes 更新 + CRM MPLS inseg カウント増減
```

IP ルート (`APP_ROUTE_TABLE_NAME`) とは `doTask` 内で早期 `return` で排他的に分岐する:

```cpp
// sonic-swss/orchagent/routeorch.cpp:614-619
if (table_name == APP_LABEL_ROUTE_TABLE_NAME)
{
    doLabelTask(consumer);
    return;
}
```

この `return` により IP ルート用の `m_publisher.flush()` (ResponsePublisher) には到達しない。

---

## 3. fpmsyncd 書込経路

`fpmsyncd::RouteSync::onLabelRouteMsg()` がカーネル netlink `RTM_NEWROUTE` (AF=MPLS) を
受信し `ProducerStateTable::set()` で APPL_DB に書き込む:

```
FRR / zebra → kernel netlink (RTM_NEWROUTE, family=AF_MPLS)
  ↓
fpmsyncd::RouteSync::onLabelRouteMsg()  (routesync.cpp:2674-)
  ↓ ProducerStateTable::set(<label>, fvs)
APPL_DB: HSET "_LABEL_ROUTE_TABLE:<label>" <fields>
  ↓ Redis PUBLISH "LABEL_ROUTE_TABLE_CHANNEL@0" "G"
OrchDaemon main loop: m_select->select(&s, SELECT_TIMEOUT=1000ms)
  ↓ Consumer::execute() → ConsumerStateTable::pops()
RouteOrch::doLabelTask()
  ↓ gLabelRouteBulker.flush()
SAI: sai_mpls_api->create_inseg_entry / set / remove
ASIC
```

---

## 4. ResponsePublisher / APPL_STATE_DB の有無

`mplsrouteorch.cpp` / `nhgorch.cpp` を全行 grep した結果、`m_publisher` / `ResponsePublisher`
/ `APPL_STATE_DB` への参照は **0 件**。

- `LABEL_ROUTE_TABLE` の SET/DEL 結果は APPL_STATE_DB にミラーされない
- fpmsyncd への ack channel も存在しない
- Phase B (Side-effects) と完全に整合

---

## 5. バッチサイズ・優先度

| 項目 | 値 | 出処 |
|---|---|---|
| バッチ最大件数 | `gBatchSize`（デフォルト `DEFAULT_BATCH_SIZE = 128`） | `orchagent/main.cpp:459`, `-b` で上書き可 |
| 購読優先度 | `routeorch_pri = 5` | `orchdaemon.cpp:327` |
| select タイムアウト | `SELECT_TIMEOUT = 1000 ms` | `orchdaemon.cpp:22-23` |

---

## 6. Evidence

- `sonic-swss/orchagent/orchdaemon.cpp:327-337` — `route_tables` 定義、ZMQ feature 切替、`RouteOrch` 生成
- `sonic-swss/orchagent/mplsrouteorch.cpp:20-335` — `doLabelTask` / `gLabelRouteBulker.flush()` / `m_publisher` 参照 0 件
- `sonic-swss/orchagent/routeorch.cpp:614-619` — `doTask` での `APP_LABEL_ROUTE_TABLE_NAME` → `doLabelTask` 分岐・早期 return
- `sonic-swss/orchagent/zmqorch.cpp:59-72` — `ZmqOrch::addConsumer` の DB ID / `zmqServer` 分岐
- `sonic-swss/orchagent/main.cpp:59-60, 459, 478` — `DEFAULT_BATCH_SIZE = 128`, `-b` オプション
- `sonic-swss/fpmsyncd/routesync.cpp:2674-2732` — `onLabelRouteMsg` / `ProducerStateTable::set`
- `sonic-swss-common/common/schema.h:48` — `APP_LABEL_ROUTE_TABLE_NAME = "LABEL_ROUTE_TABLE"`
