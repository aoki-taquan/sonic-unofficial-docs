# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase G 通信メカニズムスキャンノート

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
スキャン範囲: `orchagent/orchdaemon.cpp:432-437,620-626`, `orchagent/flexcounterorch.cpp:40-155`, `orchagent/watermarkorch.cpp:23-50,52-143,144-232`, `orchagent/watermarkorch.h`

---

## CONFIG_DB → FlexCounterOrch の購読方式

### ConsumerStateTable (FLEX_COUNTER_TABLE)

orchdaemon が `FlexCounterOrch(m_configDb, flex_counter_tables)` を生成する際、`flex_counter_tables` に `CFG_FLEX_COUNTER_TABLE_NAME` (`"FLEX_COUNTER_TABLE"`) が含まれる (`orchdaemon.cpp:620-625`)。

`FlexCounterOrch` は `Orch` を継承しており、orchagent の主ループ (`orchdaemon.cpp:959`) が `SELECT_TIMEOUT = 1000 ms` の `select()` で `ConsumerStateTable` からイベントを受信する。`FLEX_COUNTER_TABLE|PG_WATERMARK` への HSET/DEL が `ProducerStateTable` 経由で書き込まれると `FLEX_COUNTER_TABLE_CHANNEL@<db>` へ PUBLISH され、`ConsumerStateTable` が起床して `doTask()` が呼び出される。

| 購読者 | 購読 API | DB | テーブル | ハンドラ |
|--------|---------|-----|---------|---------|
| `FlexCounterOrch` | `ConsumerStateTable` (Orch 汎用) | CONFIG_DB (4) | `FLEX_COUNTER_TABLE` | `FlexCounterOrch::doTask(Consumer&)` → PG_WATERMARK ハンドラ |

### WatermarkOrch も FLEX_COUNTER_TABLE を購読

`WatermarkOrch` は `wm_tables = { CFG_WATERMARK_TABLE_NAME, CFG_FLEX_COUNTER_TABLE_NAME }` を受け取り (`orchdaemon.cpp:432-437`)、同じ `FLEX_COUNTER_TABLE` の変化を `doTask()` で受信する。

| 購読者 | 購読 API | DB | テーブル | ハンドラ |
|--------|---------|-----|---------|---------|
| `WatermarkOrch` | `ConsumerStateTable` (Orch 汎用) | CONFIG_DB (4) | `FLEX_COUNTER_TABLE` | `WatermarkOrch::doTask(Consumer&)` → `handleFcConfigUpdate()` |
| `WatermarkOrch` | `ConsumerStateTable` (Orch 汎用) | CONFIG_DB (4) | `WATERMARK_TABLE` | `WatermarkOrch::doTask(Consumer&)` → telemetry interval 更新 |

### APPL_DB 通知チャネル (WATERMARK_CLEAR_REQUEST)

`WatermarkOrch` コンストラクタ (`watermarkorch.cpp:35-38`) で `NotificationConsumer` を `APPL_DB:WATERMARK_CLEAR_REQUEST` チャネルに登録する。`watermarkcfg clear pg-*` CLI が `PUBLISH WATERMARK_CLEAR_REQUEST "PG_HEADROOM"` / `"PG_SHARED"` を発行すると `WatermarkOrch::doTask(NotificationConsumer&)` が呼ばれる。

| 購読者 | 購読 API | DB | チャネル | ハンドラ |
|--------|---------|-----|---------|---------|
| `WatermarkOrch` | `NotificationConsumer` | APPL_DB | `WATERMARK_CLEAR_REQUEST` | `WatermarkOrch::doTask(NotificationConsumer&)` → `clearSingleWm()` |

---

## イベントフロー

```
config set FLEX_COUNTER_TABLE|PG_WATERMARK FLEX_COUNTER_STATUS enable
  ↓ ConfigDB HSET "FLEX_COUNTER_TABLE|PG_WATERMARK" "FLEX_COUNTER_STATUS" "enable"
  ↓ ProducerStateTable: PUBLISH "FLEX_COUNTER_TABLE_CHANNEL@4" "G" + "_KEY_SET" push

orchagent select() loop (SELECT_TIMEOUT = 1000 ms)
  ↓ ConsumerStateTable 起床
  → FlexCounterOrch::doTask(): generatePriorityGroupMap() → m_pg_watermark_enabled=true
                                → addPriorityGroupWatermarkFlexCounters()
                                → pg_watermark_manager.setCounterIdList() per PG OID
  → WatermarkOrch::doTask(): handleFcConfigUpdate("PG_WATERMARK") → m_wmStatus 更新
                             → m_telemetryTimer->start() (初回 enable 時)
```

---

## SELECT_TIMEOUT とポーリング遅延

| 項目 | 値 | 備考 |
|------|----|------|
| orchagent SELECT_TIMEOUT | 1000 ms | `orchdaemon.cpp:23` |
| warm-reboot FlexCounter 遅延 | 60 秒 | `FLEX_COUNTER_DELAY_SEC` (`flexcounterorch.cpp:44`) |
| POLL_INTERVAL デフォルト | 60000 ms | syncd FlexCounter ポーリング周期 |
| telemetry タイマー デフォルト | 120 秒 | `DEFAULT_TELEMETRY_INTERVAL` (`watermarkorch.cpp:9`) |

CONFIG_DB に `FLEX_COUNTER_STATUS = enable` を書き込んでから PG watermark カウンタが COUNTERS_DB に出現するまでには、最大 `SELECT_TIMEOUT (1s) + POLL_INTERVAL (60s)` の遅延が生じる。

---

## 購読プロセスサマリ

| プロセス | DB | テーブル / チャネル | 購読方式 | 役割 |
|---------|-----|-------------------|---------|------|
| `orchagent` (FlexCounterOrch) | CONFIG_DB | `FLEX_COUNTER_TABLE` | ConsumerStateTable | PG_WATERMARK enable/disable を処理し FLEX_COUNTER_DB に per-OID エントリを書き込む |
| `orchagent` (WatermarkOrch) | CONFIG_DB | `FLEX_COUNTER_TABLE`, `WATERMARK_TABLE` | ConsumerStateTable | telemetry タイマーの起動/停止を制御する |
| `orchagent` (WatermarkOrch) | APPL_DB | `WATERMARK_CLEAR_REQUEST` | NotificationConsumer | pg-headroom / pg-shared watermark クリアを処理する |
| `syncd` (FlexCounter) | FLEX_COUNTER_DB | `PG_WATERMARK_STAT_COUNTER:<oid>` | ConsumerTable / Traditional モード | per-OID エントリを読んで SAI ポーリングスレッドを管理する |
