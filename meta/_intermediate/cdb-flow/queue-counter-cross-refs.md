# COUNTERS_DB QUEUE カウンタ — Phase C 暗黙参照テーブル調査メモ

調査日: 2026-05-18
対象ページ: `docs/reference/config-db/queue-counter.md`

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` (ref: 4305596156d7) — `initializeQueuesBulk()`, `generateQueueMap()`, `generateQueueMapPerPort()`, `addQueueFlexCountersPerPortPerQueueIndex()`, `createPortBufferQueueCounters()`
- `sonic-swss/orchagent/flexcounterorch.cpp` (ref: 4305596156d7) — `FlexCounterOrch::doTask()`, `handleDeviceMetadataTable()`, `getQueueConfigurations()`

---

## 検出した暗黙参照関係

### 1. CONFIG_DB → FlexCounter

| テーブル | フィールド/キー | 方向 | 内容 | 証拠 |
|---------|--------------|------|------|------|
| `FLEX_COUNTER_TABLE\|QUEUE` | `FLEX_COUNTER_STATUS` | READ | enable で `addQueueFlexCounters()` 呼び出し、disable で `clearQueueFlexCounters()` | `flexcounterorch.cpp:247-252` |
| `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | `FLEX_COUNTER_STATUS` | READ | enable で `addQueueWatermarkFlexCounters()` 呼び出し | `flexcounterorch.cpp:258-264` |
| `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | `FLEX_COUNTER_STATUS` | READ | enable で `addWredQueueFlexCounters(getQueueConfigurations())` 呼び出し | `flexcounterorch.cpp:276-281` |
| `BUFFER_QUEUE` | 全エントリ | READ | `create_only_config_db_buffers=true` 時に非ゼロプロファイルのキューのみ対象に絞り込み | `flexcounterorch.cpp:544-554` |
| `DEVICE_METADATA\|localhost` | `create_only_config_db_buffers` | READ | 起動時 1 回 + `handleDeviceMetadataTable()` で動的更新 | `flexcounterorch.cpp:106-124, 488-521` |

### 2. COUNTERS_DB への書き込み（本テーブルが書き込むテーブル）

| テーブル | 方向 | 内容 | 証拠 |
|---------|------|------|------|
| `COUNTERS_QUEUE_NAME_MAP` | WRITE | `<port_alias>:<queue_index>` → `<oid>` マッピング。`generateQueueMap()` が初回のみ実行（`m_isQueueMapGenerated` ガード） | `portsorch.cpp:8391-8443` |
| `COUNTERS_QUEUE_PORT_MAP` | WRITE | `<queue_oid>` → `<port_oid>` 逆引き | `portsorch.cpp:780` |
| `COUNTERS_QUEUE_INDEX_MAP` | WRITE | `<queue_oid>` → `<queue_index>` 逆引き | `portsorch.cpp:781` |
| `COUNTERS_QUEUE_TYPE_MAP` | WRITE | `<queue_oid>` → `SAI_QUEUE_TYPE_*` 逆引き | `portsorch.cpp:782` |
| `COUNTERS:<oid>` | WRITE（syncd 経由） | SAI カウンタ値。portsorch が FLEX_COUNTER_DB に登録した ID リストを syncd がポーリング | portsorch SAI FlexCounter 機構 |

### 3. SAI 依存

| 参照先 | 方向 | 内容 | 証拠 |
|--------|------|------|------|
| `SAI_PORT_ATTR_QOS_QUEUE_LIST` | READ | `initializeQueuesBulk()` が各ポートの Queue OID を SAI から取得 | `portsorch.cpp:6583-6598` |
| `SAI_QUEUE_ATTR_*` ケイパビリティ | READ | `checkWredCapability()` が WRED 統計サポートを確認（非サポート ASIC は silent 未登録） | `portsorch.cpp:1894-1909` |

---

## 特記事項

- `FLEX_COUNTER_TABLE` が disable でも `COUNTERS_QUEUE_NAME_MAP` 等のマッピングテーブルは削除されない
- VoQ モード (`gMySwitchType == "voq"`) では `FLEX_COUNTER_TABLE|QUEUE` の enable 状態に関係なく egress queue カウンタが登録される (`portsorch.cpp:8499-8514`)
- `create_only_config_db_buffers = false`（デフォルト）では `BUFFER_QUEUE` の内容に依存しない（全キューが対象）
