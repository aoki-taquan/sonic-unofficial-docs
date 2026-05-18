# state-flex-counter — Phase C 暗黙参照マップ調査メモ

調査日: 2026-05-18
対象ファイル: `docs/reference/config-db/state-flex-counter.md`

## 調査ソース

- `sonic-swss/orchagent/flexcounterorch.cpp` (master)
- `sonic-swss/orchagent/flexcounterorch.h` (master)
- `sonic-swss/orchagent/portsorch.cpp` (master)
- `sonic-sairedis/syncd/FlexCounter.cpp` (master)
- `sonic-sairedis/syncd/FlexCounterManager.cpp` (master)

---

## 検出された暗黙参照

### 1. CONFIG_DB:FLEX_COUNTER_TABLE → FlexCounterOrch (主ソース)

FlexCounterOrch が購読する CONFIG_DB テーブルは `FLEX_COUNTER_TABLE` のみ。
`doTask()` がフィールド `POLL_INTERVAL`、`FLEX_COUNTER_STATUS`、`BULK_CHUNK_SIZE`、`BULK_CHUNK_SIZE_PER_PREFIX` を処理し、
各値を FLEX_COUNTER_DB の `FLEX_COUNTER_GROUP_TABLE|<group>` へ書き込む。

証跡: `flexcounterorch.cpp:145-415`

### 2. CONFIG_DB:DEVICE_METADATA — create_only_config_db_buffers フラグ

FlexCounterOrch コンストラクタ内で `m_deviceMetadataConfigTable.hget("localhost", "create_only_config_db_buffers", ...)` を呼び出す（`flexcounterorch.cpp:115-120`）。
このフラグが `"true"` の場合、`getQueueConfigurations()` / `getPgConfigurations()` の挙動が変わり、
`gBufferOrch->getBufferObjectsWithNonZeroProfile()` を参照して有効プロファイルのポート/PG のみを返す。
`"false"` または未設定の場合は全ポートを対象とする。

また、`DEVICE_METADATA` テーブルへの変更イベントも購読しており（`handleDeviceMetadataTable()`、`flexcounterorch.cpp:488-523`）、
ランタイムでのフラグ変化にも対応する。

証跡: `flexcounterorch.cpp:104-120,149-153,488-523`

### 3. PortsOrch 経由の暗黙依存（gPortsOrch）

`doTask()` の先頭で `gPortsOrch->allPortsReady()` を確認し（`flexcounterorch.cpp:164-167`）、
PortsOrch が未初期化の場合は処理をスキップする（silent defer）。

`FLEX_COUNTER_STATUS=enable` 受信後、グループに応じて以下を呼び出す:

| グループ | 呼び出しメソッド | 説明 |
|---------|----------------|------|
| `PORT` | `gPortsOrch->generatePortCounterMap()` | ポートOIDリストをFLEX_COUNTER_DBに書き込む |
| `PORT_BUFFER_DROP` | `gPortsOrch->generatePortBufferDropCounterMap()` | バッファドロップカウンタ |
| `QUEUE` | `gPortsOrch->generateQueueMap()` + `addQueueFlexCounters()` | キューOIDリスト |
| `QUEUE_WATERMARK` | `gPortsOrch->generateQueueMap()` + `addQueueWatermarkFlexCounters()` | キューウォーターマーク |
| `PG_DROP` | `gPortsOrch->generatePriorityGroupMap()` + `addPriorityGroupFlexCounters()` | PGドロップ |
| `PG_WATERMARK` | `gPortsOrch->generatePriorityGroupMap()` + `addPriorityGroupWatermarkFlexCounters()` | PGウォーターマーク |
| `WRED_ECN_PORT` | `gPortsOrch->generateWredPortCounterMap()` | WRED ECNポートカウンタ |
| `WRED_ECN_QUEUE` | `gPortsOrch->generateQueueMap()` + `addWredQueueFlexCounters()` | WRED ECNキュー |
| `PORT_PHY_ATTR` | `gPortsOrch->generatePortPhyAttrCounterMap()` | 物理属性カウンタ |
| `PORT_PHY_SERDES_ATTR` | `gPortsOrch->generatePortPhySerdesAttrCounterMap()` | Serdes属性 |

これらメソッドがFLEX_COUNTER_DB `FLEX_COUNTER_TABLE|<group>|<oid>` に各ポート/キュー/PGのOIDリストを書き込む。

証跡: `flexcounterorch.cpp:235-295`

### 4. FabricPortsOrch 経由の暗黙依存（gFabricPortsOrch）

Fabric ポートが有効な場合も `gFabricPortsOrch->allPortsReady()` を確認する（`flexcounterorch.cpp:169-172`）。
`QUEUE` グループの enable 時に `gFabricPortsOrch->generateQueueStats()` も呼ぶ（`flexcounterorch.cpp:291-294`）。

証跡: `flexcounterorch.cpp:169-172,291-294`

### 5. IntfsOrch 経由の暗黙依存（gIntfsOrch）

`RIF` グループの `FLEX_COUNTER_STATUS=enable` 時に `gIntfsOrch->generateInterfaceMap()` を呼び出す（`flexcounterorch.cpp:283-286`）。
RIF (Router Interface) の OID リストが FLEX_COUNTER_DB に書き込まれる。

証跡: `flexcounterorch.cpp:283-286`

### 6. BufferOrch 経由の暗黙依存（gBufferOrch）

`BUFFER_POOL_WATERMARK` グループの enable 時に `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` を呼ぶ（`flexcounterorch.cpp:287-290`）。
また、`create_only_config_db_buffers=true` 時は `gBufferOrch->getBufferObjectsWithNonZeroProfile()` を参照して対象を絞り込む。

証跡: `flexcounterorch.cpp:287-290,554,623`

### 7. APP_DB:BUFFER_QUEUE / BUFFER_PG — Queue/PG 設定照合

`getQueueConfigurations()` (`flexcounterorch.cpp:538-607`) は APP_DB の `APP_BUFFER_QUEUE_TABLE_NAME` を参照し、
バッファプロファイルが非ゼロのキューインデックスのみを有効とする（`create_only_config_db_buffers=true` 時）。

`getPgConfigurations()` (`flexcounterorch.cpp:609-668`) も同様に `APP_BUFFER_PG_TABLE_NAME` を参照する。

これらは CONFIG_DB の `BUFFER_QUEUE` / `BUFFER_PG` テーブルとは別に、APP_DB を直接参照する。

証跡: `flexcounterorch.cpp:538-668`

### 8. VxlanTunnelOrch / FlowCounterRouteOrch / DashOrch — 動的 Orch 取得

`TUNNEL` グループの enable 時に `gDirectory.get<VxlanTunnelOrch*>()->generateTunnelCounterMap()` を呼ぶ（`flexcounterorch.cpp:295-299`）。
`FLOW_CNT_ROUTE` グループの enable 時に `gFlowCounterRouteOrch->generateRouteFlowStats()` を呼ぶ（`flexcounterorch.cpp:325-332`）。
DASH 系グループでは `DashOrch`、`DashHaOrch` を参照する。

### 9. warm-reboot: FLEX_COUNTER_DELAY_SEC による遅延

warm-reboot 時 (`WarmStart::isWarmStart()`) に `m_delayTimerExpired = false` のまま起動し、
`FLEX_COUNTER_DELAY_SEC = 60` 秒後に `SelectableTimer` が発火して `m_delayTimerExpired = true` になるまで doTask 全体をスキップする。

この 60 秒遅延中、CONFIG_DB に `FLEX_COUNTER_TABLE` の変更が届いても **一切処理されない**。
FLEX_COUNTER_DB は warm-reboot 前の状態を保持しているが、orchagent 側の更新は遅延する。

証跡: `flexcounterorch.cpp:44,127-136,155-158`

---

## 参照関係サマリ図

```
CONFIG_DB:FLEX_COUNTER_TABLE
  → FlexCounterOrch::doTask()
      ├─ [guard] gPortsOrch->allPortsReady()
      ├─ [guard] gFabricPortsOrch->allPortsReady()
      ├─ [guard] m_delayTimerExpired (warm-reboot 60s 遅延)
      ├─ [config] CONFIG_DB:DEVICE_METADATA.create_only_config_db_buffers
      ├─ [GROUP_TABLE] → FLEX_COUNTER_DB:FLEX_COUNTER_GROUP_TABLE|<group>
      │     (POLL_INTERVAL / FLEX_COUNTER_STATUS / STATS_MODE / BULK_CHUNK_SIZE)
      └─ [COUNTER_TABLE via Orch] → FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|<group>|<oid>
            ├─ gPortsOrch->generate*Map() ... PORT / QUEUE / PG / WRED
            ├─ gFabricPortsOrch->generateQueueStats() ... FABRIC_QUEUE
            ├─ gIntfsOrch->generateInterfaceMap() ... RIF
            ├─ gBufferOrch->generateBufferPoolWatermarkCounterIdList() ... BUFFER_POOL
            ├─ VxlanTunnelOrch->generateTunnelCounterMap() ... TUNNEL
            └─ gFlowCounterRouteOrch->generateRouteFlowStats() ... FLOW_CNT_ROUTE
```
