# pwm (WATERMARK_TABLE) — Phase D 失敗挙動証跡

調査日: 2026-05-18  
調査対象: `sonic-swss/orchagent/watermarkorch.cpp` (master)  
           `sonic-swss-common/common/converter.h` (master)  
           `sonic-swss/orchagent/orch.cpp` (Consumer::drain())

## 1. `interval` 値不正による例外

`handleWmConfigUpdate()` (watermarkorch.cpp:103) は `to_uint<uint32_t>(i.second.c_str())` で文字列を uint32_t に変換する。  
`to_uint` は `converter.h:17` の `stoul` をラップし、変換失敗または範囲外の場合 `std::invalid_argument` を `throw` する。

`watermarkorch.cpp:90` の `consumer.m_toSync.erase(it++)` は throw の**後**に実行される。  
例外は `Consumer::drain()` (orch.cpp:612-615) の `catch (const std::invalid_argument& e)` で捕捉され、  
`SWSS_LOG_ERROR("Exception caught: type=invalid_argument, ...")` を出力してリターンする。

**結果**: 不正な `interval` 値を持つエントリは `m_toSync` から削除されずに残留し、  
次回 select イテレーションで再び `drain()` が呼ばれるたびに同じエラーログが繰り返し出力される。  
orchagent プロセス自体はクラッシュしない（例外がキャッチされる）が、  
タイマー周期は変更されないまま（旧値または 120 秒デフォルト維持）。  
修正方法: `watermarkcfg -c <正しい値>` で上書き、または `sonic-db-cli CONFIG_DB hset 'WATERMARK_TABLE|TELEMETRY_INTERVAL' interval <値>` で直接修正。

## 2. `allPortsReady()` 未達 — イベントの無限待機

`doTask(Consumer&)` (watermarkorch.cpp:56) は `!gPortsOrch->allPortsReady()` の場合に即 return する。  
`m_toSync` はクリアされないため、ポートが ready になるまでイベントは保留される。  
通常は orchagent 起動直後の一時的な状態だが、ポートの初期化が永続的に失敗した場合は  
`WATERMARK_TABLE` / `FLEX_COUNTER_TABLE` のイベントが永遠に処理されない。

## 3. DEL_COMMAND — silent 警告のみ

`WATERMARK_TABLE|TELEMETRY_INTERVAL` が DEL された場合、`doTask()` (watermarkorch.cpp:82-83) は  
`SWSS_LOG_WARN("Unsupported op %s", ...)` を出力するのみ。  
タイマー周期はリセットされず、DEL 直前の値（または 120 秒デフォルト）が継続して使用される。  
エントリは `m_toSync.erase(it++)` で消去されるため再試行は発生しない。

## 4. `clearSingleWm()` で空の OID リスト — 無音スキップ

`doTask(SelectableTimer&)` および `doTask(NotificationConsumer&)` 内で `clearSingleWm()` が呼ばれるとき、  
`m_pg_ids` / `m_unicast_queue_ids` 等が空の場合（`init_pg_ids()` / `init_queue_ids()` 呼び出し後も  
COUNTERS_DB にエントリがない場合）、`for` ループがゼロ回実行されるだけで  
エラーログも副作用もなく静かに終了する。PERIODIC_WATERMARKS はゼロクリアされない。

## 5. WATERMARK_CLEAR_REQUEST 不正 op / data

`doTask(NotificationConsumer&)` で `op` が `"PERSISTENT"` / `"USER"` 以外の場合は  
`SWSS_LOG_WARN("Unknown watermark clear request op: ...")` を出力して `return`。  
`data` が既知のクリア要求 (`PG_HEADROOM`, `PG_SHARED`, `Q_SHARED_*`, `BUFFER_POOL`, `HEADROOM_POOL`) 以外の場合も  
`SWSS_LOG_WARN("Unknown watermark clear request data: ...")` を出力して `return`。  
いずれも COUNTERS_DB への書き込みは発生しない。

## 根拠コード位置

- `watermarkorch.cpp:56` — allPortsReady ゲート
- `watermarkorch.cpp:82-88` — DEL/unknown op 処理
- `watermarkorch.cpp:94-113` — handleWmConfigUpdate (to_uint throw 経路)
- `watermarkorch.cpp:180-229` — NotificationConsumer 不正 op/data
- `watermarkorch.cpp:284-320` — init_pg_ids / init_queue_ids (空リスト条件)
- `orch.cpp:608-631` — Consumer::drain() 例外キャッチ
- `converter.h:14-29` — __to_uint64 throw 条件
