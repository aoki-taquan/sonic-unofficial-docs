# flex-counter-table — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / FLEX_COUNTER_TABLE`
対象ソース:

- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/saihelper.cpp`
- `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## スキャン結果

### FLEX_COUNTER_DB 書込 (`FLEX_COUNTER_GROUP_TABLE` / `FLEX_COUNTER_TABLE`)

`FlexCounterOrch` が CONFIG_DB `FLEX_COUNTER_TABLE` の変化を受けて `setFlexCounterGroupOperation()` → `operateFlexCounterGroupDatabase()` を呼び出し、`FLEX_COUNTER_DB` の `FLEX_COUNTER_GROUP_TABLE` に書込む（gTraditionalFlexCounter=true 時）。gTraditionalFlexCounter=false 時は SAI Redis 属性 `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` 経由で syncd に通知する。

#### FLEX_COUNTER_GROUP_TABLE (flexcounterorch → saihelper)

| 操作 | タイミング | evidence |
|---|---|---|
| `flexCounterGroupTable->set(group, fvTuples)` — FLEX_COUNTER_STATUS を enable/disable | `FLEX_COUNTER_STATUS` フィールド変化時 | `saihelper.cpp:884`, `flexcounterorch.cpp:380` |
| `flexCounterGroupTable->set(group, fvTuples)` — POLL_INTERVAL 更新 | `POLL_INTERVAL` フィールド変化時 | `saihelper.cpp:879`, `flexcounterorch.cpp:193` |
| `flexCounterGroupTable->set(group, fvTuples)` — BULK_CHUNK_SIZE 更新 | `BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX` フィールド変化時 | `flexcounterorch.cpp:404` |
| Gearbox 用 `gGearBoxFlexCounterGroupTable->set(group, fvTuples)` | `PORT` / `MACSEC*` グループ、gearbox 有効時 | `flexcounterorch.cpp:386` |
| `PORT_PHY_SERDES_ATTR` グループも連動更新 | `PORT_PHY_ATTR` 変化時に自動で同値設定 | `flexcounterorch.cpp:392` |

書込キーパターン: `FLEX_COUNTER_GROUP_TABLE|<group-name>`（例: `FLEX_COUNTER_GROUP_TABLE|PORT`）

書込フィールド（FLEX_COUNTER_DB）:

| フィールド | 内容 |
|---|---|
| `FLEX_COUNTER_STATUS` | `enable` / `disable` |
| `POLL_INTERVAL` | ポーリング間隔 (ms) 文字列 |
| `BULK_CHUNK_SIZE` | bulk API チャンクサイズ / `"NULL"` |
| `BULK_CHUNK_SIZE_PER_PREFIX` | プレフィクス別チャンクサイズ / `"NULL"` |

#### FLEX_COUNTER_TABLE (`startFlexCounterPolling` / `stopFlexCounterPolling`)

`gPortsOrch->generatePortCounterMap()` 等が `FlexCounterManager::setCounterIdList()` を経由して `startFlexCounterPolling()` を呼び出し、各オブジェクト（ポート / キュー / PG 等）の COUNTER_ID_LIST を書込む。

| 操作 | タイミング | evidence |
|---|---|---|
| `flexCounterTable->set(key, fvTuples)` — COUNTER_ID_LIST / ATTR_ID_LIST 投入 | `FLEX_COUNTER_STATUS=enable` 受信後、各 generateXxxMap() 呼び出し時 | `saihelper.cpp:1047`, `flex_counter_manager.cpp:225` |
| `flexCounterTable->del(key)` — ポーリング停止 | `FLEX_COUNTER_STATUS=disable` 時 / オブジェクト削除時 | `saihelper.cpp:1075` |

書込キーパターン: `FLEX_COUNTER_TABLE|<group-name>:<oid>`（例: `FLEX_COUNTER_TABLE|PORT:0x1000000000023`）

書込フィールド:

| フィールド | 内容 |
|---|---|
| `PORT_COUNTER_ID_LIST` | SAI ポート統計 ID リスト (カンマ区切り) |
| `PORT_DEBUG_COUNTER_ID_LIST` | バッファドロップ統計 ID リスト |
| `QUEUE_COUNTER_ID_LIST` | キュー統計 ID リスト |
| `QUEUE_WATERMARK_ID_LIST` | キュー watermark ID リスト |
| `PG_COUNTER_ID_LIST` | PG ドロップ統計 ID リスト |
| `PG_WATERMARK_ID_LIST` | PG watermark 統計 ID リスト |
| `RIF_COUNTER_ID_LIST` | RIF 統計 ID リスト |
| `TUNNEL_COUNTER_ID_LIST` | トンネル統計 ID リスト |
| `STATS_MODE` | `STATS_MODE_READ` / `STATS_MODE_READ_AND_CLEAR` |

### COUNTERS_DB 書込

`PortsOrch` コンストラクタ時、および `generatePortCounterMap()` 等のマップ生成時に COUNTERS_DB にポート / キュー / PG の名前→OID マッピングを書込む。`FLEX_COUNTER_TABLE` の enable 受信が直接トリガになる。

| 操作 | タイミング | evidence |
|---|---|---|
| `m_counterNameMapUpdater->set(port_name, oid)` — COUNTERS_PORT_NAME_MAP 更新 | `generatePortCounterMap()` (PORT=enable 受信後) | `portsorch.cpp:759, 9102` |
| `m_queueCounterNameMapUpdater->set(key, oid)` — COUNTERS_QUEUE_NAME_MAP 更新 | `generateQueueMap()` (QUEUE=enable 受信後) | `portsorch.cpp:778` |
| `m_pgCounterNameMapUpdater->set(key, oid)` — COUNTERS_PG_NAME_MAP 更新 | `generatePriorityGroupMap()` (PG_DROP / PG_WATERMARK=enable 受信後) | `portsorch.cpp:785` |
| `m_counterLagTable->set(lag_name, oid)` — COUNTERS_LAG_NAME_MAP | LAG ポート追加時 | `portsorch.cpp:762` |
| `m_voqTable->set(...)` — COUNTERS_VOQ_NAME_MAP | VOQ chassis 時 | `portsorch.cpp:779` |
| `m_queuePortTable->set(...)` — COUNTERS_QUEUE_PORT_MAP | キュー→ポート逆引き | `portsorch.cpp:780` |
| `m_queueIndexTable->set(...)` — COUNTERS_QUEUE_INDEX_MAP | キュー→インデックス逆引き | `portsorch.cpp:781` |
| `m_queueTypeTable->set(...)` — COUNTERS_QUEUE_TYPE_MAP | キュー type (ucast/mcast) 逆引き | `portsorch.cpp:782` |
| `m_pgPortTable->set(...)` — COUNTERS_PG_PORT_MAP | PG→ポート逆引き | `portsorch.cpp:786` |
| `m_pgIndexTable->set(...)` — COUNTERS_PG_INDEX_MAP | PG→インデックス逆引き | `portsorch.cpp:787` |

書込キーパターン例:

| テーブル | キー例 |
|---|---|
| `COUNTERS_PORT_NAME_MAP` | `""` (hash: port_name → OID) |
| `COUNTERS_QUEUE_NAME_MAP` | `""` (hash: `Ethernet0:0` → OID) |
| `COUNTERS_PG_NAME_MAP` | `""` (hash: `Ethernet0:0` → OID) |
| `COUNTERS_LAG_NAME_MAP` | `""` (hash: lag_name → OID) |
| `COUNTERS_QUEUE_PORT_MAP` | `""` (hash: queue_OID → port_OID) |
| `COUNTERS_QUEUE_INDEX_MAP` | `""` (hash: queue_OID → index) |
| `COUNTERS_QUEUE_TYPE_MAP` | `""` (hash: queue_OID → ucast/mcast) |
| `COUNTERS_PG_PORT_MAP` | `""` (hash: pg_OID → port_OID) |
| `COUNTERS_PG_INDEX_MAP` | `""` (hash: pg_OID → index) |

### ASIC_DB 副次書込

`syncd` が FLEX_COUNTER_DB の変化を受けて SAI API `sai_*_stats_ext()` / `sai_*_bulk_stats()` を呼び出し、取得したカウンタ値を `COUNTERS_DB` の各 OID キーに書込む（syncd の責務、flexcounterorch は直接 ASIC_DB へは書かない）。

## 副次書込まとめ

| 副次 DB | テーブル | 操作 | キーパターン | フィールド | ソース |
|---|---|---|---|---|---|
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE` | set | `FLEX_COUNTER_GROUP_TABLE\|<group>` | FLEX_COUNTER_STATUS, POLL_INTERVAL, BULK_CHUNK_SIZE 等 | `saihelper.cpp:884`, `flexcounterorch.cpp:380` |
| FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE` | set | `FLEX_COUNTER_TABLE\|<group>:<oid>` | PORT_COUNTER_ID_LIST, QUEUE_COUNTER_ID_LIST, STATS_MODE 等 | `saihelper.cpp:1047` |
| FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE` | del | `FLEX_COUNTER_TABLE\|<group>:<oid>` | (全削除) | `saihelper.cpp:1075` |
| COUNTERS_DB | `COUNTERS_PORT_NAME_MAP` | set | `""` (hash) | port_name → OID | `portsorch.cpp:759,9102` |
| COUNTERS_DB | `COUNTERS_QUEUE_NAME_MAP` | set | `""` (hash) | `Port:index` → OID | `portsorch.cpp:778` |
| COUNTERS_DB | `COUNTERS_PG_NAME_MAP` | set | `""` (hash) | `Port:index` → OID | `portsorch.cpp:785` |
| COUNTERS_DB | `COUNTERS_QUEUE_PORT_MAP` | set | `""` (hash) | queue_OID → port_OID | `portsorch.cpp:780` |
| COUNTERS_DB | `COUNTERS_QUEUE_INDEX_MAP` | set | `""` (hash) | queue_OID → index | `portsorch.cpp:781` |
| COUNTERS_DB | `COUNTERS_QUEUE_TYPE_MAP` | set | `""` (hash) | queue_OID → type | `portsorch.cpp:782` |
| COUNTERS_DB | `COUNTERS_PG_PORT_MAP` | set | `""` (hash) | pg_OID → port_OID | `portsorch.cpp:786` |
| COUNTERS_DB | `COUNTERS_PG_INDEX_MAP` | set | `""` (hash) | pg_OID → index | `portsorch.cpp:787` |
