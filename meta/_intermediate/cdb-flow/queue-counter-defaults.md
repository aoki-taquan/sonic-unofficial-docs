# COUNTERS_DB QUEUE カウンタ — コード由来デフォルト調査メモ (Phase A)

調査日: 2026-05-15
対象: COUNTERS_DB の Queue カウンタ専用エントリ（PG は counters-queue.md 参照）

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` (ref: 4305596) — `queue_stat_ids` / `voq_stat_ids` / `queueWatermarkStatIds` / `wred_queue_stat_ids` 定義、`addQueueFlexCountersPerPortPerQueueIndex` / `addQueueWatermarkFlexCountersPerPortPerQueueIndex` 実装
- `sonic-swss/orchagent/portsorch.h` (ref: 4305596) — FlexCounter グループ名定数 (`QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` / `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` / `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP`)、ポーリング間隔文字列定数
- `sonic-utilities/scripts/queuestat` (ref: 39732bc) — `counter_bucket_dict` / `trim_counter_bucket_dict` / `voq_counter_bucket_dict`、COUNTER_TABLE_PREFIX、キュータイプ判定

---

## 1. SAI カウンタフィールドセット（コードハードコード）

### 1-1. 通常カウンタ (queue_stat_ids, portsorch.cpp:389-398)

```cpp
static const vector<sai_queue_stat_t> queue_stat_ids =
{
    SAI_QUEUE_STAT_PACKETS,
    SAI_QUEUE_STAT_BYTES,
    SAI_QUEUE_STAT_DROPPED_PACKETS,
    SAI_QUEUE_STAT_DROPPED_BYTES,
    SAI_QUEUE_STAT_TRIM_PACKETS,
    SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS,
    SAI_QUEUE_STAT_TX_TRIM_PACKETS
};
```

| フィールド | 説明 |
|-----------|------|
| `SAI_QUEUE_STAT_PACKETS` | キューからの送信パケット数（累積） |
| `SAI_QUEUE_STAT_BYTES` | キューからの送信バイト数（累積） |
| `SAI_QUEUE_STAT_DROPPED_PACKETS` | キュードロップパケット数（累積） |
| `SAI_QUEUE_STAT_DROPPED_BYTES` | キュードロップバイト数（累積） |
| `SAI_QUEUE_STAT_TRIM_PACKETS` | トリミング発生パケット数（Packet Trimming 機能） |
| `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` | トリミング後にドロップされたパケット数 |
| `SAI_QUEUE_STAT_TX_TRIM_PACKETS` | トリミング後に送信されたパケット数 |

### 1-2. VoQ 専用追加フィールド (voq_stat_ids, portsorch.cpp:399-402)

```cpp
static const vector<sai_queue_stat_t> voq_stat_ids =
{
    SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS
};
```

| フィールド | 説明 |
|-----------|------|
| `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` | Credit Watchdog により削除されたパケット数（VoQ システム専用） |

VoQ モードでは `addQueueFlexCountersPerPortPerQueueIndex(port, queueIndex, voq=true, queueType)` が呼ばれ、`queue_stat_ids` + `voq_stat_ids` が合算される（portsorch.cpp:8597-8614）。

### 1-3. ウォーターマークカウンタ (queueWatermarkStatIds, portsorch.cpp:405-408)

```cpp
static const vector<sai_queue_stat_t> queueWatermarkStatIds =
{
    SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES,
};
```

| フィールド | 説明 | StatsMode |
|-----------|------|-----------|
| `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` | 共有バッファ使用量ウォーターマーク（バイト） | READ_AND_CLEAR |

### 1-4. WRED/ECN カウンタ (wred_queue_stat_ids, portsorch.cpp:429-435)

```cpp
static const vector<sai_queue_stat_t> wred_queue_stat_ids =
{
    SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS,
    SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES,
    SAI_QUEUE_STAT_WRED_DROPPED_PACKETS,
    SAI_QUEUE_STAT_WRED_DROPPED_BYTES
};
```

| フィールド | 説明 |
|-----------|------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | WRED ECN マーキングパケット数 |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | WRED ECN マーキングバイト数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | WRED ドロップパケット数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | WRED ドロップバイト数 |

---

## 2. FlexCounter グループ定数とポーリング間隔

portsorch.h:34-42、portsorch.cpp:90-91:

```cpp
// portsorch.h
#define QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_STAT_COUNTER"           // :34
#define QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_WATERMARK_STAT_COUNTER"  // :35
#define WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "WRED_ECN_QUEUE_STAT_COUNTER"       // :42
#define QUEUE_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS "60000"                  // :38

// portsorch.cpp
#define QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   10000                   // :90
#define QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS   60000         // :91
```

| FlexCounter グループ名 | CONFIG_DB キー | StatsMode | コードデフォルト ms |
|--------------------|------------|-----------|----------------|
| `QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE` | READ | **10000** |
| `QUEUE_WATERMARK_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | READ_AND_CLEAR | **60000** |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | READ | **10000** |

---

## 3. キータイプ体系 (queuestat:95-102)

```python
QUEUE_TYPE_MC  = 'MC'   # SAI_QUEUE_TYPE_MULTICAST
QUEUE_TYPE_UC  = 'UC'   # SAI_QUEUE_TYPE_UNICAST
QUEUE_TYPE_ALL = 'ALL'  # SAI_QUEUE_TYPE_ALL
QUEUE_TYPE_VOQ = 'VOQ'  # SAI_QUEUE_TYPE_UNICAST_VOQ
```

`COUNTERS_QUEUE_TYPE_MAP` の値が `SAI_QUEUE_TYPE_MULTICAST` のキューには同じ OID 空間に `SAI_QUEUE_STAT_*` が書き込まれる（type 別の別テーブルはない）。

---

## 4. コード由来挙動まとめ

| 挙動種別 | 内容 | 証拠 |
|---------|------|------|
| フィールドセット固定 | `queue_stat_ids` はソースコードにハードコード。CONFIG_DB / YANG で変更不可 | portsorch.cpp:389-398 |
| ウォーターマーク READ_AND_CLEAR | ポーリングごとに SAI 側のウォーターマークレジスタがリセットされる | portsorch.cpp:735 |
| WRED ケイパビリティチェック必須 | `checkWredCapability()` が SAI クエリを実施、未サポートならフィールドが COUNTERS: に現れない | portsorch.cpp:1894-1909 |
| VoQ モードで voq_stat_ids 合算 | `voq=true` フラグで `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` が自動追加 | portsorch.cpp:8601-8614 |
| Packet Trimming フィールド常時投入 | TRIM_PACKETS / DROPPED_TRIM_PACKETS / TX_TRIM_PACKETS は Trimming 有効設定に関係なく `queue_stat_ids` に含まれる | portsorch.cpp:395-397 |
| `isQueueMapGenerated` 冪等ガード | `generateQueueMap()` は一度だけ実行。orchagent 再起動時に重複書き込みなし | portsorch.cpp:8393-8396 |
