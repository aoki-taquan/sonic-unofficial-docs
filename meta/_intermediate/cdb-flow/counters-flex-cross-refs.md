# counters-flex — Phase C 調査証跡 (cross-table refs)

調査日: 2026-05-17  
調査対象: `sonic-swss/orchagent/flexcounterorch.cpp` 全行精読

## 概要

`FLEX_COUNTER_TABLE` の個別カウンタフィールド（COUNTER_ID_LIST 系）を生成する
`FlexCounterOrch` は、起動時および `enable` 受信時に複数のテーブル・グローバル変数を
暗黙参照して動作を決定する。これらは YANG leafref として定義されていない。

## 参照先一覧

### 1. DEVICE_METADATA|localhost → create_only_config_db_buffers

**参照箇所**: `FlexCounterOrch::FlexCounterOrch()` コンストラクタ (line ~110-125)  
**参照 DB**: CONFIG_DB  
**参照方向**: 読み取り（起動時 1 回）

```cpp
m_deviceMetadataConfigTable.hget("localhost", "create_only_config_db_buffers", createOnlyConfigDbBuffersValue)
```

`create_only_config_db_buffers=true` の場合、QUEUE/PG グループの counter map 生成時に
「全キュー/全PG を対象」ではなく、APP_DB の `BUFFER_QUEUE`/`BUFFER_PG` で
non-zero profile が設定されているポートのキュー/PG のみを登録する。
ハンドラが動的に `create_only_config_db_buffers` 変更を監視する
`handleDeviceMetadataTable()` も存在する（line ~488-522）。

### 2. APP_DB:BUFFER_QUEUE_TABLE（APP_BUFFER_QUEUE_TABLE_NAME）

**参照箇所**: `FlexCounterOrch::getQueueConfigurations()` (line ~538-607)  
**参照 DB**: APP_DB  
**参照方向**: 読み取り（QUEUE/QUEUE_WATERMARK/WRED_ECN_QUEUE の enable 時）  
**発動条件**: `create_only_config_db_buffers=true` かつ `gMySwitchType != "voq"`

```cpp
gBufferOrch->getBufferObjectsWithNonZeroProfile(portQueueKeys, APP_BUFFER_QUEUE_TABLE_NAME);
```

non-zero buffer profile が設定されたポート+キュー範囲のみを FLEX_COUNTER_DB に登録。
この APP_DB テーブルが空の場合、QUEUE カウンタが一切 FLEX_COUNTER_DB に書き込まれない。

### 3. APP_DB:BUFFER_PG_TABLE（APP_BUFFER_PG_TABLE_NAME）

**参照箇所**: `FlexCounterOrch::getPgConfigurations()` (line ~609-668)  
**参照 DB**: APP_DB  
**参照方向**: 読み取り（PG_DROP/PG_WATERMARK の enable 時）  
**発動条件**: `create_only_config_db_buffers=true`

```cpp
gBufferOrch->getBufferObjectsWithNonZeroProfile(portPgKeys, APP_BUFFER_PG_TABLE_NAME);
```

non-zero profile の PG のみを FLEX_COUNTER_DB に登録。

### 4. グローバル Orch ポインタ（暗黙的な他テーブル依存）

`doTask()` は以下のグローバル Orch が初期化済みであることを前提とする：

| グローバル | 対応テーブル / 機能 | enable グループ |
|---|---|---|
| `gPortsOrch` | PORT_TABLE (APP_DB) | PORT, PORT_BUFFER_DROP, QUEUE, PG_*, WRED_*, PORT_PHY_ATTR |
| `gFabricPortsOrch` | FABRIC_PORT_TABLE | FABRIC_STAT, FABRIC_QUEUE |
| `gIntfsOrch` | INTF_TABLE (APP_DB) | RIF |
| `gBufferOrch` | BUFFER_POOL_TABLE (APP_DB) | BUFFER_POOL_WATERMARK |
| `gCoppOrch` | COPP_TABLE (APP_DB) | FLOW_CNT_TRAP |
| `gFlowCounterRouteOrch` | ROUTE_TABLE (APP_DB) | FLOW_CNT_ROUTE |
| `gSrv6Orch` | SRV6 系テーブル | SRV6 |
| `gSwitchOrch` | SWITCH_TABLE (APP_DB) | SWITCH |
| `vxlan_tunnel_orch` (gDirectory) | VXLAN_TUNNEL_TABLE | TUNNEL |
| `dash_orch` (gDirectory) | DASH_ENI_TABLE | ENI, DASH_METER |
| `dash_ha_orch` (gDirectory) | DASH_HA_SET_TABLE | HA_SET |

各 Orch が null ポインタの場合、対応グループの enable 処理はスキップ（`if(gPortsOrch && ...)` 形式ガード）。
YANG 定義には存在しない実装上の制約。

### 5. PORT 存在確認（gPortsOrch.getPort）

`getQueueConfigurations()` 内で `gPortsOrch->getPort(configPortName, port)` を呼んで
`port.m_host_tx_queue` を参照する。CPU TX キューが設定済みポートでは対応キューを追加登録。

## YANG leafref との乖離

これらの参照はいずれも YANG leafref として定義されていない。
`sonic-flex_counter.yang` には `FLEX_COUNTER_TABLE` のフィールド定義はあるが、
`DEVICE_METADATA|localhost|create_only_config_db_buffers` や APP_DB テーブルへの
leafref 制約は記述されていない。
