# FLEX_COUNTER_TABLE — ordering 調査メモ (Phase B)

## 調査対象

- `sonic-net/sonic-swss`: `orchagent/flexcounterorch.cpp`
- `sonic-net/sonic-swss`: `orchagent/orchdaemon.cpp`
- `sonic-net/sonic-swss`: `orchagent/flexcounterorch.h`

## FlexCounterOrch 初期化順序 (orchdaemon.cpp)

`orchdaemon.cpp` 内の生成順（NPU 標準パス):

| 順番 | オブジェクト | ファイル位置 |
|------|------------|------------|
| 1 | `gPortsOrch = new PortsOrch(...)` | L232 |
| 2 | `gFlowCounterRouteOrch = new FlowCounterRouteOrch(...)` | L255 |
| 3 | `gIntfsOrch = new IntfsOrch(...)` | L296 |
| 4 | `gCoppOrch = new CoppOrch(...)` | L341 |
| 5 | `gBufferOrch = new BufferOrch(...)` | L394 |
| 6 | `gSrv6Orch = new Srv6Orch(...)` | (後続) |
| 7 | `gSwitchOrch = new SwitchOrch(...)` | (前段) |
| 8 | `flexCounterOrch = new FlexCounterOrch(...)` | L625 |

`FlexCounterOrch` は他すべての依存 Orch が生成済みの状態で生成される。`gDirectory.set(gPortsOrch)` は L629 で `FlexCounterOrch` 生成直後に呼ばれる。

## doTask ガード順序

`FlexCounterOrch::doTask(Consumer &consumer)` の早期 return ガード（順番どおり):

1. `CFG_DEVICE_METADATA_TABLE_NAME` テーブルなら `handleDeviceMetadataTable()` に委譲（即 return）
2. `!m_delayTimerExpired` なら全処理を保留（warm-reboot 遅延 60 秒）
3. `gPortsOrch && !gPortsOrch->allPortsReady()` なら全処理を保留（ポート初期化待ち）
4. `gFabricPortsOrch && !gFabricPortsOrch->allPortsReady()` なら全処理を保留
5. `!flexCounterGroupMap.count(key)` なら無効エントリを破棄（`task_invalid_entry`, リトライなし）

## グループ別 enable 前提条件

`FLEX_COUNTER_STATUS=enable` を処理するには以下の先行条件が必要:

| グループ | 先行必須条件 |
|---------|------------|
| `PORT`, `PORT_BUFFER_DROP`, `QUEUE`, `QUEUE_WATERMARK`, `PG_DROP`, `PG_WATERMARK`, `WRED_ECN_PORT`, `WRED_ECN_QUEUE`, `PORT_PHY_ATTR` | `gPortsOrch` 非 NULL かつ `allPortsReady()` |
| `QUEUE`, `QUEUE_WATERMARK`, `PG_DROP`, `PG_WATERMARK` (create_only_config_db_buffers=true 時のみ) | `gBufferOrch` に BUFFER_QUEUE/BUFFER_PG エントリが存在 |
| `RIF` | `gIntfsOrch` 非 NULL |
| `BUFFER_POOL_WATERMARK` | `gBufferOrch` 非 NULL |
| `TUNNEL` | `VxlanTunnelOrch` が `gDirectory` に登録済み |
| `ENI`, `DASH_METER` | `DashOrch` が `gDirectory` に登録済み |
| `HA_SET` | `DashHaOrch` が `gDirectory` に登録済み |
| `FLOW_CNT_TRAP` | `gCoppOrch` 非 NULL |
| `FLOW_CNT_ROUTE` | `gFlowCounterRouteOrch` 非 NULL かつ `getRouteFlowCounterSupported()` = true |
| `SRV6` | `gSrv6Orch` 非 NULL |
| `SWITCH` | `gSwitchOrch` 非 NULL |

## フィールドループ内の処理順

同一 SET コマンドに複数フィールドがある場合、ループ内の処理順:

1. `POLL_INTERVAL_FIELD` → `setFlexCounterGroupPollInterval()` (即時適用)
2. `BULK_CHUNK_SIZE_FIELD` / `BULK_CHUNK_SIZE_PER_PREFIX_FIELD` → 変数に保管（ループ後まとめて適用）
3. `FLEX_COUNTER_STATUS_FIELD` → enable/disable アクション + `setFlexCounterGroupOperation()`
4. その他 → `SWSS_LOG_NOTICE("Unsupported field")` でスキップ

`POLL_INTERVAL` と `FLEX_COUNTER_STATUS` を同一 SET に含める場合、必ず `POLL_INTERVAL` が先に適用される。

## disable 時の DEL 非対称性

`disable` 時に FLEX_COUNTER_DB の per-OID エントリを**明示削除しないグループ**:
- `PORT`, `QUEUE`, `RIF`, `BUFFER_POOL_WATERMARK`, `TUNNEL`, `WRED_ECN_PORT`, `WRED_ECN_QUEUE`, `SRV6`, `SWITCH`

`disable` 時に FLEX_COUNTER_DB / COUNTERS_DB のエントリを**明示削除するグループ**:
- `FLOW_CNT_TRAP`: `gCoppOrch->clearHostIfTrapCounterIdList()`
- `FLOW_CNT_ROUTE`: `gFlowCounterRouteOrch->clearRouteFlowStats()`
- `PORT_PHY_ATTR`: `clearPortPhyAttrCounterMap()` + `clearPortPhySerdesAttrCounterMap()`

syncd は `setFlexCounterGroupOperation("disable")` を受信してからポーリングを停止する。per-OID エントリが FLEX_COUNTER_DB に残っていても、group status が disable であれば syncd は収集しない。

## warm-reboot 時の bake() の無操作設計

`FlexCounterOrch::bake()` は意図的に `return true` のみ:

> "The FCs are not data plane configuration required during reconciling process, hence don't do anything in bake."

Reconciling 中 (m_delayTimerExpired=false) はすべての SET を保留し、60 秒後に一括適用する。データプレーンへの影響なし。

## 一度きり生成フラグ

`m_port_counter_enabled`, `m_queue_enabled` 等の `m_xxx_enabled` フラグにより、`generateXxxMap()` 等の counter map 生成は通常初回のみ実行される。`PORT_PHY_ATTR` は明示的な `if (!m_port_phy_attr_enabled)` / `if (!m_port_phy_serdes_attr_enabled)` ガードあり。

## スキャン証跡

- `flexcounterorch.cpp:145-417` (`doTask` 全行精読)
- `orchdaemon.cpp:232-629` (FlexCounterOrch 生成前後の依存 Orch 初期化シーケンス)
- `flexcounterorch.h:60-90` (m_xxx_enabled フラグ定義)
