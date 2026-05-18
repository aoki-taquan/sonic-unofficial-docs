# debug-counter — Phase G: 通信メカニズム (pubsub)

調査日: 2026-05-18
対象: `docs/reference/config-db/debug-counter.md`

## 調査根拠

- `sonic-swss/orchagent/orchdaemon.cpp:446-452`: `debug_counter_tables` ベクタ定義と `DebugCounterOrch` コンストラクタ呼び出し
- `sonic-swss/orchagent/debugcounterorch.cpp:129-135`: `Orch(db, tableNames)` 基底クラスによる Consumer 登録
- `sonic-swss/orchagent/debugcounterorch.cpp:37-39`: `publishDropCounterCapabilities()` + `gPortsOrch->attach(this)` 呼び出し
- `sonic-swss/orchagent/debugcounterorch.cpp:67-110`: `update(SubjectType, void*)` — PortsOrch Observer イベント受信
- `sonic-swss/orchagent/orchdaemon.cpp:22-23,959`: SELECT_TIMEOUT = 1000 ms

## Consumer ペア

| 区間 | 方式 | 対象テーブル |
|------|------|-------------|
| CONFIG_DB → DebugCounterOrch | `SubscriberStateTable` (Orch 基底クラス経由) | `DEBUG_COUNTER`, `DEBUG_COUNTER_DROP_REASON`, `DEBUG_DROP_MONITOR` |
| PortsOrch → DebugCounterOrch | Subject/Observer パターン (`attach`/`update`) | ポート追加/削除イベント |
| DebugCounterOrch → SAI | SAI API 直接呼び出し | `sai_debug_counter_api` |
| DebugCounterOrch → STATE_DB | `Table::set()` | `DEBUG_COUNTER_CAPABILITIES` |
| DebugCounterOrch → COUNTERS_DB | `Table::set()` / `Table::hdel()` | `COUNTERS_DEBUG_NAME_PORT_STAT_MAP`, `COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP` |
| DebugCounterOrch → FLEX_COUNTER_DB | `FlexCounterManager` 経由 | `FLEX_COUNTER_TABLE` (`DEBUG_COUNTER` / `DEBUG_MONITOR_COUNTER` グループ) |

## NotificationConsumer/Producer

使用なし。`DEBUG_COUNTER` は CONFIG_DB keyspace notification のみ。

## retry と doTask 実行順序

orchdaemon の `select()` ループが 1000 ms タイムアウトで実行。イベント受信時は `Consumer::drain()` → `DebugCounterOrch::doTask(Consumer&)` が呼ばれる。

`doTask()` 冒頭で `gPortsOrch->allPortsReady()` チェック。false の間は即 return。retry (`task_need_retry`) は**一切返さない**。代わりに `free_drop_counters` / `free_drop_reasons` の pending キューで順序依存を解決する。
