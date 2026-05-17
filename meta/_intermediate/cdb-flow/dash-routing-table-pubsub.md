# DASH_ROUTE_* テーブル — Phase G: Pub/Sub・通知経路 (pubsub)

調査対象: `orchagent/dash/dashrouteorch.cpp`, `orchagent/orchdaemon.cpp`

## 1. DashRouteOrch の購読テーブル登録

`orchdaemon.cpp` (L1363–1368) で `DashRouteOrch` を構築する際に購読テーブルを配列で渡す：

```cpp
vector<string> dash_route_tables = {
    APP_DASH_ROUTE_TABLE_NAME,       // "DASH_ROUTE_TABLE"
    APP_DASH_ROUTE_RULE_TABLE_NAME,  // "DASH_ROUTE_RULE_TABLE"
    APP_DASH_ROUTE_GROUP_TABLE_NAME  // "DASH_ROUTE_GROUP_TABLE"
};
DashRouteOrch *dash_route_orch = new DashRouteOrch(
    m_dpu_appDb, dash_route_tables, dash_orch, m_dpu_appstateDb, dash_zmq_server);
```

親クラス `ZmqOrch` のコンストラクタがこの配列を受け取り、各テーブル名に対して `ZmqConsumerStateTable` を作成して自動登録する。

## 2. ZmqOrch 経由の通知経路

`DashRouteOrch` は `Orch` ではなく `ZmqOrch` を継承する。これにより：

- **通常の Redis keyspace notification (NotificationConsumer)** ではなく、**ZeroMQ (ZMQ)** 経由でメッセージを受信する
- SDN コントローラや gNMI が ZMQ ソケット経由でイベントを直接 push するため、`m_dpu_appDb` への Redis 書き込みと ZMQ 通知が並行して行われる
- `ZmqOrch::doTask()` → `DashRouteOrch::doTask()` の呼び出しチェーンで実際の処理が行われる

## 3. 購読テーブルと処理関数のマッピング

`doTask(ConsumerBase& consumer)` (L896–920) でテーブル名から分岐：

| 購読テーブル名 | 処理関数 | DB |
|---|---|---|
| `DASH_ROUTE_TABLE` (APP_DB) | `doTaskRouteTable()` | `m_dpu_appDb` |
| `DASH_ROUTE_RULE_TABLE` (APP_DB) | `doTaskRouteRuleTable()` | `m_dpu_appDb` |
| `DASH_ROUTE_GROUP_TABLE` (APP_DB) | `doTaskRouteGroupTable()` | `m_dpu_appDb` |

## 4. 結果通知の書き戻し先 (APP_STATE_DB)

`DashRouteOrch` は処理結果を `m_dpu_appstateDb` の対応テーブルへ書き戻す（コンストラクタ L56–58）：

| 結果テーブル | 通知のトリガー |
|---|---|
| `APP_DASH_ROUTE_TABLE_NAME` (STATE) | `writeResultToDB` / `removeResultFromDB` in `doTaskRouteTable` |
| `APP_DASH_ROUTE_RULE_TABLE_NAME` (STATE) | `writeResultToDB` / `removeResultFromDB` in `doTaskRouteRuleTable` |
| `APP_DASH_ROUTE_GROUP_TABLE_NAME` (STATE) | `writeResultToDB(…, entry.version())` / `removeResultFromDB` in `doTaskRouteGroupTable` |

SDN コントローラはこの APP_STATE_DB の結果テーブルを watch することで、orchagent による SAI プログラム完了を検知できる。

## 5. 外部コンポーネントからの呼び出し (bindRouteGroup / unbindRouteGroup)

`DashRouteOrch` は `route_group_bind_count_` を自身の内部で変更しない。bind/unbind は `DashOrch` (dashorch.cpp L1192, L1272) が `DASH_ENI_ROUTE_TABLE` の SET/DEL 処理時に次のメソッドを呼び出すことで変更される：

```cpp
// dashorch.cpp:1192
DashRouteOrch *dash_route_orch = gDirectory.get<DashRouteOrch*>();
dash_route_orch->bindRouteGroup(route_group);   // ENI バインド時

// dashorch.cpp:1272
dash_route_orch->unbindRouteGroup(route_group); // ENI アンバインド時
```

この設計により、`DASH_ENI_ROUTE_TABLE` の変更が `DashRouteOrch` の `isRouteGroupBound()` チェックに間接的に影響する。2 つのオーケストレータ間に直接の pub/sub チャンネルはなく、`gDirectory` 経由のポインタ参照で同期される。

## 6. SWSS_LOG 通知

成功・失敗いずれの場合も `SWSS_LOG_INFO` / `SWSS_LOG_WARN` / `SWSS_LOG_ERROR` でログが出力され、`rsyslog` または `swssloglevel` ツールで観察可能。ただし外部コンポーネントへの能動的なイベント発行は行わない（SAI 呼び出しと APP_STATE_DB 書き戻しのみ）。
