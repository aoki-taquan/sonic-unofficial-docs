# COUNTERS_DB QUEUE カウンタ — Phase G 通信メカニズム スキャンノート

Generated: 2026-05-19
Target doc: docs/reference/config-db/queue-counter.md

対象テーブル: `COUNTERS_DB` — `COUNTERS:<queue_oid>`、`COUNTERS_QUEUE_NAME_MAP`、`COUNTERS_QUEUE_TYPE_MAP`、`COUNTERS_QUEUE_INDEX_MAP`、`COUNTERS_QUEUE_PORT_MAP`
スキャン範囲: `sonic-swss/orchagent/portsorch.cpp`、`sonic-swss/orchagent/flexcounterorch.cpp`、`sonic-swss/orchagent/countercheckorch.cpp`、`sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`、`sonic-utilities/scripts/queuestat`、`sonic-swss/orchagent/watermarkorch.cpp`

---

## 1. 書き込み側 (Producer) の通信構造

### FlexCounterOrch → portsorch — CONFIG_DB の FLEX_COUNTER_TABLE を購読

`FlexCounterOrch` は `SubscriberStateTable` 経由で CONFIG_DB の `FLEX_COUNTER_TABLE` を購読する
(`orchdaemon.cpp:620-626`, `flexcounterorch.cpp:102-103`)。

`FLEX_COUNTER_TABLE|QUEUE = enable` を受信すると `FlexCounterOrch::doTask()` が呼ばれ、以下を順に実行する
(`flexcounterorch.cpp:247-252`):

1. `gPortsOrch->generateQueueMap(getQueueConfigurations())` — `COUNTERS_QUEUE_NAME_MAP` / `*_PORT_MAP` / `*_INDEX_MAP` / `*_TYPE_MAP` を COUNTERS_DB へ書き込む
2. `gPortsOrch->addQueueFlexCounters(getQueueConfigurations())` — `FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|QUEUE_STAT_COUNTER:<oid>` へ `COUNTER_ID_LIST` を書き込む

### COUNTERS_DB マッピングテーブルの書き込み方式

`generateQueueMapPerPort()` (`portsorch.cpp:8446-8531`) は swss `Table::set()` (plain HSET) で
COUNTERS_DB へ直接書き込む。`ProducerStateTable` を使わないため PUBLISH チャンネル通知は発行されない。

### FLEX_COUNTER_DB への書き込み方式

`addQueueFlexCountersPerPortPerQueueIndex()` は `queue_stat_manager.setCounterIdList()` を呼ぶ。
`FlexCounterManager` は内部で `ProducerTable` を使い `FLEX_COUNTER_DB:FLEX_COUNTER_TABLE` に書き込む。
Traditional モードでは `FLEX_COUNTER_TABLE_CHANNEL` チャンネルへ PUBLISH し syncd を起床させる
(evidence: `saihelper.cpp:1039-1050`, `counters-flex-pubsub.md` 調査参照)。

---

## 2. syncd FlexCounter ポーリングスレッド → COUNTERS_DB

syncd は `FlexCounter.cpp:3123` の `swss::Table(&pipeline, COUNTERS_TABLE)` でポーリング結果を
`COUNTERS_DB:COUNTERS:<queue_oid>` へ書き込む。`swss::Table::set()` は plain HSET であり
PUBLISH チャンネル通知は発行されない。

ポーリング周期は FlexCounter グループ定数で決まる:

| グループ | チャンネル/キー | 間隔 |
|---------|--------------|------|
| `QUEUE_STAT_COUNTER` | `COUNTERS:<oid>` (`SAI_QUEUE_STAT_PACKETS` 等) | 10000 ms |
| `QUEUE_WATERMARK_STAT_COUNTER` | `COUNTERS:<oid>` (`SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES`) | 60000 ms |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `COUNTERS:<oid>` (`SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` 等) | 10000 ms |

---

## 3. 消費側 (Consumer) の読み出し方式

### queuestat — on-demand polling

`sonic-utilities/scripts/queuestat` は起動時に COUNTERS_DB の以下を読み出す
(`queuestat:276, 299-341`):

1. `HGETALL COUNTERS_QUEUE_NAME_MAP` でポート:キューインデックス → OID マッピングを取得
2. `HGET COUNTERS_QUEUE_PORT_MAP <oid>` でポート OID を取得
3. `HGET COUNTERS_QUEUE_INDEX_MAP <oid>` でキューインデックスを取得
4. `HGET COUNTERS_QUEUE_TYPE_MAP <oid>` でキュータイプ (UC / MC / ALL) を取得
5. `HGETALL COUNTERS:<oid>` でカウンタ値を取得

いずれも keyspace 通知購読ではなく **on-demand HGET / HGETALL**。`--persistent`（`-p`）オプション使用時は
一定間隔でポーリングを繰り返す。

### watermarkorch — タイマー起動 polling

`WatermarkOrch` は CONFIG_DB の `WATERMARK_TABLE` を `SubscriberStateTable` で購読する。
タイマー満了時に COUNTERS_DB の `COUNTERS:<oid>` (`SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES`) を
HGET して `PERIODIC_WATERMARKS_TABLE` / `PERSISTENT_WATERMARKS_TABLE` / `USER_WATERMARKS_TABLE` へ転写する
(`watermarkorch.cpp:242-278`)。

### countercheckorch — PFC Watchdog 用 polling

`countercheckorch.cpp:200` は `m_countersDb->hget(COUNTERS_QUEUE_TYPE_MAP, queueIdStr)` で
キュータイプを確認し、マルチキャストキューの `SAI_QUEUE_STAT_PACKETS` を HGET する。
PFC Watchdog の嵐検出判定に使用 (`CounterCheckOrch::checkQueueMulticast()`)。

### HFTelOrch — 高頻度テレメトリ

`HFTelOrch::SUPPORT_COUNTER_TABLES` に `{COUNTERS_QUEUE_NAME_MAP, SAI_OBJECT_TYPE_QUEUE}` が登録されており
(`hftelorch.cpp:28`)、高頻度テレメトリ有効時は COUNTERS_DB の Queue カウンタを SAI TAM API 経由で
ストリーミングする。

### PFC detect/restore Lua スクリプト — EVAL ベース

`pfc_detect_*.lua` / `pfc_restore*.lua` は Redis EVAL で `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_PORT_MAP`
を参照してキュー OID とポートの対応を解決する (`pfc_detect_mellanox.lua:70-72`)。
直接のカウンタ読み取りには `HGET COUNTERS:<oid>` を使用。

---

## 4. 通信チャンネルサマリ

| 区間 | 通知方式 | チャンネル名 / パターン |
|------|---------|----------------------|
| CONFIG_DB `FLEX_COUNTER_TABLE\|QUEUE` → FlexCounterOrch | `SubscriberStateTable` keyspace PSUBSCRIBE | `__keyspace@{cfg_db}__:FLEX_COUNTER_TABLE\|QUEUE` |
| portsorch → COUNTERS_DB マッピングテーブル | `swss::Table::set()` (plain HSET) | **なし（PUBLISH 非発行）** |
| portsorch → FLEX_COUNTER_DB (traditional) | `ProducerTable` PUBLISH | `FLEX_COUNTER_TABLE_CHANNEL` |
| syncd FlexCounter → `COUNTERS:<oid>` | `swss::Table::set()` (plain HSET) | **なし（PUBLISH 非発行）** |
| COUNTERS_DB → queuestat / countercheckorch | on-demand HGET / HGETALL | なし |
| COUNTERS_DB → watermarkorch | タイマー起動 HGET | なし |
| COUNTERS_DB → gNMI telemetry | gNMI STREAM サブスクリプション (上位レイヤー) | — |
