# dpu-counter Phase E — ハードコード定数 調査証跡

調査日: 2026-05-19  
対象: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashorch.h` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/dash/dashcounter.h` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/flexcounterorch.cpp` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-buildimage/dockers/docker-orchagent/enable_counters.py` (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## 抽出した定数一覧

### dashorch.h (L29-33)

```cpp
#define ENI_STAT_COUNTER_FLEX_COUNTER_GROUP "ENI_STAT_COUNTER"
#define ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS 10000

#define METER_STAT_COUNTER_FLEX_COUNTER_GROUP "METER_STAT_COUNTER"
#define METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS 10000
```

### flexcounterorch.cpp (L44)

```cpp
#define FLEX_COUNTER_DELAY_SEC 60
```

warm-start 時の FlexCounterOrch 遅延タイマー秒数。

### flexcounterorch.cpp (L60-61)

```cpp
#define ENI_KEY                     "ENI"
#define DASH_METER_KEY              "DASH_METER"
```

CONFIG_DB FLEX_COUNTER_TABLE のキー文字列リテラル。

### enable_counters.py (L52-64)

```python
DEFAULT_SMOOTH_INTERVAL = '10'
DEFAULT_ALPHA = '0.18'
# uptime < 300 → sleep(180)
# uptime >= 300 → sleep(60)
```

enable_counters.py の uptime 境界値 300 秒、sleep 値 60/180 秒はリテラル定数。

### dashcounter.h (L15)

```cpp
bool fc_status = false;
```

`DashCounter` テンプレートの初期フラグ。CONFIG_DB 未設定時のデフォルト状態。

## 結論

CONFIG_DB で上書き不可能なリテラル定数は以下の 7 つ:

1. `ENI_STAT_COUNTER_FLEX_COUNTER_GROUP` = `"ENI_STAT_COUNTER"`
2. `METER_STAT_COUNTER_FLEX_COUNTER_GROUP` = `"METER_STAT_COUNTER"`
3. `ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` = `10000` ms（orchagent 内部デフォルト）
4. `METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` = `10000` ms（orchagent 内部デフォルト）
5. `FLEX_COUNTER_DELAY_SEC` = `60` 秒（warm-start 時の doTask ブロック時間）
6. uptime 境界値 = `300` 秒（enable_counters.py の sleep 分岐）
7. DPU 自動有効化 sleep = `180` 秒 (uptime < 300) / `60` 秒 (uptime >= 300)
