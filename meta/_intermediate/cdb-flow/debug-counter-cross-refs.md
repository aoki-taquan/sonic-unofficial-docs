# debug-counter — cross-refs 調査メモ (Phase C)

## 調査対象

- `sonic-swss/orchagent/debugcounterorch.cpp`
- `sonic-swss/orchagent/debugcounterorch.h`
- `sonic-swss-common/common/schema.h`

## 発見した暗黙参照

### 1. PORT (PortsOrch / PORT テーブル)

`DebugCounterOrch` は起動時に `gPortsOrch->attach(this)` を呼び、`SUBJECT_TYPE_PORT_CHANGE` イベントを購読する（L39, L71）。
`PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` 型カウンタは `gPortsOrch->getAllPorts()` でポート一覧を取得し、
`Port::Type::PHY` のみを FlexCounter 対象として登録する（L629–645）。
ポート追加/削除イベントで `installDebugFlexCounters()` / `uninstallDebugFlexCounters()` が呼ばれる（L92, L106）。
YANG `sonic-debug-counter` には PORT への leafref は存在しない。

### 2. FLEX_COUNTER_DB (FlexCounterManager)

コンストラクタで `flex_counter_manager(DEBUG_COUNTER_FLEX_COUNTER_GROUP, ...)` を初期化し（L29）、
FLEX_COUNTER_DB に `"DEBUG_COUNTER"` グループエントリを作成する（L25–26 コメント）。
`setFlexCounterGroupParameter(DEBUG_DROP_MONITOR_FLEX_COUNTER_GROUP, ...)` で drop monitor 用グループも登録（L55–59）。
FlexCounter グループ名:
- `DEBUG_COUNTER` (`debugcounterorch.h:19`)
- `DEBUG_MONITOR_COUNTER` (`debugcounterorch.h:20`)

### 3. STATE_DB DEBUG_COUNTER_CAPABILITIES

起動時に `publishDropCounterCapabilities()` が SAI にクエリを投げ、
`STATE_DB DEBUG_COUNTER_CAPABILITIES` テーブルに書き込む（L31, L317–361）。
`COUNTERS_DEBUG_NAME_PORT_STAT_MAP` / `COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP` をメモリ管理する（L33–34）。

### 4. COUNTERS_DB

`COUNTERS_DEBUG_NAME_PORT_STAT_MAP` と `COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP` に counter_name ↔ SAI stat のマッピングを書き込む（L33–34、`drop_monitor.lua:18-19`）。
drop monitor Lua スクリプトがこのマップをポーリング周期ごとに参照する（`drop_monitor.lua:18`）。

## evidence 行番号サマリ

| 参照先 | evidence |
|--------|----------|
| PORT (PortsOrch) | `debugcounterorch.cpp:16,39,71,92,106,629,682` |
| FLEX_COUNTER_DB DEBUG_COUNTER グループ | `debugcounterorch.cpp:25-29; debugcounterorch.h:19-21` |
| FLEX_COUNTER_DB DEBUG_MONITOR_COUNTER グループ | `debugcounterorch.cpp:55-59; debugcounterorch.h:20` |
| STATE_DB DEBUG_COUNTER_CAPABILITIES | `debugcounterorch.cpp:31,314-361` |
| COUNTERS_DB COUNTERS_DEBUG_NAME_PORT_STAT_MAP | `debugcounterorch.cpp:33; drop_monitor.lua:18-19` |
| COUNTERS_DB COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP | `debugcounterorch.cpp:34` |
