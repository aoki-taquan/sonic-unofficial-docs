# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase G 通信メカニズム調査ノート

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
調査対象:
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/watermarkorch.cpp`
- `sonic-utilities/scripts/watermarkstat`

---

## 通信チャネル一覧

### 1. CONFIG_DB → FlexCounterOrch (SubscriberStateTable)

- チャネル種別: `SubscriberStateTable`（Redis keyspace notification）
- Producer: `counterpoll watermark enable/disable` → CONFIG_DB `FLEX_COUNTER_TABLE|PG_WATERMARK`
- Consumer: `FlexCounterOrch::doTask(Consumer&)` (`flexcounterorch.cpp:145`)
- 条件: `FLEX_COUNTER_STATUS == "enable"` のとき `m_pg_watermark_enabled = true` をセット

### 2. CONFIG_DB → WatermarkOrch (SubscriberStateTable)

- チャネル種別: `SubscriberStateTable`（Redis keyspace notification）
- Producer: `counterpoll watermark enable/disable` → CONFIG_DB `FLEX_COUNTER_TABLE|PG_WATERMARK`
- Consumer: `WatermarkOrch::doTask(Consumer&)` → `handleFcConfigUpdate()` (`watermarkorch.cpp:116`)
- 条件: `FLEX_COUNTER_STATUS == "enable"` のとき `m_wmStatus` ビットをセットし telemetry タイマーを起動

### 3. APPL_DB パブサブ通知 — WATERMARK_CLEAR_REQUEST

- チャネル種別: Redis `PUBLISH` / `SUBSCRIBE`（swss::NotificationProducer / NotificationConsumer）
- Producer: `watermarkstat -c -t pg_headroom` / `pg_shared` → `WatermarkStatDaemon.send_clear_notification()` (`watermarkstat:325`)
  - メッセージ形式: `["USER","PG_HEADROOM"]` または `["PERSISTENT","PG_HEADROOM"]` など
- Consumer: `WatermarkOrch::doTask(NotificationConsumer&)` (`watermarkorch.cpp:144`)
  - チャネル名: `WATERMARK_CLEAR_REQUEST`（`APPL_DB`）
  - `op` = `"USER"` / `"PERSISTENT"`, `data` = `"PG_HEADROOM"` / `"PG_SHARED"`
  - `clearSingleWm()` で `COUNTERS_DB PERSISTENT_WATERMARKS` / `USER_WATERMARKS` の当該フィールドを `"0"` にクリア

### 4. portsorch → FlexCounterOrch (直接関数呼び出し)

- チャネル種別: 同プロセス内の直接関数呼び出し
- `flexCounterOrch->getPgWatermarkCountersState()` で enable フラグを読み出し
- `addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex()` → `pg_watermark_manager.setCounterIdList()` (`portsorch.cpp:9051`)

### 5. FlexCounterOrch/portsorch → syncd (FLEX_COUNTER_DB)

- チャネル種別: `FlexCounterTaggedCachedManager` 書き込み（FLEX_COUNTER_DB）
- 書き込みキー: `PG_WATERMARK_STAT_COUNTER:<sai_pg_oid>:PG_WATERMARK_STAT_ID_LIST`
- syncd は FLEX_COUNTER_DB の変化を keyspace notification で検知し、SAI ポーリングを開始・停止

### 6. syncd → COUNTERS_DB (SAI ポーリング)

- チャネル種別: syncd 直接書き込み（`READ_AND_CLEAR` モード）
- 書き込みキー: `PERIODIC_WATERMARKS|<sai_pg_oid>`, `PERSISTENT_WATERMARKS|<sai_pg_oid>`, `USER_WATERMARKS|<sai_pg_oid>`
- フィールド: `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES`

---

## フロー図

```text
counterpoll watermark enable
  ↓ CONFIG_DB[FLEX_COUNTER_TABLE|PG_WATERMARK] FLEX_COUNTER_STATUS=enable
  ↓ SubscriberStateTable (keyspace notification)
FlexCounterOrch::doTask() → m_pg_watermark_enabled=true
  → gPortsOrch->addPriorityGroupWatermarkFlexCounters()
  → pg_watermark_manager.setCounterIdList()
FLEX_COUNTER_DB[PG_WATERMARK_STAT_COUNTER:<oid>:PG_WATERMARK_STAT_ID_LIST]
  ↓ syncd FlexCounter (60000ms ポーリング, READ_AND_CLEAR)
      sai_get_ingress_priority_group_stats()
COUNTERS_DB[PERIODIC/PERSISTENT/USER_WATERMARKS|<oid>] ← SAI値

WatermarkOrch::doTask() → handleFcConfigUpdate() → m_telemetryTimer->start()
  ↓ タイマー発火 (120秒)
  → clearSingleWm() → COUNTERS_DB[PERIODIC_WATERMARKS|<oid>] を "0" に

watermarkstat -c -t pg_headroom
  ↓ APPL_DB PUBLISH WATERMARK_CLEAR_REQUEST ["USER","PG_HEADROOM"]
WatermarkOrch::doTask(NotificationConsumer) → clearSingleWm()
  → COUNTERS_DB[USER_WATERMARKS|<oid>] XOFF_ROOM フィールドを "0" に
```
