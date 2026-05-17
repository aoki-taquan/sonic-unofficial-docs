# DASH_ROUTING_* テーブル — Phase G: Pub/Sub・通知経路 (pubsub)

調査対象: `orchagent/dash/dashrouteorch.cpp`, `orchagent/dash/dashorch.cpp`, `orchagent/orchdaemon.cpp`

## 1. テーブルと担当 Orch の分離

DASH ルーティング 4 テーブルは 2 つの異なる Orch に分散して購読される：

| テーブル | 担当 Orch | 構築箇所 |
|---|---|---|
| `DASH_ROUTING_TYPE_TABLE` | `DashOrch` | `orchdaemon.cpp:1342-1350` |
| `DASH_ROUTE_GROUP_TABLE` | `DashRouteOrch` | `orchdaemon.cpp:1362-1368` |
| `DASH_ROUTE_TABLE` | `DashRouteOrch` | `orchdaemon.cpp:1362-1368` |
| `DASH_ROUTE_RULE_TABLE` | `DashRouteOrch` | `orchdaemon.cpp:1362-1368` |

## 2. DashOrch の購読登録 (DASH_ROUTING_TYPE_TABLE)

`orchdaemon.cpp` (L1342–1350):

```cpp
vector<string> dash_tables = {
    APP_DASH_APPLIANCE_TABLE_NAME,
    APP_DASH_ROUTING_TYPE_TABLE_NAME,  // "DASH_ROUTING_TYPE_TABLE"
    APP_DASH_ENI_TABLE_NAME,
    APP_DASH_ENI_ROUTE_TABLE_NAME,
    APP_DASH_QOS_TABLE_NAME
};
DashOrch *dash_orch = new DashOrch(m_dpu_appDb, dash_tables, m_dpu_appstateDb, dash_zmq_server);
```

`DashOrch` は `ZmqOrch` を継承 (dashorch.cpp:60-61)。`ZmqOrch` コンストラクタが各テーブルに `ZmqConsumerStateTable` を自動登録する。`DashOrch::doTask()` が `tn == APP_DASH_ROUTING_TYPE_TABLE_NAME` でルーティングし `doTaskRoutingTypeTable()` を呼び出す (dashorch.cpp:1346-1348)。

## 3. DashRouteOrch の購読登録 (残 3 テーブル)

`orchdaemon.cpp` (L1362–1368):

```cpp
vector<string> dash_route_tables = {
    APP_DASH_ROUTE_TABLE_NAME,       // "DASH_ROUTE_TABLE"
    APP_DASH_ROUTE_RULE_TABLE_NAME,  // "DASH_ROUTE_RULE_TABLE"
    APP_DASH_ROUTE_GROUP_TABLE_NAME  // "DASH_ROUTE_GROUP_TABLE"
};
DashRouteOrch *dash_route_orch = new DashRouteOrch(
    m_dpu_appDb, dash_route_tables, dash_orch, m_dpu_appstateDb, dash_zmq_server);
```

`DashRouteOrch` も `ZmqOrch` を継承 (dashrouteorch.cpp:52)。`doTask()` がテーブル名で分岐し対応する処理関数に委譲 (dashrouteorch.cpp:896-920)。

## 4. ZmqOrch 経由の通知経路 (共通)

どちらの Orch も ZMQ 経由でメッセージを受信する。Redis keyspace notification (NotificationConsumer) は使わない：

- SDN コントローラや gNMI が ZMQ ソケット経由でイベントを直接 push
- `m_dpu_appDb` への Redis 書き込みと ZMQ 通知が並行して行われる
- `ZmqOrch::doTask()` → 各 `Orch::doTask()` の呼び出しチェーンで処理される

## 5. 結果通知の書き戻し先 (APP_STATE_DB)

処理結果は `m_dpu_appstateDb` (DPU APP_STATE_DB) の対応テーブルへ書き戻される。SDN コントローラはこれを watch することで SAI プログラム完了を検知できる。

**DashOrch が管理する結果テーブル** (dashorch.cpp:73):

| 結果テーブル | `version` フィールド |
|---|---|
| `APP_DASH_ROUTING_TYPE_TABLE_NAME` (STATE) | なし |

**DashRouteOrch が管理する結果テーブル** (dashrouteorch.cpp:56-58):

| 結果テーブル | `version` フィールド |
|---|---|
| `APP_DASH_ROUTE_TABLE_NAME` (STATE) | なし |
| `APP_DASH_ROUTE_RULE_TABLE_NAME` (STATE) | なし |
| `APP_DASH_ROUTE_GROUP_TABLE_NAME` (STATE) | `entry.version()` を第 3 引数で渡す (L874) |

## 6. 外部コンポーネントからの bind/unbind 呼び出し

`DashRouteOrch` の `route_group_bind_count_` は自身のタスクループでは変更されない。`DashOrch` が `DASH_ENI_ROUTE_TABLE` の SET/DEL 処理時に `gDirectory` 経由でポインタを取得して呼び出す：

```cpp
// dashorch.cpp:1192 (ENI バインド時)
DashRouteOrch *dash_route_orch = gDirectory.get<DashRouteOrch*>();
dash_route_orch->bindRouteGroup(entry.group_id());

// dashorch.cpp:1272 (ENI アンバインド時)
dash_route_orch->unbindRouteGroup(old_group_id);
```

2 つの Orch 間に直接の pub/sub チャンネルはなく、`gDirectory` 経由のポインタ参照で同期される。

## 7. SWSS_LOG 通知

成功・失敗いずれも `SWSS_LOG_INFO` / `SWSS_LOG_WARN` / `SWSS_LOG_ERROR` でログが出力され、`rsyslog` / `swssloglevel` ツールで観察可能。外部コンポーネントへの能動的なイベント発行は行わない（SAI 呼び出しと APP_STATE_DB 書き戻しのみ）。
