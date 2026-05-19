# queue-counter Phase F 調査メモ (SET/DEL 副次 DB 書込み)

調査対象: `docs/reference/config-db/queue-counter.md`
調査日: 2026-05-19
調査者: Claude (batch707)

## 調査ソース

- `sonic-swss/orchagent/portsorch.cpp` ref:4305596156d7
- `sonic-swss/orchagent/portsorch.h` ref:4305596156d7
- `sonic-swss/orchagent/flexcounterorch.cpp` ref:4305596156d7

## 副次書込みサマリ

### 1. STATE_DB QUEUE_COUNTER_CAPABILITIES（起動時）

`initCounterCapabilities()` (portsorch.cpp:1850-1921) が起動時に 1 回:
- 全 WRED フラグを `false` で初期化
- SAI `sai_query_stats_capability()` でプラットフォームサポートを確認
- サポート確認分のみ `true` で上書き

キー:
- `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER`
- `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER`
- `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER`
- `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER`

### 2. COUNTERS_DB マッピング（FLEX_COUNTER_TABLE|QUEUE enable 時）

`generateQueueMap()` → `generateQueueMapPerPort()` (portsorch.cpp:8391-8529):
- `COUNTERS_QUEUE_NAME_MAP`: `<port>:<queue_index>` → OID（`m_isQueueMapGenerated` で一度だけ）
- `COUNTERS_QUEUE_PORT_MAP`: `<queue_oid>` → `<port_oid>`
- `COUNTERS_QUEUE_INDEX_MAP`: `<queue_oid>` → `<index>`
- `COUNTERS_QUEUE_TYPE_MAP`: `<queue_oid>` → `SAI_QUEUE_TYPE_*`
- VoQ モード: `COUNTERS_QUEUE_NAME_MAP` の代わりに `COUNTERS_VOQ_NAME_MAP`

### 3. FLEX_COUNTER_DB COUNTER_ID_LIST（enable 時）

`addQueueFlexCountersPerPortPerQueueIndex()` (portsorch.cpp:8592-8614):
- `FLEX_COUNTER_TABLE|QUEUE_STAT_COUNTER:<oid>` : `COUNTER_ID_LIST`
- `FLEX_COUNTER_TABLE|QUEUE_WATERMARK_STAT_COUNTER:<oid>`: `COUNTER_ID_LIST`
- `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE_STAT_COUNTER:<oid>`: `COUNTER_ID_LIST` (ケイパビリティ確認済みのみ)

### 4. ポート削除時の DEL（portsorch.cpp:8780-8816）

- `COUNTERS_QUEUE_NAME_MAP` フィールド削除
- `COUNTERS_QUEUE_PORT_MAP` フィールド削除
- `COUNTERS_QUEUE_TYPE_MAP` フィールド削除
- `COUNTERS_QUEUE_INDEX_MAP` フィールド削除
- FLEX_COUNTER_DB 各グループ `clearCounterIdList()`
