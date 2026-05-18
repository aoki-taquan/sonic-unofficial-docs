# pg-watermark Phase C — 暗黙参照テーブルスキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/pg-watermark.md

対象テーブル: `FLEX_COUNTER_TABLE|PG_WATERMARK`
Consumer: `flexcounterorch` (FlexCounterOrch) / `portsorch` (PortsOrch) / `watermarkorch` (WatermarkOrch)
スキャン範囲: `flexcounterorch.cpp` 全行, `portsorch.cpp` pg_watermark 関連関数, `watermarkorch.cpp` 全行, `sonic-swss-common/common/schema.h`

---

## 検出した暗黙参照関係

### 1. COUNTERS_DB — COUNTERS_PG_NAME_MAP (WRITE)

`portsorch.cpp:8882, 8937` が `m_pgCounterNameMapUpdater->setCounterNameMap(pgVector)` を呼び、`COUNTERS_DB` の `COUNTERS_PG_NAME_MAP` テーブルに `<port_alias>:<pg_index>` → `<sai_oid>` マッピングを書き込む。これは `FLEX_COUNTER_TABLE|PG_WATERMARK` enable の有無に依存せず、`BUFFER_PG` テーブルにエントリが追加された時点で常に書かれる。`watermarkstat` / `pg-drop` コマンドがこのマップを参照して OID を解決する。

根拠: `sonic-swss-common/common/schema.h:230` `#define COUNTERS_PG_NAME_MAP "COUNTERS_PG_NAME_MAP"`; `portsorch.cpp:785, 8882, 8937`

### 2. COUNTERS_DB — COUNTERS_PG_PORT_MAP (WRITE)

`portsorch.cpp:8883, 8938` が `m_pgPortTable->set("", pgPortVector)` を呼び、`COUNTERS_PG_PORT_MAP` テーブルに `<sai_pg_oid>` → `<sai_port_oid>` マッピングを書き込む。`watermarkstat` がウォーターマーク値をポートごとに集計するために参照する。

根拠: `sonic-swss-common/common/schema.h:231`; `portsorch.cpp:786, 8883, 8938`

### 3. COUNTERS_DB — COUNTERS_PG_INDEX_MAP (WRITE)

`portsorch.cpp:8884, 8939` が `m_pgIndexTable->set("", pgIndexVector)` を呼び、`COUNTERS_PG_INDEX_MAP` テーブルに `<sai_pg_oid>` → `<pg_index>` マッピングを書き込む。PG インデックス（0–7）を OID から逆引きするために利用される。

根拠: `sonic-swss-common/common/schema.h:232`; `portsorch.cpp:787, 8884, 8939`

### 4. FLEX_COUNTER_DB — FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER (WRITE)

`portsorch.cpp:872-876` が `setFlexCounterGroupParameter()` を呼び、`FLEX_COUNTER_DB` の `FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER` にポーリング間隔 (`60000`) と `STATS_MODE=READ_AND_CLEAR` を書き込む。`syncd` の FlexCounter がこのグループ設定を読んでポーリング動作を決定する。

根拠: `portsorch.h:36` `#define PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "PG_WATERMARK_STAT_COUNTER"`; `sonic-swss-common/common/schema.h:336`; `portsorch.cpp:872-876`

### 5. FLEX_COUNTER_DB — PG_WATERMARK_STAT_COUNTER:<sai_oid> (WRITE)

`pg_watermark_manager.setCounterIdList(port.m_priority_group_ids[pgIndex], CounterType::PRIORITY_GROUP, pg_counter_stats)` (`portsorch.cpp:9051`) が、PG OID ごとに `FLEX_COUNTER_DB|PG_WATERMARK_STAT_COUNTER:<oid>|PG_WATERMARK_STAT_ID_LIST` を書き込む。`syncd` がこのエントリを見て `sai_get_ingress_priority_group_stats()` を呼ぶ。`FLEX_COUNTER_TABLE|PG_WATERMARK` が enable でない場合この書き込みは行われない。

根拠: `portsorch.cpp:9048-9051`

### 6. COUNTERS_DB — PERIODIC_WATERMARKS / PERSISTENT_WATERMARKS / USER_WATERMARKS (WRITE)

`watermarkorch` の Lua スクリプト (`watermark_pg.lua`) が syncd の FlexCounter ポーリング結果を受け取り、3 つの COUNTERS_DB テーブルに PG ウォーターマーク値を書き込む。`PERIODIC_WATERMARKS` は telemetry タイマー周期でクリア、`PERSISTENT_WATERMARKS` / `USER_WATERMARKS` は明示的なクリアコマンドまで保持。

根拠: `sonic-swss-common/common/schema.h:268-270`; `watermark_pg.lua:10-12`; `watermarkorch.cpp:31-33`

### 7. CONFIG_DB — BUFFER_PG (READ)

`flexcounterorch.cpp` の `getPgConfigurations()` が `FLEX_COUNTER_TABLE|PG_WATERMARK` enable 受信時に `BUFFER_PG` テーブルを参照して PG インデックスのセットを決定する。`BUFFER_PG` エントリが存在しない場合は `addPriorityGroupWatermarkFlexCounters()` が空マップで呼ばれ、FlexCounter への OID 登録が発生しない。

根拠: `flexcounterorch.cpp:538-670` (getPgConfigurations); `portsorch.cpp:8998-9027`

### 8. APPL_DB — WATERMARK_CLEAR_REQUEST 通知チャネル (READ)

`watermarkorch` が `APPL_DB` の `WATERMARK_CLEAR_REQUEST` 通知チャネルを購読し、`watermarkcfg clear` CLI からの `PERSISTENT` / `USER` クリア要求を受信して対応 COUNTERS_DB テーブルをリセットする。`FLEX_COUNTER_TABLE|PG_WATERMARK` とは別経路。

根拠: `watermarkorch.cpp:35-39`
