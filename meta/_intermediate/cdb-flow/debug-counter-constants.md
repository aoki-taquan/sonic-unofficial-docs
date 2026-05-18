# debug-counter: Phase E ハードコード定数調査

調査日: 2026-05-18
対象: `DEBUG_COUNTER` テーブル / `DebugCounterOrch`

## フィールド名定数 (debug_counter.h)

```c
#define COUNTER_TYPE        "type"           // L16
#define COUNTER_ALIAS       "alias"          // L15
#define COUNTER_DESCRIPTION "desc"           // L17
#define COUNTER_GROUP       "group"          // L18

#define DROP_MONITOR_STATUS                   "drop_monitor_status"       // L21
#define DROP_MONITOR_DROP_COUNT_THRESHOLD     "drop_count_threshold"      // L22
#define DROP_MONITOR_INCIDENT_COUNT_THRESHOLD "incident_count_threshold"  // L23
#define DROP_MONITOR_WINDOW                   "window"                    // L24
```

## counter_type 値 → SAI マッピング (debug_counter.cpp:38-44)

```cpp
const std::unordered_map<std::string, sai_debug_counter_type_t> DebugCounter::debug_counter_type_lookup = {
    { "PORT_INGRESS_DROPS",   SAI_DEBUG_COUNTER_TYPE_PORT_IN_DROP_REASONS },
    { "PORT_EGRESS_DROPS",    SAI_DEBUG_COUNTER_TYPE_PORT_OUT_DROP_REASONS },
    { "SWITCH_INGRESS_DROPS", SAI_DEBUG_COUNTER_TYPE_SWITCH_IN_DROP_REASONS },
    { "SWITCH_EGRESS_DROPS",  SAI_DEBUG_COUNTER_TYPE_SWITCH_OUT_DROP_REASONS },
};
```

## flex_counter_type_lookup (debugcounterorch.cpp:18-22)

```cpp
static const unordered_map<string, CounterType> flex_counter_type_lookup = {
    { "PORT_INGRESS_DROPS",   CounterType::PORT_DEBUG },
    { "PORT_EGRESS_DROPS",    CounterType::PORT_DEBUG },
    { "SWITCH_INGRESS_DROPS", CounterType::SWITCH_DEBUG },
    { "SWITCH_EGRESS_DROPS",  CounterType::SWITCH_DEBUG },
};
```

## FLEX_COUNTER グループ定数 (debugcounterorch.h)

```c
#define DEBUG_COUNTER_FLEX_COUNTER_GROUP              "DEBUG_COUNTER"        // L19
#define DEBUG_DROP_MONITOR_FLEX_COUNTER_GROUP         "DEBUG_MONITOR_COUNTER"// L20
#define DEBUG_DROP_MONITOR_FLEX_COUNTER_POLLING_INTERVAL_MS "60000"          // L21 (60 秒)
```

## DROP_REASON キー区切り文字

debugcounterorch.cpp の `parseDropReasonKey()` で `|` を delimiter として使用:
`DEBUG_COUNTER_DROP_REASON|<counter_name>|<reason>` → `counter_name` + `drop_reason` に分割。

## 結論

- `type` フィールドの値は 4 値のみ。それ以外は `supported_counter_types` に含まれず `task_failed`。
- FlexCounter ポーリングは DROP_MONITOR 系のみ固定 60000 ms (60 秒)。DEBUG_COUNTER 系は `orchdaemon.cpp` のコンストラクタ引数 `poll_interval` 依存。
- `drop_count_threshold` / `incident_count_threshold` / `window` は DROP_MONITOR 専用フィールド。通常の debug counter では無視。
