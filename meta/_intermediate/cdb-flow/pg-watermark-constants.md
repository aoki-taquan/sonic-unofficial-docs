# Phase E: FLEX_COUNTER_TABLE|PG_WATERMARK ハードコード定数調査

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.h`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/watermarkorch.cpp`

## 検出した定数

### portsorch.h

```cpp
// line 36-40
#define PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "PG_WATERMARK_STAT_COUNTER"
#define QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS "60000"
#define PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS    "60000"
#define PG_DROP_FLEX_STAT_COUNTER_POLL_MSECS         "10000"
```

`PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS "60000"` — 文字列定数。
`setFlexCounterGroupParameter()` 呼び出し時に FLEX_COUNTER_DB `FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER` の `POLL_INTERVAL` フィールドへ書き込まれる。

`PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "PG_WATERMARK_STAT_COUNTER"` — FLEX_COUNTER_DB グループ名。syncd がこの名前でポーリングスレッドを識別する。

### portsorch.cpp

```cpp
// line 92
#define PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000

// line 736
pg_watermark_manager(PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP,
                     StatsMode::READ_AND_CLEAR,
                     PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS,
                     false),

// line 872-876
setFlexCounterGroupParameter(PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP,
                             PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS,
                             STATS_MODE_READ_AND_CLEAR,
                             PG_PLUGIN_FIELD,
                             pgWmSha);

// line 410-414
static const vector<sai_ingress_priority_group_stat_t> ingressPriorityGroupWatermarkStatIds =
{
    SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES,
    SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES,
};
```

`STATS_MODE_READ_AND_CLEAR = "READ_AND_CLEAR"` — FLEX_COUNTER_GROUP_TABLE に書き込まれる固定値。SAI からポーリングするたびにハードウェアウォーターマークレジスタがクリアされる。CONFIG_DB から変更不可能。

`ingressPriorityGroupWatermarkStatIds` — `static const` 配列。FlexCounter が各 PG OID に対して収集する SAI カウンタを決定。XOFF_ROOM_WATERMARK_BYTES と SHARED_WATERMARK_BYTES の 2 統計のみ。ランタイム変更手段なし。

### watermarkorch.cpp

```cpp
// line 9
#define DEFAULT_TELEMETRY_INTERVAL 120

// line 11-16
#define CLEAR_PG_HEADROOM_REQUEST "PG_HEADROOM"
#define CLEAR_PG_SHARED_REQUEST "PG_SHARED"
#define CLEAR_QUEUE_SHARED_UNI_REQUEST "Q_SHARED_UNI"
#define CLEAR_QUEUE_SHARED_MULTI_REQUEST "Q_SHARED_MULTI"
#define CLEAR_QUEUE_SHARED_ALL_REQUEST "Q_SHARED_ALL"
#define CLEAR_BUFFER_POOL_REQUEST "BUFFER_POOL"
#define CLEAR_HEADROOM_POOL_REQUEST "HEADROOM_POOL"

// line 41
auto intervT = timespec { .tv_sec = DEFAULT_TELEMETRY_INTERVAL , .tv_nsec = 0 };
```

`DEFAULT_TELEMETRY_INTERVAL 120` — `m_telemetryTimer` のデフォルト周期 (秒)。`WATERMARK_TABLE|TELEMETRY_INTERVAL` エントリで上書き可能。

`CLEAR_PG_HEADROOM_REQUEST "PG_HEADROOM"` — `WATERMARK_CLEAR_REQUEST` 通知チャネルへのリクエスト文字列。CLI `watermarkcfg clear pg-headroom` が発行する文字列と完全一致が必要。

## 結論

PG_WATERMARK に直接関連するハードコード定数は 9 件:
1. `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS = "60000"` (portsorch.h:39)
2. `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 60000` (portsorch.cpp:92)
3. `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP = "PG_WATERMARK_STAT_COUNTER"` (portsorch.h:36)
4. `STATS_MODE_READ_AND_CLEAR = "READ_AND_CLEAR"` (固定で setFlexCounterGroupParameter に渡される)
5. `DEFAULT_TELEMETRY_INTERVAL = 120` 秒 (watermarkorch.cpp:9)
6. `CLEAR_PG_HEADROOM_REQUEST = "PG_HEADROOM"` (watermarkorch.cpp:11)
7. `CLEAR_PG_SHARED_REQUEST = "PG_SHARED"` (watermarkorch.cpp:12)
8. `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` (portsorch.cpp:412)
9. `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` (portsorch.cpp:413)
