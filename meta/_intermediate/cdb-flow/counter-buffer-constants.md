# counter-buffer — Phase E: 定数・マジックナンバー

調査対象:
- `sonic-swss/orchagent/portsorch.cpp` (L79-93)
- `sonic-swss/orchagent/portsorch.h` (L29-43)
- `sonic-swss/orchagent/bufferorch.h` (L15-34)
- `sonic-swss/orchagent/bufferorch.cpp` (L29-32, L234-250, L358)
- `sonic-swss/orchagent/watermarkorch.cpp` (L9-17)
- `sonic-swss/orchagent/flexcounterorch.cpp` (L44-98)
- `sonic-swss-common/common/schema.h` (L225-333)

---

## FlexCounter グループ名文字列定数

`portsorch.h` および `bufferorch.h` で定義されたグループ名マクロ:

| マクロ定数 | 文字列値 | 定義箇所 |
|-----------|---------|---------|
| `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_STAT_COUNTER"` | portsorch.h:34 |
| `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_WATERMARK_STAT_COUNTER"` | portsorch.h:35 |
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | portsorch.h:36 |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | portsorch.h:37 |
| `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP` | `"PORT_BUFFER_DROP_STAT"` | portsorch.h:31 |
| `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_QUEUE_STAT_COUNTER"` | portsorch.h:42 |
| `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_PORT_STAT_COUNTER"` | portsorch.h:43 |
| `BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"BUFFER_POOL_WATERMARK_STAT_COUNTER"` | bufferorch.h:15 |

## ポーリング間隔マクロ (`#define` / string定数)

### portsorch.cpp (数値 int 型マクロ)

| マクロ | 値 | 利用箇所 |
|-------|---|---------|
| `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS` | `60000` | portsorch.cpp:88 → port_buffer_drop_stat_manager 初期化 |
| `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | portsorch.cpp:90 → queue_stat_manager / wred_queue_stat_manager |
| `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` | portsorch.cpp:91 → queue_watermark_manager |
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` | portsorch.cpp:92 → pg_watermark_manager |
| `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | portsorch.cpp:93 → pg_drop_stat_manager |

### portsorch.h (文字列定数、`setFlexCounterGroupParameter` に渡す)

| マクロ | 値 | 利用箇所 |
|-------|---|---------|
| `QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | portsorch.h:38 → portsorch.cpp:866-867 |
| `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | portsorch.h:39 → portsorch.cpp:872-873 |
| `PG_DROP_FLEX_STAT_COUNTER_POLL_MSECS` | `"10000"` | portsorch.h:40 → portsorch.cpp:884-885 |
| `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS` | `"1000"` | portsorch.h:41 (バッファ系とは無関係) |

### bufferorch.h (文字列定数)

| マクロ | 値 | 利用箇所 |
|-------|---|---------|
| `BUFFER_POOL_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | bufferorch.h:16 → bufferorch.cpp:247-249 |

### flexcounterorch.cpp (数値 int 型マクロ)

| マクロ | 値 | 利用箇所 |
|-------|---|---------|
| `FLEX_COUNTER_DELAY_SEC` | `60` | flexcounterorch.cpp:44 → SelectableTimer 起動遅延 (秒) |

## FLEX_COUNTER_TABLE キー文字列定数

`flexcounterorch.cpp` で定義されたキー文字列:

| マクロ | 文字列値 | `FLEX_COUNTER_TABLE` キー |
|-------|---------|--------------------------|
| `BUFFER_POOL_WATERMARK_KEY` | `"BUFFER_POOL_WATERMARK"` | `FLEX_COUNTER_TABLE\|BUFFER_POOL_WATERMARK` |
| `PORT_BUFFER_DROP_KEY` | `"PORT_BUFFER_DROP"` | `FLEX_COUNTER_TABLE\|PORT_BUFFER_DROP` |
| `QUEUE_KEY` | `"QUEUE"` | `FLEX_COUNTER_TABLE\|QUEUE` |
| `QUEUE_WATERMARK` | `"QUEUE_WATERMARK"` | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` |
| `PG_WATERMARK_KEY` | `"PG_WATERMARK"` | `FLEX_COUNTER_TABLE\|PG_WATERMARK` |
| `PG_DROP_KEY` | `"PG_DROP"` | `FLEX_COUNTER_TABLE\|PG_DROP` |
| `WRED_QUEUE_KEY` | `"WRED_ECN_QUEUE"` | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` |

## COUNTERS_DB フィールド名定数 (schema.h)

| マクロ | 文字列値 | 定義箇所 |
|-------|---------|---------|
| `QUEUE_COUNTER_ID_LIST` | `"QUEUE_COUNTER_ID_LIST"` | schema.h:290 |
| `PG_COUNTER_ID_LIST` | `"PG_COUNTER_ID_LIST"` | schema.h:300 |
| `BUFFER_POOL_COUNTER_ID_LIST` | `"BUFFER_POOL_COUNTER_ID_LIST"` | schema.h:292 |
| `QUEUE_ATTR_ID_LIST` | `"QUEUE_ATTR_ID_LIST"` | schema.h:291 |
| `PG_ATTR_ID_LIST` | `"PG_ATTR_ID_LIST"` | schema.h:301 |
| `QUEUE_PLUGIN_FIELD` | `"QUEUE_PLUGIN_LIST"` | schema.h:325 |
| `PG_PLUGIN_FIELD` | `"PG_PLUGIN_LIST"` | schema.h:331 |
| `BUFFER_POOL_PLUGIN_FIELD` | `"BUFFER_POOL_PLUGIN_LIST"` | schema.h:333 |
| `COUNTERS_QUEUE_NAME_MAP` | `"COUNTERS_QUEUE_NAME_MAP"` | schema.h:225 |
| `COUNTERS_PG_NAME_MAP` | `"COUNTERS_PG_NAME_MAP"` | schema.h:230 |
| `PERIODIC_WATERMARKS_TABLE` | `"PERIODIC_WATERMARKS"` | schema.h:268 |
| `PERSISTENT_WATERMARKS_TABLE` | `"PERSISTENT_WATERMARKS"` | schema.h:269 |
| `USER_WATERMARKS_TABLE` | `"USER_WATERMARKS"` | schema.h:270 |

## bufferorch.h フィールド名文字列定数

BUFFER_POOL / BUFFER_PROFILE の CONFIG_DB フィールド名として使われる文字列定数:

| 定数名 | 文字列値 | 用途 |
|-------|---------|------|
| `buffer_size_field_name` | `"size"` | プール/プロファイルのバッファサイズ |
| `buffer_pool_type_field_name` | `"type"` | `ingress` / `egress` / `both` |
| `buffer_pool_mode_field_name` | `"mode"` | `dynamic` / `static` / `fallback` |
| `buffer_pool_field_name` | `"pool"` | プロファイルが参照するプール名 |
| `buffer_pool_mode_dynamic_value` | `"dynamic"` | dynamic しきい値モード |
| `buffer_pool_mode_static_value` | `"static"` | static しきい値モード |
| `buffer_pool_xoff_field_name` | `"xoff"` | xoff サイズ |
| `buffer_xon_field_name` | `"xon"` | xon サイズ |
| `buffer_xon_offset_field_name` | `"xon_offset"` | xon_offset |
| `buffer_xoff_field_name` | `"xoff"` | xoff サイズ（プロファイル用） |
| `buffer_dynamic_th_field_name` | `"dynamic_th"` | dynamic しきい値 |
| `buffer_static_th_field_name` | `"static_th"` | static しきい値 |
| `buffer_profile_field_name` | `"profile"` | PG/Queue が参照するプロファイル名 |
| `buffer_value_ingress` | `"ingress"` | pool type 値 |
| `buffer_value_egress` | `"egress"` | pool type 値 |
| `buffer_value_both` | `"both"` | pool type 値（egress + ingress 両用プール） |
| `buffer_profile_list_field_name` | `"profile_list"` | ポートのイングレス/エグレスプロファイルリスト |
| `buffer_headroom_type_field_name` | `"headroom_type"` | ヘッドルームタイプ |

## watermarkorch.cpp クリアリクエスト定数

`WATERMARK_CLEAR_REQUEST` 通知の op 文字列として使われるマクロ:

| マクロ | 文字列値 | 意味 |
|-------|---------|------|
| `CLEAR_PG_HEADROOM_REQUEST` | `"PG_HEADROOM"` | PG ヘッドルームウォーターマーク クリア |
| `CLEAR_PG_SHARED_REQUEST` | `"PG_SHARED"` | PG 共有ウォーターマーク クリア |
| `CLEAR_QUEUE_SHARED_UNI_REQUEST` | `"Q_SHARED_UNI"` | ユニキャスト Queue 共有 WM クリア |
| `CLEAR_QUEUE_SHARED_MULTI_REQUEST` | `"Q_SHARED_MULTI"` | マルチキャスト Queue 共有 WM クリア |
| `CLEAR_QUEUE_SHARED_ALL_REQUEST` | `"Q_SHARED_ALL"` | 全 Queue 共有 WM クリア |
| `CLEAR_BUFFER_POOL_REQUEST` | `"BUFFER_POOL"` | バッファプール WM クリア |
| `CLEAR_HEADROOM_POOL_REQUEST` | `"HEADROOM_POOL"` | ヘッドルームプール WM クリア |
| `DEFAULT_TELEMETRY_INTERVAL` | `120` (秒) | テレメトリタイマー初期値 |

## SAI 統計 ID 配列定数

`bufferorch.cpp:29-32` に定義された静的配列:

```cpp
static const vector<sai_buffer_pool_stat_t> bufferPoolWatermarkStatIds = {
    SAI_BUFFER_POOL_STAT_WATERMARK_BYTES,
    SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES
};
```

この配列が `generateBufferPoolWatermarkCounterIdList()` → `startFlexCounterPolling()` に渡され、`BUFFER_POOL_COUNTER_ID_LIST` フィールドとして FLEX_COUNTER_DB に書き込まれる。
