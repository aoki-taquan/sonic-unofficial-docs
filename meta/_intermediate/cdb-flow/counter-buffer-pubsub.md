# counter-buffer Phase G — 通信メカニズム (pubsub)

Generated: 2026-05-17  
Target doc: docs/reference/config-db/counter-buffer.md

## スキャン対象

- `sonic-swss/orchagent/watermarkorch.cpp`
- `sonic-swss/orchagent/watermarkorch.h`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-utilities/scripts/watermarkstat`

---

## 1. CONFIG_DB → orchagent — SubscriberStateTable (swsscommon)

### watermarkorch の購読テーブル

`WatermarkOrch` は `orchdaemon.cpp:437` で以下の 2 テーブルを購読する:

| テーブル | 定数 | 役割 |
|---------|------|------|
| `WATERMARK_TABLE` (`CFG_WATERMARK_TABLE_NAME`) | CONFIG_DB | TELEMETRY_INTERVAL 変更通知受信 |
| `FLEX_COUNTER_TABLE` (`CFG_FLEX_COUNTER_TABLE_NAME`) | CONFIG_DB | FLEX_COUNTER_STATUS 変更通知受信 |

購読 API は `swsscommon::Orch(db, tables)` コンストラクタが内部で生成する `ConsumerStateTable`。
各テーブルへの SET コマンドは `WatermarkOrch::doTask(Consumer &consumer)` で受信し、
- テーブルが `CFG_WATERMARK_TABLE_NAME` → `handleWmConfigUpdate(key, fvt)` へ dispatch
- テーブルが `CFG_FLEX_COUNTER_TABLE_NAME` → `handleFcConfigUpdate(key, fvt)` へ dispatch

### flexcounterorch の購読テーブル

`FlexCounterOrch` は `orchdaemon.cpp:625` で以下を購読する:

| テーブル | 定数 | 役割 |
|---------|------|------|
| `FLEX_COUNTER_TABLE` | CONFIG_DB | FLEX_COUNTER_STATUS / POLL_INTERVAL 変更 |
| `DEVICE_METADATA` | CONFIG_DB | スイッチタイプ等のメタ情報 |

`FLEX_COUNTER_STATUS:enable` / `disable` を受信すると、対象グループ (`QUEUE_WATERMARK` / `PG_WATERMARK` / `QUEUE_STAT` / `PG_DROP` / `PORT_BUFFER_DROP` / `BUFFER_POOL_WATERMARK` 等) に応じて `gPortsOrch` / `gBufferOrch` のカウンタ登録メソッドを呼び出す (flexcounterorch.cpp:225-295)。

---

## 2. APPL_DB → watermarkorch — Redis PUBLISH/SUBSCRIBE (NotificationConsumer)

### WATERMARK_CLEAR_REQUEST チャネル

`WatermarkOrch` は初期化時に `swss::NotificationConsumer` を `APPL_DB` の
`WATERMARK_CLEAR_REQUEST` チャネルに対して作成する (watermarkorch.cpp:35-39)。

送信者は `watermarkstat` CLI (`sonic-utilities/scripts/watermarkstat:323-325`):
```python
def send_clear_notification(self, data):
    msg = json.dumps(data, separators=(',', ':'))
    self.db.publish('APPL_DB', 'WATERMARK_CLEAR_REQUEST', msg)
```

メッセージフォーマット: `["<op>", "<type>"]`
- `op`: `"PERSISTENT"` または `"USER"`
- `type`: `"PG_HEADROOM"` / `"PG_SHARED"` / `"Q_SHARED_UNI"` / `"Q_SHARED_MULTI"` / `"Q_SHARED_ALL"` / `"BUFFER_POOL"` / `"HEADROOM_POOL"`

`WatermarkOrch::doTask(NotificationConsumer &consumer)` が受信し、対象テーブル
(`PERSISTENT_WATERMARKS` または `USER_WATERMARKS`) の指定フィールドを `"0"` にリセットする
(`clearSingleWm()` 経由)。

**これは Redis の PUBLISH/SUBSCRIBE (pub-sub) であり、CONFIG_DB の keyspace 通知とは別機構**。
watermarkstat CLI が APPL_DB に直接 `PUBLISH` し、orchagent 内の `NotificationConsumer` が
APPL_DB の `NOTIFY__WATERMARK_CLEAR_REQUEST` チャネルを SUBSCRIBE する。

---

## 3. SelectableTimer — PERIODIC_WATERMARKS 定期リセット

`WatermarkOrch` は初期化時に `SelectableTimer` を `DEFAULT_TELEMETRY_INTERVAL (120秒)` で作成し、
`Orch::addExecutor(executorT)` で登録する (watermarkorch.cpp:41-44)。

タイマーが発火すると `WatermarkOrch::doTask(SelectableTimer &timer)` が呼ばれ、
`PERIODIC_WATERMARKS` テーブルの全フィールド (`SAI_INGRESS_PRIORITY_GROUP_STAT_*` / `SAI_QUEUE_STAT_*` / `SAI_BUFFER_POOL_STAT_*`) を `"0"` にリセットする (watermarkorch.cpp:259-280)。

タイマーの開始/停止は FLEX_COUNTER_STATUS と連動:
- `QUEUE_WATERMARK` または `PG_WATERMARK` グループが `enable` になると `m_telemetryTimer->start()` (watermarkorch.cpp:138)
- 両グループが `disable` になると `m_wmStatus == 0` のため次回タイマー発火時に `m_telemetryTimer->stop()` (watermarkorch.cpp:256)

---

## 4. flexcounterorch から portsorch/bufferorch へのコールバック

`FlexCounterOrch::doTask()` が `FLEX_COUNTER_STATUS:enable` を受信した際、グループごとに
orchagent 内でのメソッド呼び出しが発生する (flexcounterorch.cpp:235-295):

| グループキー | 呼び出し先 | 動作 |
|------------|----------|------|
| `QUEUE_STAT` | `gPortsOrch->generateQueueCounterMap()` | Queue OID → カウンタ ID list 登録 |
| `QUEUE_WATERMARK` | `gPortsOrch->generateQueueWatermarkCounterMap()` | Queue WM カウンタ ID list 登録 |
| `PG_STAT` | `gPortsOrch->generatePriorityGroupCounterMap()` | PG OID → カウンタ ID list 登録 |
| `PG_WATERMARK` | `gPortsOrch->generatePriorityGroupWatermarkCounterMap()` | PG WM カウンタ ID list 登録 |
| `PORT_BUFFER_DROP` | `gPortsOrch->generatePortBufferDropCounterMap()` | Port buffer drop カウンタ ID list 登録 |
| `BUFFER_POOL_WATERMARK` | `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` | Buffer Pool WM カウンタ ID list 登録 |

これらのメソッドは FLEX_COUNTER_TABLE (syncd 側) に `COUNTER_ID_LIST` を書き込み、
syncd の FlexCounter ポーリングを開始させる。

---

## 5. 購読者が存在しないケース

以下のテーブル / チャネルには **watermarkorch / bufferorch 以外に購読者がいない**:

| テーブル/チャネル | 購読者 |
|---------------|-------|
| `WATERMARK_CLEAR_REQUEST` | `watermarkorch` のみ |
| `CFG_WATERMARK_TABLE_NAME` | `watermarkorch` のみ |
| `COUNTERS_DB / COUNTERS:<oid>` への書き込み (syncd) | 読み取り専用 (show / watermarkstat) |

外部サービス (gnmi-server / sonic-telemetry / CLI show) は COUNTERS_DB を **読み取り専用**で参照するだけで、
watermarkorch / bufferorch にイベントを送ることはない。

---

## 検出されたポイント

1. **WATERMARK_CLEAR_REQUEST は APPL_DB の Redis PUBLISH/SUBSCRIBE**: CONFIG_DB の keyspace 通知とは異なる機構。watermarkstat CLI が APPL_DB に直接 PUBLISH し、orchagent の NotificationConsumer が受信する。HLD に明示されていない。

2. **タイマーは FLEX_COUNTER_STATUS と連動**: `QUEUE_WATERMARK` / `PG_WATERMARK` の両グループが disable になるとタイマーも自動停止し、PERIODIC_WATERMARKS のリセットが停止する。

3. **flexcounterorch は仲介役**: CONFIG_DB の `FLEX_COUNTER_TABLE` 変更を受信して `gPortsOrch` / `gBufferOrch` のメソッドを呼び出す。portsorch / bufferorch は CONFIG_DB を直接購読せず、flexcounterorch 経由でカウンタ登録が行われる。

4. **Buffer Pool WM のみ enable 時に bufferorch::generateBufferPoolWatermarkCounterIdList() が呼ばれる**: Queue/PG は gPortsOrch 経由だが、Buffer Pool のみ gBufferOrch 経由という非対称設計。
