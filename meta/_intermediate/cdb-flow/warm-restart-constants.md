# WARM_RESTART — ハードコード定数調査 (Phase E)

## 調査対象

- `sonic-swss-common/common/warm_restart.h`
- `sonic-swss-common/common/warm_restart.cpp`
- `sonic-swss/fpmsyncd/fpmsyncd.cpp`
- `sonic-swss/neighsyncd/neighsync.h`
- `sonic-swss/warmrestart/warmRestartAssist.h`

## 調査日: 2026-05-19

---

## 1. タイマー上限値マクロ (warm_restart.h)

```c
#define MAXIMUM_WARMRESTART_TIMER_VALUE 9999
#define DISABLE_WARMRESTART_TIMER_VALUE MAXIMUM_WARMRESTART_TIMER_VALUE
```

- `MAXIMUM_WARMRESTART_TIMER_VALUE = 9999` が `getWarmStartTimer()` 内の上限チェックに使われる (`warm_restart.cpp:161`)
- 値が 9999 を超えると `return 0` → ハードコードデフォルトへフォールバック
- `DISABLE_WARMRESTART_TIMER_VALUE` は `MAXIMUM_WARMRESTART_TIMER_VALUE` と同値。CONFIG_DB から設定不可

## 2. bgp_timer フォールバック (fpmsyncd.cpp)

```cpp
const uint32_t DEFAULT_ROUTING_RESTART_INTERVAL = 120;  // fpmsyncd.cpp:46
const uint32_t DEFAULT_EOIU_HOLD_INTERVAL = 3;           // fpmsyncd.cpp:51
```

- `DEFAULT_ROUTING_RESTART_INTERVAL = 120` 秒: `getWarmStartTimer()` が 0 を返した場合の bgp_timer フォールバック (`fpmsyncd.cpp:160`)
- `DEFAULT_EOIU_HOLD_INTERVAL = 3` 秒: `eoiu_hold_timer` (YANG/CLI 未公開) フォールバック (`fpmsyncd.cpp:229`)

## 3. neighsyncd_timer フォールバック (neighsync.h)

```c
#define DEFAULT_NEIGHSYNC_WARMSTART_TIMER 5  // neighsync.h:10
```

- `getWarmStartTimer()` が 0 を返した場合の `neighsyncd_timer` フォールバック = **5 秒** (`neighsync.cpp:30`)

## 4. teamsyncd_timer フォールバック (warmRestartAssist.h)

```cpp
static const uint32_t DEFAULT_INTERNAL_TIMER_VALUE = 5;  // warmRestartAssist.h:104
```

- `teamsyncd_timer` 未設定時のフォールバック = **5 秒**

## まとめ

| 定数名 | 値 | ソース | CONFIG_DB で変更可否 |
|--------|-----|--------|---------------------|
| `MAXIMUM_WARMRESTART_TIMER_VALUE` | 9999 | warm_restart.h:8 | 不可 |
| `DISABLE_WARMRESTART_TIMER_VALUE` | 9999 | warm_restart.h:9 | 不可 |
| `DEFAULT_ROUTING_RESTART_INTERVAL` | 120 秒 | fpmsyncd.cpp:46 | 可 (bgp_timer) |
| `DEFAULT_EOIU_HOLD_INTERVAL` | 3 秒 | fpmsyncd.cpp:51 | 可 (eoiu_hold_timer, YANG 未公開) |
| `DEFAULT_NEIGHSYNC_WARMSTART_TIMER` | 5 秒 | neighsync.h:10 | 可 (neighsyncd_timer) |
| `DEFAULT_INTERNAL_TIMER_VALUE` | 5 秒 | warmRestartAssist.h:104 | 可 (teamsyncd_timer) |
