# FLEX_COUNTER_TABLE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/flex-counter-table.md` Phase C 追加分。
YANG に leafref 定義なし。以下に示す全依存は実装レベルの暗黙参照。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/flexcounterorch.cpp` | `FlexCounterOrch::doTask()` — SET/DEL ハンドラ、各 Orch への委譲 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | `FlexCounterOrch::FlexCounterOrch()` — コンストラクタ、`DEVICE_METADATA` 読み込み、warm-reboot タイマー設定 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | `handleDeviceMetadataTable()` — `DEVICE_METADATA` の動的変更ハンドリング |

## YANG leafref

なし。`FLEX_COUNTER_TABLE` は独立した管理テーブルで、YANG 上の leafref 依存を持たない。

## 暗黙参照 (実装レベル)

### 1. PORT（PortsOrch / PortInitDone ゲート）

- **参照先テーブル**: `PORT`（CONFIG_DB、PortsOrch 管理）
- **参照方向**: ゲート依存（`allPortsReady()` チェック）
- **条件**: 全 SET 処理の前提条件として毎回チェック
- **参照元 (flexcounterorch.cpp)**:
  - L164-167 — `if (gPortsOrch && !gPortsOrch->allPortsReady()) { return; }`
- **意味**: PORT テーブルが全ポート初期化完了するまで `FLEX_COUNTER_TABLE` への全 SET が `m_toSync` に蓄積される。PortInitDone 後に自動再処理。

### 2. FLOW_COUNTER_ROUTE_PATTERN（FlowCounterRouteOrch）

- **参照先テーブル**: `FLOW_COUNTER_ROUTE_PATTERN`（CONFIG_DB）
- **参照方向**: 実行時読み込み（`generateRouteFlowStats()` が本テーブルを走査）
- **条件**: `FLOW_CNT_ROUTE` グループを `enable` にしたとき
- **参照元 (flexcounterorch.cpp)**:
  - L324-336 — `if (gFlowCounterRouteOrch && gFlowCounterRouteOrch->getRouteFlowCounterSupported() && key == FLOW_CNT_ROUTE_KEY)`
  - L329 — `gFlowCounterRouteOrch->generateRouteFlowStats()` — 本テーブルのパターンをもとにルートカウンタ付与
- **意味**: `FLOW_COUNTER_ROUTE_PATTERN` が未設定でも enable は成功するが、対象ルートが 0 件となる（silent）。パターンを先に投入してから `FLOW_CNT_ROUTE` を enable するのが推奨順序。

### 3. DEVICE_METADATA（コンストラクタ + 動的変更）

- **参照先テーブル**: `DEVICE_METADATA`（CONFIG_DB）
- **参照方向**: 初期化時読み込み + 購読
- **参照元 (flexcounterorch.cpp)**:
  - L114-125 — コンストラクタで `m_deviceMetadataConfigTable.hget("localhost", "create_only_config_db_buffers", ...)` を呼び出し
  - L488+ — `handleDeviceMetadataTable()` で動的変更も処理
- **意味**: 読み取り失敗時は `SWSS_LOG_ERROR` を出力し `m_createOnlyConfigDbBuffers = false` のまま（バッファカウンタはデフォルト動作）。

### 4. COUNTERS_DB（出力先 DB）

- **参照先 DB**: `COUNTERS_DB`（読み書き先）
- **参照種別**: 書き込み先（SAI polling 結果）
- **参照元**: `portsorch.cpp`, `intfsorch.cpp`, `bufferorch.cpp` 等（各 Orch の generateXxxMap / generateXxxCounterIdList）
- **意味**: `FLEX_COUNTER_STATUS = enable` にすると `COUNTERS_DB` への更新が開始される。disable の間は SAI polling が止まり `COUNTERS_DB` の値は古くなる（0 になるのではなく最後の値が残る）。

### 5. 複数 Orch への委譲（グループ別）

`FLEX_COUNTER_STATUS = enable` 受信時に、グループに応じて以下 Orch に処理を委譲する。各 Orch が nullptr の場合は silent skip（エラーなし）。

| グループ | 委譲先 Orch | メソッド | コード行 |
|---------|-----------|---------|---------|
| `PORT` | `gPortsOrch` | `generatePortCounterMap()` | L239 |
| `PORT_BUFFER_DROP` | `gPortsOrch` | `generatePortBufferDropCounterMap()` | L244 |
| `QUEUE` | `gPortsOrch` | `generateQueueMap()` + `addQueueFlexCounters()` | L249-251 |
| `QUEUE_WATERMARK` | `gPortsOrch` | `generateQueueMap()` + `addQueueWatermarkFlexCounters()` | L255-257 |
| `PG_DROP` | `gPortsOrch` | `generatePriorityGroupMap()` + `addPriorityGroupFlexCounters()` | L261-263 |
| `PG_WATERMARK` | `gPortsOrch` | `generatePriorityGroupMap()` + `addPriorityGroupWatermarkFlexCounters()` | L267-269 |
| `WRED_ECN_PORT` | `gPortsOrch` | `generateWredPortCounterMap()` | L273 |
| `WRED_ECN_QUEUE` | `gPortsOrch` | `generateQueueMap()` + `addWredQueueFlexCounters()` | L278-280 |
| `RIF` | `gIntfsOrch` | `generateInterfaceMap()` | L285 |
| `BUFFER_POOL_WATERMARK` | `gBufferOrch` | `generateBufferPoolWatermarkCounterIdList()` | L289 |
| `TUNNEL` | `VxlanTunnelOrch` (Directory) | `generateTunnelCounterMap()` | L297 |
| `ENI` | `DashOrch` (Directory) | `handleFCStatusUpdate()` | L301 |
| `DASH_METER` | `DashOrch` (Directory) | `handleMeterFCStatusUpdate()` | L305 |
| `HA_SET` | `DashHaOrch` (Directory) | `handleHaSetFCStatusUpdate()` | L309 |
| `FLOW_CNT_TRAP` | `gCoppOrch` | `generateHostIfTrapCounterIdList()` | L316 |
| `FLOW_CNT_ROUTE` | `gFlowCounterRouteOrch` | `generateRouteFlowStats()` | L329 |
| `SRV6` | `gSrv6Orch` | `setCountersState(true)` | L339 |
| `PORT_PHY_ATTR` | `gPortsOrch` | `generatePortPhyAttrCounterMap()` + `generatePortPhySerdesAttrCounterMap()` | L348-354 |
| `SWITCH` | `gSwitchOrch` | `generateSwitchCounterIdList()` | L372 |

### 6. FabricPortsOrch（Fabric ポートゲート）

- **参照先**: `gFabricPortsOrch`
- **条件**: 毎回 `allFabricPortsReady()` チェック
- **参照元**: L169-172 — `if (gFabricPortsOrch && !gFabricPortsOrch->allPortsReady()) { return; }`
- **意味**: Fabric ポートが未準備の間も `doTask` が早期 return する（chassis 構成のみ）。

## 非充足時サマリ

| 依存 | 非充足時の挙動 | silent/error |
|-----|--------------|-------------|
| PORT (PortInitDone 未完) | 全 SET を蓄積・後回し | silent |
| FLOW_COUNTER_ROUTE_PATTERN 空 | カウンタ付与ルート 0 件 | silent |
| DEVICE_METADATA 読み取り失敗 | `m_createOnlyConfigDbBuffers = false` で続行 | error ログ |
| 各 Orch null | 対象グループの enable が無効化 | silent |
| `getRouteFlowCounterSupported() == false` | `FLOW_CNT_ROUTE` enable が SAI 適用ゼロ | silent |
| `gCoppOrch == nullptr` | `FLOW_CNT_TRAP` enable が無効 | silent |

## 結論

`FLEX_COUNTER_TABLE` は YANG leafref を持たない独立テーブルだが、`FlexCounterOrch` が orchagent 内の複数 Orch に処理を委譲するため、ポートや各種機能 Orch の初期化状態に依存する。最も重要な依存は `PortInitDone` ゲートと `FLOW_COUNTER_ROUTE_PATTERN` の有無。
