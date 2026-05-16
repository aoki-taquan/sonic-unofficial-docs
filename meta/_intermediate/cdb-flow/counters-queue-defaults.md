# COUNTERS_DB QUEUE / PG カウンタ フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: COUNTERS_DB の Queue / Priority Group カウンタ関連テーブル群

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` — queue_stat_ids / queueWatermarkStatIds / ingressPriorityGroupDropStatIds / ingressPriorityGroupWatermarkStatIds 定義、generateQueueMapPerPort / generatePriorityGroupMapPerPort / addQueueFlexCountersPerPortPerQueueIndex / addPriorityGroupFlexCountersPerPortPerPgIndex 実装
- `sonic-swss/orchagent/portsorch.h` — flex counter group 名定数、FlexCounterTaggedCachedManager 宣言
- `sonic-swss-common/common/schema.h` — COUNTERS_TABLE / COUNTERS_QUEUE_NAME_MAP / COUNTERS_PG_NAME_MAP / COUNTERS_QUEUE_PORT_MAP / COUNTERS_QUEUE_INDEX_MAP / COUNTERS_QUEUE_TYPE_MAP / COUNTERS_PG_PORT_MAP / COUNTERS_PG_INDEX_MAP / PERIODIC_WATERMARKS_TABLE / PERSISTENT_WATERMARKS_TABLE / USER_WATERMARKS_TABLE 定義
- `sonic-utilities/scripts/queuestat` — SAI_QUEUE_STAT_* 列挙、COUNTER_TABLE_PREFIX 参照パターン
- `sonic-utilities/scripts/pg-drop` — SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS 参照、counterpoll PG_DROP 有効チェック
- `sonic-utilities/scripts/watermarkstat` — PERSISTENT_WATERMARKS: / PERIODIC_WATERMARKS: / USER_WATERMARKS: テーブルプレフィクス参照
- `sonic-sairedis/syncd/FlexCounter.cpp` — PG_COUNTER_ID_LIST / COUNTERS_TABLE への書き込み

---

## 1. COUNTERS_DB テーブル体系（コード由来）

### 1-1. ベースカウンタテーブル

| Redis テーブル定数 | 実際の Redis キー | 書き込み主体 | 読み取り主体 |
|------------------|-----------------|------------|------------|
| `COUNTERS_TABLE` ("COUNTERS") | `COUNTERS:<OID>` | syncd FlexCounter | queuestat / pg-drop / portstat |
| `COUNTERS_QUEUE_NAME_MAP` | `COUNTERS_QUEUE_NAME_MAP` | portsorch.generateQueueMapPerPort | queuestat / watermarkstat |
| `COUNTERS_VOQ_NAME_MAP` | `COUNTERS_VOQ_NAME_MAP` | portsorch.generateQueueMapPerPort (voq) | queuestat |
| `COUNTERS_QUEUE_PORT_MAP` | `COUNTERS_QUEUE_PORT_MAP` | portsorch.generateQueueMapPerPort | queuestat / pg-drop |
| `COUNTERS_QUEUE_INDEX_MAP` | `COUNTERS_QUEUE_INDEX_MAP` | portsorch.generateQueueMapPerPort | queuestat / watermarkstat |
| `COUNTERS_QUEUE_TYPE_MAP` | `COUNTERS_QUEUE_TYPE_MAP` | portsorch.generateQueueMapPerPort | queuestat / watermarkstat |
| `COUNTERS_PG_NAME_MAP` | `COUNTERS_PG_NAME_MAP` | portsorch.generatePriorityGroupMapPerPort | pg-drop / watermarkstat |
| `COUNTERS_PG_PORT_MAP` | `COUNTERS_PG_PORT_MAP` | portsorch.generatePriorityGroupMapPerPort | pg-drop |
| `COUNTERS_PG_INDEX_MAP` | `COUNTERS_PG_INDEX_MAP` | portsorch.generatePriorityGroupMapPerPort | pg-drop / watermarkstat |

### 1-2. ウォーターマークテーブル

| Redis テーブル定数 | 実際の Redis キープレフィクス | 書き込み主体 |
|------------------|--------------------------|------------|
| `PERIODIC_WATERMARKS_TABLE` | `PERIODIC_WATERMARKS:<OID>` | syncd FlexCounter (READ_AND_CLEAR モード) |
| `PERSISTENT_WATERMARKS_TABLE` | `PERSISTENT_WATERMARKS:<OID>` | syncd FlexCounter |
| `USER_WATERMARKS_TABLE` | `USER_WATERMARKS:<OID>` | watermarkcfg clear コマンド経由 |

---

## 2. SAI カウンタフィールド（コードハードコード由来）

### 2-1. Queue 通常カウンタ (QUEUE_STAT_COUNTER グループ)

portsorch.cpp:389-398 の `queue_stat_ids` より:

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

COUNTERS:<OID> に書き込まれる field:

| field 名 | 説明 |
|---------|------|
| `SAI_QUEUE_STAT_PACKETS` | 送信パケット数（合計） |
| `SAI_QUEUE_STAT_BYTES` | 送信バイト数（合計） |
| `SAI_QUEUE_STAT_DROPPED_PACKETS` | キュードロップパケット数 |
| `SAI_QUEUE_STAT_DROPPED_BYTES` | キュードロップバイト数 |
| `SAI_QUEUE_STAT_TRIM_PACKETS` | トリミング発生パケット数 |
| `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` | トリミング後ドロップパケット数 |
| `SAI_QUEUE_STAT_TX_TRIM_PACKETS` | トリミング後送信パケット数 |

### 2-2. VoQ カウンタ（voq モード専用追加フィールド）

portsorch.cpp:399-402 の `voq_stat_ids` より:

| field 名 | 説明 |
|---------|------|
| `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` | Credit Watchdog により削除されたパケット数 |

### 2-3. Queue ウォーターマークカウンタ (QUEUE_WATERMARK_STAT_COUNTER グループ)

portsorch.cpp:405-408 の `queueWatermarkStatIds` より:

| field 名 | 書き込み先テーブル | 説明 |
|---------|----------------|------|
| `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` | `COUNTERS:<OID>` (READ_AND_CLEAR) | 共有バッファ使用量ウォーターマーク（バイト） |

### 2-4. WRED/ECN Queue カウンタ (WRED_ECN_QUEUE_STAT_COUNTER グループ)

portsorch.cpp:429-435 の `wred_queue_stat_ids` より:

| field 名 | 説明 |
|---------|------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | WRED ECN マーキングされたパケット数 |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | WRED ECN マーキングされたバイト数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | WRED ドロップパケット数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | WRED ドロップバイト数 |

### 2-5. PG ドロップカウンタ (PG_DROP_STAT_COUNTER グループ)

portsorch.cpp:416-419 の `ingressPriorityGroupDropStatIds` より:

| field 名 | 説明 |
|---------|------|
| `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` | PG イングレスドロップパケット数 |

### 2-6. PG ウォーターマークカウンタ (PG_WATERMARK_STAT_COUNTER グループ)

portsorch.cpp:410-414 の `ingressPriorityGroupWatermarkStatIds` より:

| field 名 | 書き込み先テーブル | 説明 |
|---------|----------------|------|
| `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` | `COUNTERS:<OID>` (READ_AND_CLEAR) | XOFF リザーブ領域ウォーターマーク（バイト） |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` | `COUNTERS:<OID>` (READ_AND_CLEAR) | 共有バッファ使用量ウォーターマーク（バイト） |

---

## 3. FlexCounter グループ定数とポーリング間隔（コードハードコード）

portsorch.h:34-42 および portsorch.cpp:90-93:

| FlexCounter グループ名 | 定数名 | StatsMode | ハードコードポーリング間隔 |
|--------------------|------|-----------|----------------------|
| `QUEUE_STAT_COUNTER` | `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `READ` | 10000 ms |
| `QUEUE_WATERMARK_STAT_COUNTER` | `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `READ_AND_CLEAR` | 60000 ms |
| `PG_WATERMARK_STAT_COUNTER` | `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `READ_AND_CLEAR` | 60000 ms |
| `PG_DROP_STAT_COUNTER` | `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `READ` | 10000 ms |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `READ` | 10000 ms |

**重要**: これらのポーリング間隔は orchagent コンストラクタのデフォルト値として渡されるが、FLEX_COUNTER_TABLE 経由で `POLL_INTERVAL` を設定することで CONFIG_DB から上書き可能（counterpoll CLI 経由が推奨）。

---

## 4. COUNTERS_QUEUE_NAME_MAP のキー形式

portsorch.cpp:8464-8475 より:

- **通常キュー**: `<port_alias>:<queue_index>` 例: `Ethernet0:0`
- **VoQ**: `<system_port_alias>:<queue_index>` 例: `Linecard1|ASIC0|Ethernet0:0`

各キーの値は SAI OID（16 進数文字列）。

---

## 5. COUNTERS_PG_NAME_MAP のキー形式

portsorch.cpp:8871-8873 より:

- **キー形式**: `<port_alias>:<pg_index>` 例: `Ethernet0:3`

---

## 6. 暗黙デフォルト・コード由来挙動まとめ

| 挙動種別 | 内容 | 証拠ファイル |
|---------|------|-----------|
| カウンタフィールド固定 | queue_stat_ids / queueWatermarkStatIds / ingressPriorityGroupDropStatIds / ingressPriorityGroupWatermarkStatIds はコードにハードコード。YANG や CONFIG_DB では変更不可 | portsorch.cpp:389-419 |
| ウォーターマーク READ_AND_CLEAR | QUEUE_WATERMARK / PG_WATERMARK グループは `StatsMode::READ_AND_CLEAR` で動作。SAI から読み取るたびにハードウェアカウンタがリセットされる。PERIODIC/PERSISTENT/USER テーブルへの分岐は syncd 側が処理 | portsorch.cpp:735-736 |
| WRED 検出時のみ追加 | WRED/ECN 統計（SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS 等）は `checkWredCapability()` が SAI から WRED ケイパビリティを問い合わせ、サポート確認後にのみ FlexCounter に追加（portsorch.cpp:1894-1909）。未サポート ASIC では COUNTERS: に field 自体が存在しない | portsorch.cpp:1894-1909 |
| VoQ カウンタ常時 enable | VoQ システムでは `addQueueFlexCountersPerPortPerQueueIndex(port, queueIndex, true, queueType)` が buffer queue config 不要で常時呼び出される。CONFIG_DB の FLEX_COUNTER_STATUS 設定に関係なく有効 | portsorch.cpp:8499 |
| PG カウンタ条件付き追加 | createPortBufferPgCounters は `flexCounterOrch->getPgCountersState()` / `getPgWatermarkCountersState()` を確認してから追加。FLEX_COUNTER_TABLE|PG_DROP / PG_WATERMARK の STATUS が enable の場合のみ追加 | portsorch.cpp:8924-8934 |
| isQueueMapGenerated ガード | `generateQueueMap()` は `m_isQueueMapGenerated` フラグで一度だけ実行（冪等性）。再起動時に重複エントリが COUNTERS_DB に蓄積しない | portsorch.cpp:8393-8396 |
| allPortsReady 前はスキップ | `addQueueFlexCounters` / `addPriorityGroupFlexCounters` は全ポート ready 後に呼ばれる。ready 前に FLEX_COUNTER_TABLE を enable にしても、FlexCounter は設定されない（後から一括適用） | portsorch.cpp の呼び出しチェーン全体 |

---

## 7. 証拠リンク

- `sonic-swss/orchagent/portsorch.cpp:389-435` — SAI カウンタ ID ベクタ定義
- `sonic-swss/orchagent/portsorch.cpp:727-750` — FlexCounterManager コンストラクタ引数（ポーリング間隔・StatsMode）
- `sonic-swss/orchagent/portsorch.cpp:8446-8531` — generateQueueMapPerPort
- `sonic-swss/orchagent/portsorch.cpp:8592-8620` — addQueueFlexCountersPerPortPerQueueIndex（queue_stat_ids 投入）
- `sonic-swss/orchagent/portsorch.cpp:8858-8886` — generatePriorityGroupMapPerPort
- `sonic-swss/orchagent/portsorch.cpp:8992-8996` — addPriorityGroupFlexCountersPerPortPerPgIndex（PG drop stat 投入）
- `sonic-swss/orchagent/portsorch.cpp:9048-9052` — addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex（PG watermark 投入）
- `sonic-swss/orchagent/portsorch.h:34-42` — FlexCounter グループ名定数
- `sonic-swss-common/common/schema.h:223-270` — COUNTERS_DB テーブル定数
- `sonic-utilities/scripts/queuestat:77-110` — counter_bucket_dict（SAI フィールド名とカラム位置）
- `sonic-utilities/scripts/pg-drop:95-101` — SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS 参照
- `sonic-utilities/scripts/watermarkstat:58-71` — PERIODIC/PERSISTENT/USER テーブルプレフィクス
