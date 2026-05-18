# ROUTE_TABLE (STATE_DB / APPL_STATE_DB) — Phase F 副作用スキャンノート

対象テーブル: `STATE_DB ROUTE_TABLE` / `APPL_STATE_DB ROUTE_TABLE`
Consumer: `orchagent RouteOrch` (`sonic-swss/orchagent/routeorch.cpp`)
スキャン範囲: `fpmsyncd/fpmsyncd.cpp:78`, `fpmsyncd/routesync.cpp:156-158`,
              `scripts/route_check.py:767-768`, `routeorch.cpp:1227`, `routeorch.cpp:2726`

---

## 検出した副作用

### 1. APPL_STATE_DB 書き込み → FIB suppression フィードバック（fpmsyncd）

`publishRouteState()` が APPL_STATE_DB `ROUTE_TABLE` に `err_str` + `protocol` を書き込むと、
`ResponsePublisher` が同時に `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` へ通知を送出する。

`fpmsyncd` は `suppress-fib-pending=enabled` 設定時にこのチャンネルを購読し、
FIB プログラミング結果を FRR の BGP FIB suppression 機能へフィードバックする。

```python
# fpmsyncd/fpmsyncd.cpp:78
const auto routeResponseChannelName = std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
# fpmsyncd/fpmsyncd.cpp:113-117
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

**副作用**: APPL_STATE_DB への `err_str=SWSS_RC_SUCCESS` 書き込みが FRR への経路アドバタイズを
アンロックする（suppress-fib-pending が有効な場合）。SAI 失敗時は `err_str` に `[SAI]` プレフィクス
エラーが書かれ、FRR は経路を suppress 状態のまま保持する。

evidence: `fpmsyncd/fpmsyncd.cpp:78`, `fpmsyncd/fpmsyncd.cpp:113-117`

---

### 2. APPL_STATE_DB 書き込み → route_check.py による整合確認

`route_check.py` は `APPL_STATE_DB ROUTE_TABLE` を参照して APPL_DB と APPL_STATE_DB の
経路整合を確認する。不整合（APPL_DB にあるが APPL_STATE_DB にない経路）を検出すると
syslog にアラートを出力する。

```python
# scripts/route_check.py:767-768
db = swsscommon.DBConnector('APPL_STATE_DB', REDIS_TIMEOUT_MSECS, True, namespace)
response_producer = swsscommon.NotificationProducer(db, f'{APPL_DB_NAME}_{swsscommon.APP_ROUTE_TABLE_NAME}_RESPONSE_CHANNEL')
```

**副作用**: orchagent が SAI 操作失敗などで APPL_STATE_DB への書き込みをスキップした場合、
`route_check.py` が `missed_ROUTE_TABLE_routes` としてアラートを記録する。

evidence: `scripts/route_check.py:767-768`, `scripts/route_check.py:940`

---

### 3. RouteOrch doTask バルク処理後の flush → レスポンス通知タイミング

```cpp
// routeorch.cpp:1227
/* Flush response publisher so route notifications reach fpmsyncd every batch. */
```

RouteOrch は 1 回の `doTask()` イテレーションで複数の ROUTE_TABLE エントリを
バルク処理し、全 SAI 操作完了後に `publishRouteState()` を一括 flush する。
このため APPL_STATE_DB への書き込みとレスポンスチャンネル通知はバッチ単位で遅延する。

evidence: `routeorch.cpp:1227`

---

### 4. STATE_DB `state=ok` / `state=na` → NextHop Observer 通知（間接）

STATE_DB `ROUTE_TABLE` への書き込みはデフォルト経路（`0.0.0.0/0` / `::/0`）が
SAI 登録/削除された後に行われるが、その直前に `notifyNextHopChangeObservers()` が
呼ばれ、MirrorOrch / NatOrch 等の登録済み Observer に次ホップ変更を通知する。

```cpp
// routeorch.cpp:2726
notifyNextHopChangeObservers(vrf_id, ipPrefix, nextHops, true);
// routeorch.cpp:2729
publishRouteState(ctx);
```

**副作用**: デフォルト経路の変更は MirrorOrch のミラーセッション更新、
NatOrch の NAT エントリ更新をトリガーしうる。STATE_DB の `state` 書き込みは
これらの Observer 通知の直後に行われる。

evidence: `routeorch.cpp:2703`, `routeorch.cpp:2726`, `routeorch.cpp:2729`

---

## 副作用サマリ

| # | 副作用 | トリガー | 影響範囲 |
|---|--------|----------|---------|
| 1 | APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL 通知 → fpmsyncd FIB suppression アンロック | APPL_STATE_DB 書き込み（SET / DEL） | suppress-fib-pending 有効時のみ |
| 2 | route_check.py アラート (`missed_ROUTE_TABLE_routes`) | APPL_STATE_DB 書き込みスキップ（SAI 失敗等） | syslog アラート |
| 3 | レスポンス通知のバッチ遅延 | RouteOrch doTask バルク flush | APPL_STATE_DB 書き込みは 1 イテレーション単位 |
| 4 | NextHop Observer 通知（MirrorOrch / NatOrch 等） | updateDefRouteState() 直前の notifyNextHopChangeObservers() | デフォルト経路変更時のみ |
