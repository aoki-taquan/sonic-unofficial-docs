# COUNTERS_DB QUEUE / PG カウンタ — Phase G 通信メカニズムスキャンノート

対象: `FLEX_COUNTER_TABLE|QUEUE` / `FLEX_COUNTER_TABLE|QUEUE_WATERMARK` / `FLEX_COUNTER_TABLE|PG_DROP` / `FLEX_COUNTER_TABLE|PG_WATERMARK` / `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE`  
Consumer: `FlexCounterOrch` (`sonic-swss/orchagent/flexcounterorch.cpp`), `WatermarkOrch` (`sonic-swss/orchagent/watermarkorch.cpp`)  
スキャン範囲: `orchdaemon.cpp` (登録部), `flexcounterorch.cpp` (doTask, コンストラクタ), `watermarkorch.cpp` (doTask, コンストラクタ), `sonic-utilities/scripts/watermarkstat` (publish 側)

---

## 1. FlexCounterOrch の CONFIG_DB 購読

`orchdaemon.cpp:620-625` にて `FlexCounterOrch` を以下の 2 テーブルで生成する:

```cpp
vector<string> flex_counter_tables = {
    CFG_FLEX_COUNTER_TABLE_NAME,   // "FLEX_COUNTER_TABLE"
    CFG_DEVICE_METADATA_TABLE_NAME // "DEVICE_METADATA"
};
auto* flexCounterOrch = new FlexCounterOrch(m_configDb, flex_counter_tables);
```

`Orch(db, tableNames)` 基底クラスが `addConsumer()` を通じて各テーブルに `SubscriberStateTable` を生成する。CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@{config_db_id}__:FLEX_COUNTER_TABLE|*`) でエントリの変化を検出し、`pops()` で現在値を読み出す。

## 2. FlexCounterOrch::doTask() の処理フロー

`flexcounterorch.cpp:148-167` にて以下のガードを通過した場合のみ処理を実行:

1. `DEVICE_METADATA` テーブルは専用ハンドラへ委譲（即時処理、ガードなし）
2. `m_delayTimerExpired == false`（Warm-reboot 60 秒遅延）→ 即 return（保留）
3. `gPortsOrch->allPortsReady() == false` → 即 return（保留、m_toSync に残留）

キー `QUEUE` / `QUEUE_WATERMARK` / `PG_DROP` / `PG_WATERMARK` / `WRED_ECN_QUEUE` が `FLEX_COUNTER_STATUS = enable` で届くと `flexcounterorch.cpp:247-281` の分岐にて対応する `generateQueueMap()` / `addQueueFlexCounters()` 等を呼び出す。

未知キーは `SWSS_LOG_NOTICE` を出力して即削除（`flexcounterorch.cpp:183-188`）。

## 3. WatermarkOrch の二経路購読

`orchdaemon.cpp:432-437` にて `WatermarkOrch` を以下のテーブルで生成:

```cpp
vector<string> wm_tables = {
    CFG_WATERMARK_TABLE_NAME,     // "WATERMARK_TABLE" (TELEMETRY_INTERVAL 設定)
    CFG_FLEX_COUNTER_TABLE_NAME   // "FLEX_COUNTER_TABLE" (ウォーターマーク有効化状態の監視)
};
WatermarkOrch *wm_orch = new WatermarkOrch(m_configDb, wm_tables);
```

さらに `WatermarkOrch` コンストラクタ (`watermarkorch.cpp:35-38`) にて APPL_DB の `WATERMARK_CLEAR_REQUEST` チャンネルを `NotificationConsumer` で購読する:

```cpp
m_clearNotificationConsumer = new swss::NotificationConsumer(
    m_appDb.get(),
    "WATERMARK_CLEAR_REQUEST");
auto clearNotifier = new Notifier(m_clearNotificationConsumer, this, "WM_CLEAR_NOTIFIER");
```

## 4. watermarkstat → WATERMARK_CLEAR_REQUEST の publish

`sonic-utilities/scripts/watermarkstat:325`:

```python
self.db.publish('APPL_DB', 'WATERMARK_CLEAR_REQUEST', msg)
```

`msg` は `{op}:{data}` 形式。`op` は `"PERSISTENT"` または `"USER"`。`data` は以下のいずれか:

| data 文字列 | 対象 |
|------------|------|
| `PG_HEADROOM` | `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` |
| `PG_SHARED` | `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` |
| `Q_SHARED_UNI` | Unicast queue の `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` |
| `Q_SHARED_MULTI` | Multicast queue の `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` |
| `Q_SHARED_ALL` | ALL type queue の `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` |

`WatermarkOrch::doTask(NotificationConsumer&)` が受信し、対象テーブル（`PERSISTENT_WATERMARKS` / `USER_WATERMARKS`）の該当 OID を 0 クリアする。

## 5. PERIODIC_WATERMARKS の自動クリア（タイマー経路）

`WatermarkOrch` は `SelectableTimer`（デフォルト 120 秒、`DEFAULT_TELEMETRY_INTERVAL`）を持ち、`doTask(SelectableTimer&)` で `PERIODIC_WATERMARKS` テーブルの全 Queue / PG ウォーターマークを 0 クリアする（`watermarkorch.cpp:233-281`）。この経路は Redis pub/sub ではなくタイマー起動であり、外部からのイベントなしで自律的に動作する。

## 6. Lua スクリプトによる COUNTERS → WATERMARK テーブル転写

syncd の FlexCounter が `StatsMode::READ_AND_CLEAR` で `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` / PG ウォーターマーク統計をポーリングすると、`COUNTERS:<OID>` に値が書き込まれる。`watermark_queue.lua` / `watermark_pg.lua` が COUNTERS_DB 内で Lua アトミック処理として:

1. `COUNTERS:<OID>` の最新値を読み取り
2. `PERIODIC_WATERMARKS:<OID>` / `PERSISTENT_WATERMARKS:<OID>` / `USER_WATERMARKS:<OID>` の現在値と max 比較
3. max 値でウォーターマークテーブルを更新

この転写処理は Redis の Lua スクリプト実行（syncd 内）であり、orch や CLI からの pub/sub とは独立した経路。

## 7. 通信経路サマリ

| 経路 | Producer | Consumer | チャンネル / 方式 |
|------|----------|----------|----------------|
| FlexCounter 有効化 | `sonic-cfggen` / `counterpoll` CLI | `FlexCounterOrch` | `FLEX_COUNTER_TABLE|QUEUE` 等 SubscriberStateTable (CONFIG_DB keyspace) |
| FlexCounter → FLEX_COUNTER_DB | `FlexCounterOrch` (orchagent) | `syncd` FlexCounter | FLEX_COUNTER_DB（hset: COUNTER_ID_LIST, POLL_INTERVAL） |
| SAI ポーリング | `syncd` FlexCounter | SAI API | `sai_get_queue_stats` / `sai_get_ingress_priority_group_stats` |
| カウンタ書き込み | `syncd` | `COUNTERS_DB` | Redis HSET `COUNTERS:<OID>` |
| Watermark テーブル転写 | `syncd` (Lua) | `COUNTERS_DB` | `watermark_queue.lua` / `watermark_pg.lua` |
| Watermark クリア要求 | `watermarkstat -c` | `WatermarkOrch` | `APPL_DB WATERMARK_CLEAR_REQUEST` (Redis publish) |
| 周期クリア | `WatermarkOrch` SelectableTimer | `PERIODIC_WATERMARKS` | 内部タイマー (120 秒) |
| DEVICE_METADATA 変更 | 管理者 / `sonic-cfggen` | `FlexCounterOrch` | `DEVICE_METADATA` SubscriberStateTable (CONFIG_DB keyspace) |
