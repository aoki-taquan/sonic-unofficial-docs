# counter-buffer Phase C — 暗黙参照テーブル (cross-refs)

Generated: 2026-05-17
Target doc: docs/reference/config-db/counter-buffer.md

調査範囲:
- `sonic-swss/orchagent/bufferorch.cpp` (全行精読: L53-56, L232-361, L540-547, L2040-2099)
- `sonic-swss/orchagent/flexcounterorch.cpp` (全行精読: L35, L44-46, L80-81, L106-124, L149-152, L156-169, L287-289, L485-516, L544-554, L620-623)
- `sonic-swss/orchagent/portsorch.cpp` (参照箇所: L6583-6598, L8391-8396, L8730-8745, L8925-8933)

---

## 暗黙参照マップ

以下はすべて実装レベルの暗黙参照（YANG leafref なし）。

### 1. FLEX_COUNTER_TABLE — enable ゲート

| 参照先キー | 参照方向 | 条件 | 証跡 |
|-----------|---------|------|------|
| `FLEX_COUNTER_TABLE\|BUFFER_POOL_WATERMARK` | 読み取り（状態確認）→ トリガー | `FlexCounterOrch::doTask()` が `BUFFER_POOL_WATERMARK_KEY` と `FLEX_COUNTER_STATUS=enable` の組み合わせを検知し `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` を呼び出す。`disable` 受信時は逆に `clearBufferPoolWatermarkCounterIdList()` が呼ばれる | `flexcounterorch.cpp:287-289` |
| `FLEX_COUNTER_TABLE\|QUEUE` | 読み取り（状態確認）→ ゲート | `getQueueCountersState()=true` のときのみ Queue カウンタ FLEX_COUNTER_DB 登録。`false` の場合は `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` へのマッピングのみ | `portsorch.cpp:8731`, `flexcounterorch.cpp:453` |
| `FLEX_COUNTER_TABLE\|PG_DROP` | 読み取り（状態確認）→ ゲート | `getPgCountersState()=true` のときのみ PG ドロップカウンタを登録 | `portsorch.cpp:8925-8927` |
| `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | 読み取り（状態確認）→ ゲート | `getQueueWatermarkCountersState()=true` のときのみ Queue Watermark を登録 | `portsorch.cpp:8736-8738` |
| `FLEX_COUNTER_TABLE\|PG_WATERMARK` | 読み取り（状態確認）→ ゲート | `getPgWatermarkCountersState()=true` のときのみ PG Watermark を登録 | `portsorch.cpp:8930-8933` |
| `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | 読み取り（状態確認）→ ゲート | `getWredQueueCountersState()=true` のときのみ WRED カウンタを登録 | `portsorch.cpp:8741-8745` |

### 2. DEVICE_METADATA — バッファモード分岐フラグ

| 参照先キー | 参照方向 | 条件 | 証跡 |
|-----------|---------|------|------|
| `DEVICE_METADATA\|localhost` フィールド `create_only_config_db_buffers` | 読み取り（起動時 + 動的更新）→ モード分岐 | `FlexCounterOrch` コンストラクタで 1 回読込み `m_createOnlyConfigDbBuffers` にキャッシュ。`true` の場合 `getQueueConfigurations()` / `getPgConfigurations()` は非ゼロプロファイル付きのキュー/PG のみを FlexCounter 対象とする。`false`（デフォルト）または VoQ では全対象。実行時変更は `handleDeviceMetadataTable()` で反映されるが**既登録カウンタは変更されない** | `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:508-513` |

### 3. APP_DB:BUFFER_POOL_TABLE — プール OID ソース

| 参照先テーブル | 参照方向 | 条件 | 証跡 |
|--------------|---------|------|------|
| `APP_DB:BUFFER_POOL_TABLE\|<pool_name>` | 読み取り → SAI OID 生成 | `BufferOrch::processBufferPool()` が `APP_BUFFER_POOL_TABLE` を subscribe し、SAI `create_buffer_pool` でプール OID を生成。生成した OID を `m_buffer_type_maps` に蓄積し、後続の `generateBufferPoolWatermarkCounterIdList()` がイテレートして FLEX_COUNTER_DB に push する | `bufferorch.cpp:391-560`, `bufferorch.cpp:316-344` |

### 4. COUNTERS_DB 書き込み依存

| 書き込み先テーブル | 書き込みタイミング | 証跡 |
|------------------|----------------|------|
| `COUNTERS_DB:COUNTERS_BUFFER_POOL_NAME_MAP` | `processBufferPool()` で SAI create 成功直後（`m_counterNameMapUpdater->setCounterNameMap()`）。`FLEX_COUNTER_STATUS` と無関係に常時書き込み | `bufferorch.cpp:542-547` |
| `FLEX_COUNTER_DB:BUFFER_POOL_WATERMARK_STAT_COUNTER:<OID>:COUNTER_ID_LIST` | `generateBufferPoolWatermarkCounterIdList()` が `FLEX_COUNTER_STATUS=enable` 受信後に各プール OID に対して push | `bufferorch.cpp:340-356` |
| `FLEX_COUNTER_DB:BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP:stats_mode` | `generateBufferPoolWatermarkCounterIdList()` がプラットフォームの `clear_buffer_pool_stats` サポート確認後にグループ全体の stats_mode を設定（READ_AND_CLEAR または READ） | `bufferorch.cpp:333-337` |
| `COUNTERS_DB:COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` | `FLEX_COUNTER_STATUS` 受信後に `FlexCounterOrch` が `gPortsOrch->generateQueueMap()` 等を呼び出し書き込み | `portsorch.cpp:8391-8443`, `flexcounterorch.cpp:249-255` |

### 5. PORT (allPortsReady) — 起動ブロック

| 参照先テーブル / リソース | 参照方向 | 条件 | 証跡 |
|--------------------------|---------|------|------|
| `APP_DB:PORT_TABLE\|PortInitDone` | 読み取り（存在確認）→ 起動ブロック | `allPortsReady()` が `false` の間 `FlexCounterOrch::doTask()` は先頭で `return`。全バッファカウンタグループ（QUEUE, PG, BUFFER_POOL_WATERMARK）の `enable` 処理が保留される | `flexcounterorch.cpp:164-169` |

---

## 解決タイミングサマリ

| 参照先 | 解決タイミング |
|--------|--------------|
| `FLEX_COUNTER_TABLE` キー各グループ | `FlexCounterOrch::doTask()` が即時評価。allPortsReady + m_delayTimerExpired が前提 |
| `DEVICE_METADATA.create_only_config_db_buffers` | コンストラクタで 1 回 + `handleDeviceMetadataTable()` で動的更新。既登録カウンタへの遡及なし |
| `APP_BUFFER_POOL_TABLE` OID | `BufferOrch::processBufferPool()` で SAI create 後に即時確定 |
| `PORT` (`allPortsReady`) | `portsyncd` が PortInitDone を書き込み後に自動アンブロック |
| `BUFFER_QUEUE` / `BUFFER_PG` 非ゼロプロファイル | `getQueueConfigurations()` / `getPgConfigurations()` 呼び出しのたびに動的再取得（`create_only_config_db_buffers=true` 時のみ） |
