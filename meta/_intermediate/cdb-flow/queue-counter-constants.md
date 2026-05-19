# COUNTERS_DB QUEUE カウンタ — Phase E ハードコード定数調査ノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS:<oid>`（QUEUE カウンタ）
調査日: 2026-05-19
スキャン範囲: `portsorch.h` L34-42、`portsorch.cpp` L87-93, L734-739、`flexcounterorch.cpp` L44-63

---

## 検出した定数一覧

### 1. FlexCounter グループ名定数 (portsorch.h)

```cpp
// portsorch.h:34-35, 42
#define QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_STAT_COUNTER"
#define QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_WATERMARK_STAT_COUNTER"
#define WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "WRED_ECN_QUEUE_STAT_COUNTER"
```

これらは FLEX_COUNTER_DB における FlexCounter グループ識別子。syncd 側の `FlexCounter` クラスもこの文字列でグループを検索するため、両者が一致していなければカウンタポーリングが機能しない。CONFIG_DB の `FLEX_COUNTER_TABLE` キー名とは別物（`FLEX_COUNTER_TABLE|QUEUE` の `QUEUE` 部分は flexcounterorch 内部の照合キー）。

### 2. ポーリング間隔定数 (portsorch.cpp)

```cpp
// portsorch.cpp:90-93
#define QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   10000
#define QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000
#define PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000
#define PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   10000
```

PortsOrch コンストラクタ (`portsorch.cpp:734-739`) で FlexCounter マネージャを初期化する際に使用:

```cpp
// portsorch.cpp:734-739
queue_stat_manager(QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ,
    QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false),
queue_watermark_manager(QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ_AND_CLEAR,
    QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false),
// ...
wred_queue_stat_manager(WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ,
    QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false),  // ← WRED は QUEUE 間隔を共用
```

WRED_ECN_QUEUE グループは専用の間隔定数を持たず `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS`（10000 ms）を共用する点に注意。

文字列版も存在（setFlexCounterGroupParameter に渡す用途）:

```cpp
// portsorch.h:38
#define QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS "60000"
```

### 3. CONFIG_DB キー照合文字列 (flexcounterorch.cpp)

```cpp
// flexcounterorch.cpp:51-63
#define QUEUE_KEY        "QUEUE"
#define QUEUE_WATERMARK  "QUEUE_WATERMARK"
#define WRED_QUEUE_KEY   "WRED_ECN_QUEUE"
```

`FlexCounterOrch::doTask()` が `FLEX_COUNTER_TABLE` のエントリを switch/if-else で照合する際の文字列。`FLEX_COUNTER_TABLE|QUEUE` の `QUEUE` 部分（`key` 変数）が `QUEUE_KEY` と一致したときのみ `addQueueFlexCounters()` が呼ばれる。

### 4. warm-reboot 遅延定数 (flexcounterorch.cpp)

```cpp
// flexcounterorch.cpp:44
#define FLEX_COUNTER_DELAY_SEC 60
```

cold boot では `m_delayTimerExpired = true` で即座に解除。warm-reboot では 60 秒間 `doTask()` をブロックし、COUNTERS_DB のキュー統計更新が遅延する。

---

## 外部変更可否サマリ

| 定数 | 変更可否 | 手段 |
|------|---------|------|
| FlexCounter グループ名 | 不可 | ソースコード修正 + 再ビルド |
| ポーリング間隔デフォルト | 可 | `counterpoll queue interval <ms>` |
| CONFIG_DB キー照合文字列 | 不可 | ソースコード修正 + 再ビルド |
| warm-reboot 遅延秒数 | 不可 | ソースコード修正 + 再ビルド |
