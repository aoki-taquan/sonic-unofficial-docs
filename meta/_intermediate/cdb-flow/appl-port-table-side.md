# APPL_DB PORT_TABLE SET/DEL 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-15
ソース:
- `sonic-swss/orchagent/portsorch.cpp` — `PortsOrch::initializePort()`, `PortsOrch::removePort()`, `PortsOrch::deInitPort()`, `PortsOrch::addLag()`, `PortsOrch::removeLag()`, `PortsOrch::initPortSupportedSpeeds()`, `PortsOrch::initPortCapAutoNeg()` 周辺, `PortsOrch::initHostTxReadyState()`, `PortsOrch::setHostTxReady()`, `PortsOrch::updateDbPortOperStatus()`, `PortsOrch::updateDbPortOperSpeed()`, `PortsOrch::updateDbPortOperFec()`, `PortsOrch::updateDbPortFlapCount()`, `PortsOrch::updateGearboxPortOperStatus()`, `PortsOrch::createPortBufferQueueCounterIds()`, `PortsOrch::createPortBufferPgCounters()`, `PortsOrch::generateQueueMapPerPort()`, `PortsOrch::generatePriorityGroupMapPerPort()`, `PortsOrch::refreshPortStateAutoNeg()`, `PortsOrch::refreshPortStateLinkTraining()`, `PortsOrch::initGearbox()`
- `sonic-swss-common/common/schema.h` — `STATE_PORT_TABLE_NAME`, `STATE_BUFFER_MAXIMUM_VALUE_TABLE`, `COUNTERS_PORT_NAME_MAP`, `COUNTERS_LAG_NAME_MAP`, `COUNTERS_SYSTEM_PORT_NAME_MAP`, `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP`, `COUNTERS_QUEUE_NAME_MAP`, `COUNTERS_QUEUE_PORT_MAP`, `COUNTERS_QUEUE_INDEX_MAP`, `COUNTERS_QUEUE_TYPE_MAP`, `COUNTERS_PG_NAME_MAP`, `COUNTERS_PG_PORT_MAP`, `COUNTERS_PG_INDEX_MAP`

---

## PortsOrch (orchagent/portsorch.cpp)

`PortsOrch` は APPL_DB `PORT_TABLE` を `Consumer`（`APP_PORT_TABLE_NAME`）として購読する。
SET（ポート初期化／属性更新） / DEL（ポート削除）に伴って、SAI 呼び出しのほかに 4 種類の DB に副次書き込みが発生する。

### SET (PORT_TABLE:<port>)

#### 1. STATE_DB / `PORT_TABLE`

ポート初期化時の能力情報、運用速度／FEC、host_tx_ready、LT/AN 状態などを `STATE_DB` の `PORT_TABLE` テーブルに書き込む（`m_portStateTable` は `STATE_PORT_TABLE_NAME` を参照）。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_portStateTable.set(alias, {{"supported_speeds", ...}})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`supported_speeds` | カンマ区切り uint list | `initPortSupportedSpeeds()` (`portsorch.cpp:3172`) — ポート初期化時 |
| `m_portStateTable.set(alias, {{"supported_fecs", ...}})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`supported_fecs` | カンマ区切り FEC mode list | `initPortCapFec()` (`portsorch.cpp:3320`) |
| `m_portStateTable.hset(alias, "host_tx_ready", ...)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`host_tx_ready` | `"true"` / `"false"` | `setHostTxReady()` (`portsorch.cpp:2274`) — admin_status の遷移時 |
| `m_portStateTable.set(port.m_alias, {{"speed", ...}})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`speed` | `"<Mbps>"` または `"N/A"` | `updateDbPortOperSpeed()` (`portsorch.cpp:9857`) — SAI からの oper speed 通知 |
| `m_portStateTable.set(port.m_alias, {{"fec", ...}})` | STATE_DB / `PORT_TABLE` | `<alias>` field=`fec` | FEC mode 文字列 | `updateDbPortOperFec()` (`portsorch.cpp:9870`) |
| `m_portStateTable.hdel(alias, "rmt_adv_speeds")` / `hset(alias, "rmt_adv_speeds", ...)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`rmt_adv_speeds` | uint list | `doPortTask()` autoneg 更新時 (`portsorch.cpp:4862`), `refreshPortStateAutoNeg()` (`portsorch.cpp:11338`) |
| `m_portStateTable.hset(alias, "link_training_status", ...)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`link_training_status` | `"on"` / `"off"` / `"trained"` / failure 文字列 | `doPortTask()` LT 更新時 (`portsorch.cpp:4907`), `refreshPortStateLinkTraining()` (`portsorch.cpp:11380`) |
| `m_portStateTable.hset(alias, "phy_ctrl_unreliable_los", ...)` | STATE_DB / `PORT_TABLE` | `<alias>` field=`phy_ctrl_unreliable_los` | `"true"` / `"false"` | `doPortTask()` unreliable_los 更新時 (`portsorch.cpp:5200`) |

コード証跡:
- `portsorch.cpp:725` — `m_portStateTable(stateDb, STATE_PORT_TABLE_NAME)`
- `schema.h:420` — `#define STATE_PORT_TABLE_NAME "PORT_TABLE"`

#### 2. STATE_DB / `BUFFER_MAX_PARAM_TABLE`

ポートごとの最大キュー / PG / headroom 情報を `STATE_DB` の `BUFFER_MAX_PARAM_TABLE` に書き込む。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_stateBufferMaximumValueTable->set(alias, fvVector)` | STATE_DB / `BUFFER_MAX_PARAM_TABLE` | `<alias>` fields=`max_headroom_size`/`max_priority_groups`/`max_queues` | uint | ポート初期化時 (`portsorch.cpp:7046`) |
| `m_stateBufferMaximumValueTable->del(alias)` | STATE_DB / `BUFFER_MAX_PARAM_TABLE` | `<alias>` | — | `deInitPort()` (`portsorch.cpp:4332`) |

コード証跡:
- `portsorch.cpp:790` — `m_stateBufferMaximumValueTable = ... STATE_BUFFER_MAXIMUM_VALUE_TABLE`
- `schema.h:480` — `#define STATE_BUFFER_MAXIMUM_VALUE_TABLE "BUFFER_MAX_PARAM_TABLE"`

#### 3. APPL_DB / `PORT_TABLE`（自テーブルへの書き戻し）

PortsOrch 自身が `APPL_DB PORT_TABLE` の oper / flap 情報を書き戻す（producer-side write）。これは Phase A `defaults` ブロックで詳述済みの "orchagent が書き込むフィールド" と同一であり、Phase F でも副次書込として再掲する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_portTable->set(port.m_alias, {{"flap_count", ...}, {"last_up_time", ...}/{"last_down_time", ...}})` | APPL_DB / `PORT_TABLE` | `<alias>` fields=`flap_count`/`last_up_time`/`last_down_time` | uint64 / UTC 文字列 | `updateDbPortFlapCount()` (`portsorch.cpp:3890`) — oper status 変化時 |
| `m_portTable->set(port.m_alias, {{"oper_status", ...}})` | APPL_DB / `PORT_TABLE` | `<alias>` field=`oper_status` | `"up"` / `"down"` | `updateDbPortOperStatus()` (`portsorch.cpp:3930`) |
| `m_portTable->hset(port.m_alias, "oper_status", "down")` | APPL_DB / `PORT_TABLE` | `<alias>` field=`oper_status` | `"down"` | warmboot 初期化 (`portsorch.cpp:6643`) |
| `m_portTable->hset(port.m_alias, "flap_count", flapCount)` | APPL_DB / `PORT_TABLE` | `<alias>` field=`flap_count` | uint64 | warmboot 初期化 (`portsorch.cpp:6656`) |
| `m_portTable->set(alias, {{"system_oper_status", ...}})` | APPL_DB / `PORT_TABLE` | `<alias>` field=`system_oper_status` | `"up"` / `"down"` | `updateGearboxPortOperStatus()` (`portsorch.cpp:11244`) — Gearbox 環境のみ |
| `m_portTable->set(alias, {{"line_oper_status", ...}})` | APPL_DB / `PORT_TABLE` | `<alias>` field=`line_oper_status` | `"up"` / `"down"` | `updateGearboxPortOperStatus()` (`portsorch.cpp:11259`) — Gearbox 環境のみ |

#### 4. COUNTERS_DB / 各種 NAME_MAP・INDEX_MAP・TYPE_MAP

ポート初期化時に SAI OID → 名前マップを `COUNTERS_DB` に登録する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_counterNameMapUpdater->setCounterNameMap(alias, port_id)` | COUNTERS_DB / `COUNTERS_PORT_NAME_MAP` | `""` field=`<alias>` | `<port OID>` | `initializePort()` 内 (`portsorch.cpp:4118`) |
| `m_counterLagTable->set("", {{lag_alias, lag_oid}})` | COUNTERS_DB / `COUNTERS_LAG_NAME_MAP` | `""` field=`<lag_alias>` | `<lag OID>` | `addLag()` (`portsorch.cpp:8022`) — LAG 作成時 |
| `m_counterSysPortTable->set("", {{sysport_alias, sysport_oid}})` | COUNTERS_DB / `COUNTERS_SYSTEM_PORT_NAME_MAP` | `""` field=`<sysport_alias>` | `<system port OID>` | voq switch のシステムポート初期化 (`portsorch.cpp:11000`) |
| `m_queueCounterNameMapUpdater->setCounterNameMap(queueVector)` | COUNTERS_DB / `COUNTERS_QUEUE_NAME_MAP` | `""` fields=`<alias>:<queueIndex>` | `<queue OID>` | `generateQueueMapPerPort()` (`portsorch.cpp:8524, 8749`) |
| `m_queuePortTable->set("", queuePortVector)` | COUNTERS_DB / `COUNTERS_QUEUE_PORT_MAP` | `""` fields=`<queue OID>` | `<port OID>` | `generateQueueMapPerPort()` (`portsorch.cpp:8750`) |
| `m_queueIndexTable->set("", queueIndexVector)` | COUNTERS_DB / `COUNTERS_QUEUE_INDEX_MAP` | `""` fields=`<queue OID>` | `<queueIndex>` | 同上 (`portsorch.cpp:8751`) |
| `m_queueTypeTable->set("", queueTypeVector)` | COUNTERS_DB / `COUNTERS_QUEUE_TYPE_MAP` | `""` fields=`<queue OID>` | `<queueType>` | 同上 (`portsorch.cpp:8752`) |
| `m_pgCounterNameMapUpdater->setCounterNameMap(pgVector)` | COUNTERS_DB / `COUNTERS_PG_NAME_MAP` | `""` fields=`<alias>:<pgIndex>` | `<pg OID>` | `generatePriorityGroupMapPerPort()` (`portsorch.cpp:8882, 8937`) |
| `m_pgPortTable->set("", pgPortVector)` | COUNTERS_DB / `COUNTERS_PG_PORT_MAP` | `""` fields=`<pg OID>` | `<port OID>` | 同上 (`portsorch.cpp:8883, 8938`) |
| `m_pgIndexTable->set("", pgIndexVector)` | COUNTERS_DB / `COUNTERS_PG_INDEX_MAP` | `""` fields=`<pg OID>` | `<pgIndex>` | 同上 (`portsorch.cpp:8884, 8939`) |
| `m_gbcounterTable->set("", {{alias+"_system"/"_line", oid}})` | COUNTERS_GB_DB / `COUNTERS_PORT_NAME_MAP` | `""` fields=`<alias>_system`/`<alias>_line` | `<gb port OID>` | Gearbox 初期化 (`portsorch.cpp:10653, 10656`) — Gearbox 環境のみ |

コード証跡:
- `portsorch.cpp:758-787` — `m_counter_db` および各 counter table の構築
- `schema.h:219-222` — `COUNTERS_PORT_NAME_MAP` / `COUNTERS_SYSTEM_PORT_NAME_MAP` / `COUNTERS_LAG_NAME_MAP` 等の定義

#### 5. FLEX_COUNTER_DB（FlexCounter 経由）

ポート / queue / PG ごとの flex counter ポーリング登録を `FLEX_COUNTER_DB` に書き込む。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|--------------------|-----------------|------|
| `port_stat_manager.setCounterIdList(port_id, ...)` → `startFlexCounterPolling()` → `gFlexCounterTable->set("PORT_STAT_COUNTER:<oid>", ...)` | FLEX_COUNTER_DB / `PORT_STAT_COUNTER:<oid>` | port stat 有効時、ポート初期化時 |
| `port_buffer_drop_stat_manager.setCounterIdList(...)` | FLEX_COUNTER_DB / `PORT_BUFFER_DROP_STAT:<oid>` | port buffer drop counter 有効時 |
| `port_phy_serdes_attr_manager.setCounterIdList(port_serdes_id, ...)` | FLEX_COUNTER_DB / `PORT_SERDES_STAT_COUNTER:<serdes_oid>` | port serdes 有効時 |
| queue / PG / WRED queue / PG drop の flex counter 登録 | FLEX_COUNTER_DB / `QUEUE_STAT_COUNTER` / `QUEUE_WATERMARK_STAT_COUNTER` / `PG_WATERMARK_STAT_COUNTER` / `PG_DROP_STAT_COUNTER` / `WRED_ECN_QUEUE_STAT_COUNTER` 等 | 各 counter 有効時 (`addQueueFlexCounters*`, `addPriorityGroupFlexCounters*`, `addWredQueueFlexCounters*`) |

コード証跡:
- `portsorch.cpp:8730-8745` — `addQueueFlexCountersPerPortPerQueueIndex` / `addQueueWatermarkFlexCountersPerPortPerQueueIndex` / `addWredQueueFlexCountersPerPortPerQueueIndex`
- `portsorch.cpp:8924-8938` — `addPriorityGroupFlexCountersPerPortPerPgIndex` / `addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex`
- `portsorch.cpp:10133` — `flex_counters_orch` 経由の有効判定

#### 6. ASIC_DB (SAI 経由)

SAI の `sai_port_api->create_port()` / `set_port_attribute()` / `remove_port()` 呼び出しを通じて、syncd が `ASIC_DB` の `ASIC_STATE:SAI_OBJECT_TYPE_PORT:<oid>` を書き込む。これは orchagent の直接 DB 書込ではなく、SAI → syncd → ASIC_DB のチェーンであるため、Phase F では明示的な操作行は計上しない（chain として記録）。

---

### DEL (PORT_TABLE:<port>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|--------------------|-----------------|------|
| `m_portTable->del(key)` | APPL_DB / `PORT_TABLE` | `<alias>` | `removePortFromLanesMap` 等 (`portsorch.cpp:4403`) |
| `m_stateBufferMaximumValueTable->del(alias)` | STATE_DB / `BUFFER_MAX_PARAM_TABLE` | `<alias>` | `deInitPort()` (`portsorch.cpp:4332`) |
| `m_counterNameMapUpdater->delCounterNameMap(alias)` | COUNTERS_DB / `COUNTERS_PORT_NAME_MAP` | field=`<alias>` | `deInitPort()` (`portsorch.cpp:4312`) |
| `m_counterLagTable->hdel("", lag.m_alias)` | COUNTERS_DB / `COUNTERS_LAG_NAME_MAP` | field=`<lag_alias>` | `removeLag()` (`portsorch.cpp:8095`) |
| `m_queueCounterNameMapUpdater->delCounterNameMap(name)` / `m_queuePortTable->hdel("", id)` / `m_queueIndexTable->hdel("", id)` / `m_queueTypeTable->hdel("", id)` | COUNTERS_DB / 各 QUEUE_* マップ | `<queue OID>` または `<alias>:<queueIndex>` | queue マップ解除 (`portsorch.cpp:8789-8797`) |
| `m_pgCounterNameMapUpdater->delCounterNameMap(name)` / `m_pgPortTable->hdel("", id)` / `m_pgIndexTable->hdel("", id)` | COUNTERS_DB / 各 PG_* マップ | `<pg OID>` または `<alias>:<pgIndex>` | PG マップ解除 (`portsorch.cpp:9081-9083`) |
| `gFlexCounterTable->del(...)` (各 FlexCounterManager 経由) | FLEX_COUNTER_DB / `PORT_STAT_COUNTER` / `QUEUE_STAT_COUNTER` / `PG_*` / `PORT_SERDES_STAT_COUNTER` 等 | `<oid>` | flex counter 停止時 |

---

## 副次 DB 書込なし（スコープ外）

- **CONFIG_DB**: PortsOrch は APPL_DB を consume し、CONFIG_DB へは書き込まない（CONFIG_DB は portmgrd / cfggen が書く側）。
- **ASIC_DB**: SAI 呼び出し経由で syncd が書き込む（orchagent の直接 DB 書込ではない）。

---

## 全体サマリ

| 副次書込先 DB | テーブル | トリガ |
|---|---|---|
| STATE_DB | `PORT_TABLE` | ポート能力 (`supported_speeds`/`supported_fecs`)、`host_tx_ready`、運用 `speed`/`fec`、`rmt_adv_speeds`、`link_training_status`、`phy_ctrl_unreliable_los` の更新 |
| STATE_DB | `BUFFER_MAX_PARAM_TABLE` | ポート初期化／削除で `max_headroom_size`/`max_priority_groups`/`max_queues` を set/del |
| APPL_DB | `PORT_TABLE`（自テーブル書き戻し） | `oper_status`/`flap_count`/`last_up_time`/`last_down_time`/`system_oper_status`/`line_oper_status` の書き戻し |
| COUNTERS_DB | `COUNTERS_PORT_NAME_MAP` / `COUNTERS_LAG_NAME_MAP` / `COUNTERS_SYSTEM_PORT_NAME_MAP` / `COUNTERS_QUEUE_*` / `COUNTERS_PG_*` | ポート / LAG / queue / PG ごとの OID 名前マップ登録・解除 |
| FLEX_COUNTER_DB | `PORT_STAT_COUNTER` / `PORT_BUFFER_DROP_STAT` / `PORT_SERDES_STAT_COUNTER` / `QUEUE_*` / `PG_*` | ポート / queue / PG flex counter ポーリングの開始・停止 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_PORT:<oid>` 等 | SAI 経由で syncd が書く（chain、orchagent の直接書込ではない） |
