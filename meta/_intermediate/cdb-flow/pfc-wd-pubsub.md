# PFC_WD — Phase G: Redis 通知メカニズム 調査ノート

## 調査対象

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## CONFIG_DB 購読経路

`PfcWdOrch` は `Orch(db, tableNames)` ベースクラス経由で CONFIG_DB の `CFG_PFC_WD_TABLE_NAME` (= `"PFC_WD"`) を `SubscriberStateTable` で購読する。

- バインド: `orchdaemon.cpp:631-633` — `pfc_wd_tables = { CFG_PFC_WD_TABLE_NAME }` を `PfcWdSwOrch` コンストラクタへ渡す
- 受信: `pfcwdorch.cpp:64-122` — `doTask(Consumer& consumer)` で SET/DEL を処理

## APPL_DB 購読 (SubscriberStateTable)

`PfcWdSwOrch` コンストラクタ (`pfcwdorch.cpp:736-739`) でウォームリブート対応として APPL_DB の `PFC_WD_TABLE` (`APP_PFC_WD_TABLE_NAME`) を `SubscriberStateTable` で購読する。

```cpp
auto ssTable = new swss::SubscriberStateTable(
        m_applDb.get(), APP_PFC_WD_TABLE_NAME, ...);
auto ssConsumer = new Consumer(ssTable, this, APP_PFC_WD_TABLE_NAME);
Orch::addExecutor(ssConsumer);
```

これはウォームリブート後に storm 状態を引き継ぐために使用される。

## NotificationConsumer (COUNTERS_DB `PFC_WD_ACTION`)

`PfcWdSwOrch` コンストラクタ (`pfcwdorch.cpp:724-728`) で COUNTERS_DB の `"PFC_WD_ACTION"` チャネルを `NotificationConsumer` で購読する。

```cpp
auto consumer = new swss::NotificationConsumer(
        this->getCountersDb().get(), "PFC_WD_ACTION");
auto wdNotification = new Notifier(consumer, this, "PFC_WD_ACTION");
Orch::addExecutor(wdNotification);
```

Lua スクリプト (`pfc_detect_<platform>.lua`) が PFC storm を検出すると COUNTERS_DB へ `PUBLISH PFC_WD_ACTION <queue_oid>` を発行し、`doTask(NotificationConsumer&)` がこれを受けて storm ハンドラを起動する。

## SelectableTimer (カウンタポーリング)

`PfcWdSwOrch` コンストラクタ (`pfcwdorch.cpp:730-734`) で `COUNTER_CHECK_POLL_TIMEOUT_SEC = 1` 秒間隔の `SelectableTimer` を登録する。

```cpp
auto interv = timespec { .tv_sec = COUNTER_CHECK_POLL_TIMEOUT_SEC, .tv_nsec = 0 };
auto timer = new SelectableTimer(interv);
auto executor = new ExecutableTimer(timer, this, "PFC_WD_COUNTERS_POLL");
Orch::addExecutor(executor);
timer->start();
```

タイマー発火 → `doTask(SelectableTimer&)` → 全エントリの `handler->commitCounters(true)` でカウンタを COUNTERS_DB に flush する。

## orchagent 主ループ の SELECT_TIMEOUT

`orchdaemon.cpp:959` — `m_select->select(&s, SELECT_TIMEOUT)` (SELECT_TIMEOUT = 1000 ms)。

CONFIG_DB / APPL_DB / COUNTERS_DB いずれの Selectable もこの主ループで多重化される。NotificationConsumer イベントが来るか SelectableTimer が発火するか、最長 1000 ms でポーリングされる。

## まとめ

| チャネル | DB | キー/テーブル | 方向 | 購読方式 |
|---|---|---|---|---|
| CONFIG_DB CFG_PFC_WD | CONFIG_DB | `PFC_WD\|*` | 受信 | `SubscriberStateTable` (Orch ベース) |
| APPL_DB PFC_WD_TABLE | APPL_DB | `PFC_WD_TABLE\|*` | 受信 | `SubscriberStateTable` |
| COUNTERS_DB PFC_WD_ACTION | COUNTERS_DB | `PFC_WD_ACTION` (channel) | 受信 | `NotificationConsumer` + `Notifier` |
| SelectableTimer | — | — | タイマー (1 秒) | `SelectableTimer` / `ExecutableTimer` |
