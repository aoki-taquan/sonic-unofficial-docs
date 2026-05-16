# counters-flex ordering 調査メモ

## 調査対象

- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.h`

## FLEX_COUNTER_TABLE 処理順序

`FlexCounterOrch::doTask(Consumer &consumer)` の処理ガード条件（順番どおり）:

1. `CFG_DEVICE_METADATA_TABLE_NAME` テーブルなら `handleDeviceMetadataTable()` に委譲（即リターン）
2. `!m_delayTimerExpired` なら即リターン（Warm-reboot 遅延期間中は全処理を保留）
3. `gPortsOrch && !gPortsOrch->allPortsReady()` なら即リターン（ポート初期化待ち）
4. `gFabricPortsOrch && !gFabricPortsOrch->allPortsReady()` なら即リターン（FabricPort 初期化待ち）
5. `flexCounterGroupMap` に存在しないキーは `task_invalid_entry` として即破棄（リトライなし）

## enable/disable 時の先行必須条件

### SET + `FLEX_COUNTER_STATUS = enable` 時のグループ別アクション

| グループキー | 呼び出し先 | 先行必須 |
|---|---|---|
| `PORT` | `gPortsOrch->generatePortCounterMap()` | `gPortsOrch` 非 NULL、allPortsReady |
| `PORT_BUFFER_DROP` | `gPortsOrch->generatePortBufferDropCounterMap()` | `gPortsOrch` 非 NULL、allPortsReady |
| `QUEUE` | `gPortsOrch->generateQueueMap()` + `addQueueFlexCounters()` | `gPortsOrch` 非 NULL、allPortsReady; `create_only_config_db_buffers=true` 時は BUFFER_QUEUE も必須 |
| `QUEUE_WATERMARK` | `gPortsOrch->generateQueueMap()` + `addQueueWatermarkFlexCounters()` | 同上 |
| `PG_DROP` | `gPortsOrch->generatePriorityGroupMap()` + `addPriorityGroupFlexCounters()` | `gPortsOrch` 非 NULL、allPortsReady; `create_only_config_db_buffers=true` 時は BUFFER_PG も必須 |
| `PG_WATERMARK` | `gPortsOrch->generatePriorityGroupMap()` + `addPriorityGroupWatermarkFlexCounters()` | 同上 |
| `WRED_ECN_PORT` | `gPortsOrch->generateWredPortCounterMap()` | `gPortsOrch` 非 NULL |
| `WRED_ECN_QUEUE` | `gPortsOrch->generateQueueMap()` + `addWredQueueFlexCounters()` | `gPortsOrch` 非 NULL |
| `RIF` | `gIntfsOrch->generateInterfaceMap()` | `gIntfsOrch` 非 NULL |
| `BUFFER_POOL_WATERMARK` | `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` | `gBufferOrch` 非 NULL |
| `TUNNEL` | `vxlan_tunnel_orch->generateTunnelCounterMap()` | VxlanTunnelOrch が gDirectory 登録済み |
| `ENI` | `dash_orch->handleFCStatusUpdate(true)` | DashOrch が gDirectory 登録済み |
| `DASH_METER` | `dash_orch->handleMeterFCStatusUpdate(true)` | DashOrch が gDirectory 登録済み |
| `HA_SET` | `dash_ha_orch->handleHaSetFCStatusUpdate(true)` | DashHaOrch が gDirectory 登録済み |
| `FLOW_CNT_TRAP` | `gCoppOrch->generateHostIfTrapCounterIdList()` | `gCoppOrch` 非 NULL |
| `FLOW_CNT_ROUTE` | `gFlowCounterRouteOrch->generateRouteFlowStats()` | `gFlowCounterRouteOrch` 非 NULL かつ `getRouteFlowCounterSupported()` |
| `SRV6` | `gSrv6Orch->setCountersState(true)` | `gSrv6Orch` 非 NULL |
| `PORT_PHY_ATTR` | `gPortsOrch->generatePortPhyAttrCounterMap()` + `generatePortPhySerdesAttrCounterMap()` | `gPortsOrch` 非 NULL、allPortsReady |
| `SWITCH` | `gSwitchOrch->generateSwitchCounterIdList()` | `gSwitchOrch` 非 NULL |

### disable 時のアクション

disable 時は多くのグループが `setFlexCounterGroupOperation()` のみ呼ばれる。
例外:
- `FLOW_CNT_TRAP`: `gCoppOrch->clearHostIfTrapCounterIdList()` で ID リストを明示削除
- `FLOW_CNT_ROUTE`: `gFlowCounterRouteOrch->clearRouteFlowStats()` で明示削除
- `PORT_PHY_ATTR`: `clearPortPhyAttrCounterMap()` + `clearPortPhySerdesAttrCounterMap()` で明示削除

その他グループ（PORT, QUEUE, RIF 等）は disable 時に FLEX_COUNTER_DB のエントリを削除しない。
syncd 側で polling を停止するだけで、per-OID エントリは残ったまま。

## Warm-reboot 挙動

`FlexCounterOrch::bake()` は意図的に no-op（`return true`）。コメントに明示:

> "The FCs are not data plane configuration required during reconciling process, hence don't do anything in bake."

Warm-reboot 時は `SelectableTimer` (60秒) を開始し、`m_delayTimerExpired = false` のまま
すべての `doTask()` 処理が保留される。60秒後に `doTask(SelectableTimer&)` が呼ばれて
`m_delayTimerExpired = true` になり、通常処理が再開される。

cold-start 時はコンストラクタで `m_delayTimerExpired = true` に即設定される。

## 一度きり生成フラグ

各グループには専用の `m_xxx_enabled` フラグ（`flexcounterorch.h:66-78`）がある。
`enable` アクション（generateXxxMap 呼び出し）は **初回のみ** 実行される（フラグ確認あり）。
一部グループ（PORT_PHY_ATTR 等）は明示的に `if (!m_xxx_enabled)` で二重実行を防ぐ。

## create_only_config_db_buffers の影響

`DEVICE_METADATA|localhost|create_only_config_db_buffers = true` の場合:
- QUEUE/PG 系の counter map 生成は `gBufferOrch->getBufferObjectsWithNonZeroProfile()` で
  non-zero profile 設定済みの port+queue/pg のみに絞り込まれる
- `false` の場合（デフォルト）はすべての利用可能 queue/pg を対象とする

## gearbox 対応

`gPortsOrch->isGearboxEnabled()` が true の場合、PORT と MACSEC 系グループは
`setFlexCounterGroupPollInterval()` と `setFlexCounterGroupOperation()` を
通常の flexcounter に加えて gearbox 用にも同じ値で呼び出す（2重設定）。

## フィールド処理順序

`SET` コマンド受信時のフィールドループ内での処理順:
1. `POLL_INTERVAL_FIELD` → `setFlexCounterGroupPollInterval()`
2. `BULK_CHUNK_SIZE_FIELD` / `BULK_CHUNK_SIZE_PER_PREFIX_FIELD` → 変数に保存（後で一括適用）
3. `FLEX_COUNTER_STATUS_FIELD` → enable/disable アクション + `setFlexCounterGroupOperation()`
4. 上記以外 → `SWSS_LOG_NOTICE("Unsupported field ...")` で無視

`POLL_INTERVAL` と `FLEX_COUNTER_STATUS` を同一 SET コマンドに含める場合、
フィールドループ順次処理のため `POLL_INTERVAL` が先に適用される。
