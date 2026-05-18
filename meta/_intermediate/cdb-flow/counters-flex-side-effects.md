# counters-flex Phase F — 副次 DB 書込スキャンノート

Generated: 2026-05-18  
Target doc: docs/reference/config-db/counters-flex.md

対象: `FLEX_COUNTER_TABLE|<group>` への `FLEX_COUNTER_STATUS = enable/disable` 受信時に
`FlexCounterOrch::doTask()` → 各 generateXxxMap() が引き起こす副次 DB 書き込みおよびシステム状態変化。

---

## 副次書き込み一覧

### 1. FLEX_COUNTER_DB — per-OID エントリ (`*_COUNTER_ID_LIST` / `*_ATTR_ID_LIST`)

`generatePortCounterMap()` / `generateQueueMap()` / `generatePriorityGroupMap()` 等は
`FlexCounterManager::setCounterIdList()` 経由で `FLEX_COUNTER_DB` へ per-OID エントリを書き込む。

これが **主作用** でもあるが、本ページの CONFIG_DB/FLEX_COUNTER_TABLE 視点では副次 DB への書き込みと位置づける。

| グループ | 書き込み先 DB | テーブル / キー形式 |
|---------|------------|---------------|
| PORT / PORT_BUFFER_DROP / WRED_ECN_PORT | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:PORT_STAT_COUNTER:<oid>` |
| QUEUE / QUEUE_WATERMARK / WRED_ECN_QUEUE | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:QUEUE_STAT_COUNTER:<oid>` |
| PG_DROP / PG_WATERMARK | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:PG_DROP_STAT_COUNTER:<oid>` |
| RIF | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:RIF_STAT_COUNTER:<oid>` |
| BUFFER_POOL_WATERMARK | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:BUFFER_POOL_WATERMARK_STAT_COUNTER:<oid>` |
| TUNNEL | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:TUNNEL_STAT_COUNTER:<oid>` |
| ACL | FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:ACL_STAT_COUNTER:<oid>` |

evidence: `portsorch.cpp:9118-9125` (`port_stat_manager.setCounterIdList`), `intfsorch.cpp:1527-1545` (`addRifToFlexCounter`)

### 2. COUNTERS_DB — name map (COUNTERS_PORT_NAME_MAP / COUNTERS_QUEUE_NAME_MAP / COUNTERS_PG_NAME_MAP)

`PortsOrch` は初期化時に `CounterNameMapUpdater` を作成し、ポート / キュー / PG ごとに
`COUNTERS_DB` 内のエイリアス→OID マップを管理する。

`FLEX_COUNTER_TABLE|PORT = enable` 受信で `generatePortCounterMap()` が呼ばれると、
`m_counterNameMapUpdater->setCounterNameMap(alias, oid)` により `COUNTERS_PORT_NAME_MAP` が更新される。
QUEUE / PG enable でも同様に `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` が更新される。

| グループ | 書き込み先 | キー/フィールド |
|---------|----------|--------------|
| PORT | `COUNTERS_DB COUNTERS_PORT_NAME_MAP` | `<alias>` → `<oid>` |
| QUEUE | `COUNTERS_DB COUNTERS_QUEUE_NAME_MAP` | `<Ethernet0:0>` → `<oid>` |
| PG_DROP / PG_WATERMARK | `COUNTERS_DB COUNTERS_PG_NAME_MAP` | `<Ethernet0:0>` → `<oid>` |

evidence: `portsorch.cpp:759,778,785,4118,8524,8749,8882,8937`

### 3. COUNTERS_DB — RIF name map (COUNTERS_RIF_NAME_MAP / COUNTERS_RIF_TYPE_MAP)

`FLEX_COUNTER_TABLE|RIF = enable` 受信で `gIntfsOrch->generateInterfaceMap()` が呼ばれ、
タイマー経由で `addRifToFlexCounter()` → `m_rifNameTable->set()` が `COUNTERS_DB` の
`COUNTERS_RIF_NAME_MAP` と `COUNTERS_RIF_TYPE_MAP` を更新する。

evidence: `intfsorch.cpp:1527-1545`, `intfsorch.cpp:1576-1580`

### 4. PortsOrch::flushCounters() — pending な FLEX_COUNTER_DB 書き込みのフラッシュ

`FLEX_COUNTER_STATUS` フィールドを処理した後、`gPortsOrch->flushCounters()` が呼ばれる
(`flexcounterorch.cpp:375-378`)。`counter_managers` リストに登録された全 `FlexCounterManager` に対して
`flush()` を実行し、バッファ済みの FLEX_COUNTER_DB 書き込みを即時 Redis に送信する。

enable / disable どちらの場合も呼ばれるため、設定変更後の FLEX_COUNTER_DB が一時的に中間状態に
なることはない。

evidence: `flexcounterorch.cpp:375-378`, `portsorch.cpp:9595-9601`

### 5. 各 Orch への状態変化通知

FLEX_COUNTER_STATUS の enable/disable を受信すると、FlexCounterOrch 内部フラグ
(`m_port_counter_enabled`, `m_queue_enabled`, `m_pg_enabled` 等) が更新される。
これらのフラグは他の Orch から `getPortCountersState()` 等の getter 経由で参照される。

| 呼び出し先 | enable 時の副次効果 |
|---------|----------------|
| `gCoppOrch->generateHostIfTrapCounterIdList()` | CoppOrch が FLOW_COUNTER_ID_LIST を FLEX_COUNTER_DB に書き込む |
| `gCoppOrch->clearHostIfTrapCounterIdList()` | CoppOrch が FLEX_COUNTER_DB から FLOW_COUNTER_ID_LIST を削除 |
| `gSrv6Orch->setCountersState(true/false)` | Srv6Orch が SRV6_COUNTER_ID_LIST を更新 |
| `gSwitchOrch->generateSwitchCounterIdList()` | SwitchOrch が SWITCH_COUNTER_ID_LIST を FLEX_COUNTER_DB に書き込む |
| `gFlowCounterRouteOrch->generateRouteFlowStats()` | RouteFlowCounterOrch が ROUTE_FLOW_COUNTER を FLEX_COUNTER_DB に書き込む |
| `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` | BufferOrch がバッファプール OID をリストアップして FLEX_COUNTER_DB に書き込む |

evidence: `flexcounterorch.cpp:287-340`
