# COUNTERS_DB QUEUE / PG カウンタ — Phase E ハードコード定数スキャンノート

対象グループ: QUEUE / QUEUE_WATERMARK / PG_DROP / PG_WATERMARK / WRED_ECN_QUEUE  
スキャン対象: `sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/portsorch.h`, `sonic-swss/orchagent/flexcounterorch.cpp`, `sonic-swss-common/common/schema.h`

---

## 1. FlexCounter グループ名定数（`portsorch.h` / `flexcounterorch.cpp`）

| マクロ名 | 文字列値 | ファイル | 行 |
|---------|---------|---------|-----|
| `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_STAT_COUNTER"` | `portsorch.h` | 34 |
| `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_WATERMARK_STAT_COUNTER"` | `portsorch.h` | 35 |
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | `portsorch.h` | 36 |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | `portsorch.h` | 37 |
| `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_QUEUE_STAT_COUNTER"` | `portsorch.h` / `flexcounterorch.cpp` | 42 / 42 |
| `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_PORT_STAT_COUNTER"` | `portsorch.h` / `flexcounterorch.cpp` | 43 / 43 |

これらはプロセス起動時にハードコードで FlexCounter_DB のグループキーとして使用される。CONFIG_DB / YANG から変更不可。

## 2. ポーリング間隔定数（`portsorch.cpp` / `portsorch.h`）

| マクロ名 | 値 | 対象グループ | 収集モード | ファイル | 行 |
|---------|-----|------------|---------|---------|-----|
| `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | QUEUE_STAT_COUNTER | READ | `portsorch.cpp` | 90 |
| `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` ms | QUEUE_WATERMARK_STAT_COUNTER | READ_AND_CLEAR | `portsorch.cpp` | 91 |
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` ms | PG_WATERMARK_STAT_COUNTER | READ_AND_CLEAR | `portsorch.cpp` | 92 |
| `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | PG_DROP_STAT_COUNTER | READ | `portsorch.cpp` | 93 |
| `QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | QUEUE_WATERMARK (plugin) | READ_AND_CLEAR | `portsorch.h` | 38 |
| `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | PG_WATERMARK (plugin) | READ_AND_CLEAR | `portsorch.h` | 39 |
| `PG_DROP_FLEX_STAT_COUNTER_POLL_MSECS` | `"10000"` | PG_DROP | READ | `portsorch.h` | 40 |

WRED_ECN_QUEUE のポーリング間隔は `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS`（10000 ms）と共用される（`portsorch.cpp:739`）。  
CONFIG_DB の `FLEX_COUNTER_TABLE|<GROUP>|POLL_INTERVAL` で上書き可能だが、初期値は上記定数から FlexCounter_DB に書き込まれる。

## 3. Warm-reboot 遅延定数（`flexcounterorch.cpp`）

| マクロ名 | 値 | 用途 | ファイル | 行 |
|---------|-----|------|---------|-----|
| `FLEX_COUNTER_DELAY_SEC` | `60` 秒 | Warm-reboot 時に全 FlexCounter 処理をブロックする SelectableTimer の秒数 | `flexcounterorch.cpp` | 44 |

Cold boot では `m_delayTimerExpired = true` に初期化されてこの遅延は適用されない（`flexcounterorch.cpp:136`）。

## 4. SAI カウンタ ID 静的配列（`portsorch.cpp`）

### queue_stat_ids（QUEUE_STAT_COUNTER グループ）

```
static const vector<sai_queue_stat_t> queue_stat_ids = {
    SAI_QUEUE_STAT_PACKETS,
    SAI_QUEUE_STAT_BYTES,
    SAI_QUEUE_STAT_DROPPED_PACKETS,
    SAI_QUEUE_STAT_DROPPED_BYTES,
    SAI_QUEUE_STAT_TRIM_PACKETS,
    SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS,
    SAI_QUEUE_STAT_TX_TRIM_PACKETS
};
// portsorch.cpp:389-397
// + SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS は voq 専用 (portsorch.cpp:401)
```

### voq_stat_ids（VoQ 専用）

```
static const vector<sai_queue_stat_t> voq_stat_ids = {
    SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS
};
// portsorch.cpp:399-402
```

### queueWatermarkStatIds（QUEUE_WATERMARK グループ）

```
static const vector<sai_queue_stat_t> queueWatermarkStatIds = {
    SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES,
};
// portsorch.cpp:405-408
```

### ingressPriorityGroupWatermarkStatIds（PG_WATERMARK グループ）

```
static const vector<sai_ingress_priority_group_stat_t> ingressPriorityGroupWatermarkStatIds = {
    SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES,
    SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES,
};
// portsorch.cpp:410-414
```

### ingressPriorityGroupDropStatIds（PG_DROP グループ）

```
static const vector<sai_ingress_priority_group_stat_t> ingressPriorityGroupDropStatIds = {
    SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS
};
// portsorch.cpp:416-419
```

### wred_queue_stat_ids（WRED_ECN_QUEUE グループ）

```
static const vector<sai_queue_stat_t> wred_queue_stat_ids = {
    SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS,
    SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES,
    SAI_QUEUE_STAT_WRED_DROPPED_PACKETS,
    SAI_QUEUE_STAT_WRED_DROPPED_BYTES
};
// portsorch.cpp:429-434
```

## 5. COUNTERS_DB テーブル名定数（`schema.h`）

| マクロ名 | 文字列値 | 行 |
|---------|---------|-----|
| `COUNTERS_QUEUE_NAME_MAP` | `"COUNTERS_QUEUE_NAME_MAP"` | 225 |
| `COUNTERS_VOQ_NAME_MAP` | `"COUNTERS_VOQ_NAME_MAP"` | 226 |
| `COUNTERS_QUEUE_PORT_MAP` | `"COUNTERS_QUEUE_PORT_MAP"` | 227 |
| `COUNTERS_QUEUE_INDEX_MAP` | `"COUNTERS_QUEUE_INDEX_MAP"` | 228 |
| `COUNTERS_QUEUE_TYPE_MAP` | `"COUNTERS_QUEUE_TYPE_MAP"` | 229 |
| `COUNTERS_PG_NAME_MAP` | `"COUNTERS_PG_NAME_MAP"` | 230 |
| `COUNTERS_PG_PORT_MAP` | `"COUNTERS_PG_PORT_MAP"` | 231 |
| `COUNTERS_PG_INDEX_MAP` | `"COUNTERS_PG_INDEX_MAP"` | 232 |
| `PERIODIC_WATERMARKS_TABLE` | `"PERIODIC_WATERMARKS"` | 268 |
| `PERSISTENT_WATERMARKS_TABLE` | `"PERSISTENT_WATERMARKS"` | 269 |
| `USER_WATERMARKS_TABLE` | `"USER_WATERMARKS"` | 270 |
| `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` | `"QUEUE_COUNTER_CAPABILITIES"` | 528 |

## 6. StatsMode（READ vs READ_AND_CLEAR）

| グループ | StatsMode | ポーリング間隔 | 証跡 |
|---------|-----------|-------------|------|
| `QUEUE_STAT_COUNTER` | `READ` | 10000 ms | `portsorch.cpp:734` |
| `QUEUE_WATERMARK_STAT_COUNTER` | `READ_AND_CLEAR` | 60000 ms | `portsorch.cpp:735` |
| `PG_WATERMARK_STAT_COUNTER` | `READ_AND_CLEAR` | 60000 ms | `portsorch.cpp:736` |
| `PG_DROP_STAT_COUNTER` | `READ` | 10000 ms | `portsorch.cpp:737` |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `READ` | 10000 ms | `portsorch.cpp:739` |

`READ_AND_CLEAR`: syncd が SAI からポーリングするたびにハードウェアのウォーターマークレジスタをゼロクリアする。`PERIODIC_WATERMARKS` / `PERSISTENT_WATERMARKS` / `USER_WATERMARKS` への振り分けは syncd 側の Lua スクリプト（`watermark_stat.lua`）が担当する。

## スキャン証跡

- `portsorch.cpp:83-93`（ポーリング間隔 #define）
- `portsorch.cpp:389-434`（SAI カウンタ ID 静的配列）
- `portsorch.cpp:727-739`（FlexCounterManager コンストラクタ引数で間隔・モードを確認）
- `portsorch.cpp:866-886`（setFlexCounterGroupParameter 呼び出しで WATERMARK/PG_DROP グループのポーリング間隔設定）
- `portsorch.h:29-43`（FlexCounter グループ名マクロ）
- `flexcounterorch.cpp:34-44`（FlexCounter グループ名マクロ、FLEX_COUNTER_DELAY_SEC）
- `schema.h:225-270,528`（COUNTERS_DB テーブル名マクロ）
