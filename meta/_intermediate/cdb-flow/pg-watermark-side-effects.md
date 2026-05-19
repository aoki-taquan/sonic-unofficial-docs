# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase F 副次 DB 書込スキャンノート

対象ページ: `docs/reference/config-db/pg-watermark.md`
対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
Producer: `FlexCounterOrch` (`flexcounterorch.cpp`) + `PortsOrch` (`portsorch.cpp`) + `WatermarkOrch` (`watermarkorch.cpp`)
スキャン範囲: flexcounterorch.cpp:265-269、portsorch.cpp:736,872-876,8822-9051、watermarkorch.cpp:23-350 の全行精読

---

## 検出した副次 DB 書込

### 1. FLEX_COUNTER_DB — FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER（orsagent init 時）

- 書込元: `PortsOrch::init()` → `setFlexCounterGroupParameter()` (`portsorch.cpp:872-876`)
- タイミング: orchagent 起動時 **1 回限り**（CONFIG_DB の PG_WATERMARK エントリ変化とは独立）
- 書込内容: `POLL_INTERVAL=60000`、`STATS_MODE=READ_AND_CLEAR`、`FLEX_COUNTER_STATUS=disable`
- 条件: 常時（orchagent 起動で必ず書かれる）

### 2. FLEX_COUNTER_DB — PG_WATERMARK_STAT_COUNTER:<sai_oid>（per-OID エントリ）

- 書込元: `pg_watermark_manager.setCounterIdList()` (`portsorch.cpp:9051`)
- タイミング: `FLEX_COUNTER_STATUS=enable` を受信した際の `addPriorityGroupWatermarkFlexCounters()` 内、または `BUFFER_PG` SET イベント時（enable フラグが true の場合）
- 書込内容: `PG_WATERMARK_STAT_ID_LIST` = SAI カウンタ ID リスト（XOFF_ROOM + SHARED の 2 統計）
- 削除: `FLEX_COUNTER_STATUS=disable` で `clearCounterIdList()` → エントリ削除 (`portsorch.cpp:9095`)

### 3. COUNTERS_DB — COUNTERS_PG_NAME_MAP（BUFFER_PG 設定時）

- 書込元: `PortsOrch::addPortBufferPgCounters()` → `m_pgCounterNameMapUpdater->setCounterNameMap()` (`portsorch.cpp:8937`)
- タイミング: `BUFFER_PG` テーブルへの書き込みイベント（PG_WATERMARK enable 状態に依存しない）
- 書込内容: `<port_alias>:<pg_index>` → `<sai_pg_oid>` マッピング
- 条件: `BUFFER_PG` SET イベント時に常時書かれる

### 4. COUNTERS_DB — COUNTERS_PG_PORT_MAP（BUFFER_PG 設定時）

- 書込元: `PortsOrch::addPortBufferPgCounters()` → `m_pgPortTable->set()` (`portsorch.cpp:8938`)
- タイミング: `BUFFER_PG` テーブルへの書き込みイベント
- 書込内容: `<sai_pg_oid>` → `<sai_port_oid>` マッピング
- 条件: PG_WATERMARK enable 状態に依存しない

### 5. COUNTERS_DB — COUNTERS_PG_INDEX_MAP（BUFFER_PG 設定時）

- 書込元: `PortsOrch::addPortBufferPgCounters()` → `m_pgIndexTable->set()` (`portsorch.cpp:8939`)
- タイミング: `BUFFER_PG` テーブルへの書き込みイベント
- 書込内容: `<sai_pg_oid>` → `<pg_index>` マッピング
- 条件: PG_WATERMARK enable 状態に依存しない

### 6. COUNTERS_DB — PERIODIC_WATERMARKS（telemetry タイマー発火時）

- 書込元: `WatermarkOrch::doTask(SelectableTimer&)` → `clearSingleWm(m_periodicWatermarkTable, ...)` (`watermarkorch.cpp:258-266`)
- タイミング: telemetry タイマー発火ごと（デフォルト 120 秒周期）
- 書込内容: 対象 PG OID の `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` / `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` を `"0"` に設定（クリア）
- 条件: `m_wmStatus != 0`（PG_WATERMARK または QUEUE_WATERMARK が enable）の場合のみタイマーが動作する。`m_wmStatus == 0` になると `m_telemetryTimer->stop()` が呼ばれる

### 7. COUNTERS_DB — PERIODIC_WATERMARKS / PERSISTENT_WATERMARKS / USER_WATERMARKS（syncd Lua スクリプト）

- 書込元: syncd FlexCounter ポーリング → `watermark_pg.lua`
- タイミング: FlexCounter ポーリング周期ごと（デフォルト 60 秒）
- 書込内容: SAI から取得したウォーターマーク値（バイト単位）を 3 テーブルに書き込む。`PERIODIC_WATERMARKS` は telemetry タイマーでクリアされる。`PERSISTENT_WATERMARKS` / `USER_WATERMARKS` は明示クリア（`watermarkcfg clear`）まで保持
- 条件: `FLEX_COUNTER_STATUS=enable` かつ PG OID が FlexCounter に登録済みの場合のみ

---

## 副次書き込みが発生しないケース

| ケース | 理由 |
|--------|------|
| BUFFER_PG テーブルが空 | COUNTERS_PG_NAME_MAP / PORT_MAP / INDEX_MAP への書き込みが発生しない |
| FLEX_COUNTER_STATUS=disable（または未設定） | FLEX_COUNTER_DB per-OID エントリが登録されず syncd ポーリングが発生しない |
| m_wmStatus が 0 | telemetry タイマーが停止し PERIODIC_WATERMARKS のクリアが行われない |
| orchagent 未起動 | FLEX_COUNTER_GROUP_TABLE 設定が書かれないため syncd がグループを認識しない |

---

## スキャン証跡

- `flexcounterorch.cpp:265-269` 読了: enable ハンドラで `generatePriorityGroupMap()` → `addPriorityGroupWatermarkFlexCounters()` の呼び出し確認
- `portsorch.cpp:872-876` 読了: init 時の `setFlexCounterGroupParameter()` でグループ設定書き込み確認
- `portsorch.cpp:8904-8939` 読了: `addPortBufferPgCounters()` で 3 種の COUNTERS_DB マップ書き込み確認
- `portsorch.cpp:9048-9052` 読了: `setCounterIdList()` で FLEX_COUNTER_DB per-OID エントリ書き込み確認
- `portsorch.cpp:9090-9095` 読了: `clearCounterIdList()` で disable 時のエントリ削除確認
- `watermarkorch.cpp:233-281` 読了: telemetry タイマーで PERIODIC_WATERMARKS クリア確認
- `watermarkorch.cpp:116-140` 読了: `handleFcConfigUpdate()` で `m_wmStatus` 更新とタイマー起動確認
