# APPL_DB BUFFER_* 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/bufferorch.cpp` (commit `4305596156d70e9797e8a881b3d19b46de0bce0d`)

`BufferOrch` は `APPL_DB` の `BUFFER_POOL_TABLE` / `BUFFER_PROFILE_TABLE` / `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` / `BUFFER_PORT_*_PROFILE_LIST_TABLE` を購読する SAI 反映 orch だが、SET/DEL とは別に **STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB** に副次書込を行う。本書はその全件マトリクス。

---

## 1. STATE_DB 書込

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 / トリガ | evidence |
|------|------------------|-----------------|--------------|----------|
| `m_stateBufferMaximumValueTable.set("global", [{mmu_size}])` | STATE_DB / `BUFFER_MAX_PARAM_TABLE` (`STATE_BUFFER_MAXIMUM_VALUE_TABLE`) | key=`global`, field=`mmu_size` (bytes; `SAI_SWITCH_ATTR_MAX_BUFFER_SIZE` × 1024) | `BufferOrch` コンストラクタの末尾で `getMMUSize()` 起動 → SAI から MMU 全体サイズ取得後 1 回だけ書込 | `bufferorch.cpp:53-62`, `bufferorch.cpp:206-230` |

> STATE_DB への書込は起動時の MMU サイズ 1 件のみ。SET/DEL ハンドラ内では STATE_DB 書込を行わない。

---

## 2. COUNTERS_DB 書込

`m_counterNameMapUpdater = new CounterNameMapUpdater("COUNTERS_DB", COUNTERS_BUFFER_POOL_NAME_MAP)` を介して COUNTERS_DB の `COUNTERS_BUFFER_POOL_NAME_MAP` テーブル（buffer pool name → SAI OID マップ）を更新する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 / トリガ | evidence |
|------|------------------|-----------------|--------------|----------|
| `m_counterNameMapUpdater->setCounterNameMap(object_name, sai_object)` | COUNTERS_DB / `COUNTERS_BUFFER_POOL_NAME_MAP` | field=`<pool_name>` value=`<sai_object_id>` (HSET) | `processBufferPool()` の SET で SAI `create_buffer_pool()` 成功直後 (新規 pool 作成時のみ) | `bufferorch.cpp:546` |
| `m_counterNameMapUpdater->delCounterNameMap(object_name)` | COUNTERS_DB / `COUNTERS_BUFFER_POOL_NAME_MAP` | field=`<pool_name>` (HDEL) | `processBufferPool()` の DEL で `remove_buffer_pool()` 成功後 | `bufferorch.cpp:586` |

> BUFFER_PROFILE / BUFFER_PG / BUFFER_QUEUE / BUFFER_PORT_*_PROFILE_LIST には pool 相当の name map は存在しない (PG / Queue のマップは PortsOrch 側で管理)。

### 関連: PortsOrch 経由の PG/Queue カウンタ作成 (間接トリガ)

`processQueue()` / `processPriorityGroup()` は buffer profile attach 成功直後に、`FlexCounterOrch::isCreateOnlyConfigDbBuffers()` が true のとき `gPortsOrch->createPortBufferQueueCounters()` / `createPortBufferPgCounters()` を呼び、PortsOrch 側で COUNTERS_DB / FLEX_COUNTER_DB の queue/PG カウンタを追加する（detach 時は remove）。BufferOrch 自身ではなく PortsOrch がデータ書込みを行うため、本表では間接書込とする。

| 操作 (間接) | 対象 DB / テーブル | 条件 / トリガ | evidence |
|------------|------------------|--------------|----------|
| `gPortsOrch->createPortBufferQueueCounters(port, queues)` | COUNTERS_DB / `COUNTERS_QUEUE_NAME_MAP` + FLEX_COUNTER_DB queue group | profile attach 後、`queueContext.counter_needs_to_add` && (queue counter / queue watermark 有効) | `bufferorch.cpp:1138-1146` |
| `gPortsOrch->removePortBufferQueueCounters(port, queues)` | 同上 | profile detach 時に対応 | `bufferorch.cpp:1147-1152` |
| `gPortsOrch->createPortBufferPgCounters(port, pgs)` | COUNTERS_DB / `COUNTERS_PG_NAME_MAP` + FLEX_COUNTER_DB PG group | profile attach 後、`pg.counter_needs_to_add` && (PG counter / PG watermark 有効) | `bufferorch.cpp:1513-1521` |
| `gPortsOrch->removePortBufferPgCounters(port, pgs)` | 同上 | profile detach 時 | `bufferorch.cpp:1522-1525` |

VOQ スイッチ (`gMySwitchType == "voq"`) では BUFFER_QUEUE 設定とは無関係に FlexCounterOrch が常時 queue counter を追加するため、`bufferorch.cpp:1135-1137` のコメントに基づき BufferOrch 側からの create/remove はスキップされる。

---

## 3. FLEX_COUNTER_DB 書込

`flex_counter_manager.h` の自由関数 `setFlexCounterGroupParameter` / `setFlexCounterGroupStatsMode` / `startFlexCounterPolling` / `stopFlexCounterPolling` 経由で FLEX_COUNTER_DB の `FLEX_COUNTER_GROUP_TABLE` / `FLEX_COUNTER_TABLE` を更新する。

### 3.1 初期化時 (`BufferOrch` ctor → `initFlexCounterGroupTable()`)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 | evidence |
|------|------------------|-----------------|------|----------|
| `setFlexCounterGroupParameter(BUFFER_POOL_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, POLL_INTERVAL, "", BUFFER_POOL_PLUGIN_FIELD, sha)` | FLEX_COUNTER_DB / `FLEX_COUNTER_GROUP_TABLE\|BUFFER_POOL_WATERMARK_STAT_COUNTER` | fields: `POLL_INTERVAL`, plugin sha | 起動時 1 回。`watermark_bufferpool.lua` を `loadRedisScript()` した sha を group に登録 | `bufferorch.cpp:232-251` |
| `loadRedisScript(m_countersDb, bufferPoolLuaScript)` | COUNTERS_DB (Redis `SCRIPT LOAD`) | Lua script ハッシュ登録 | 同上 (副次的に COUNTERS_DB Redis インスタンス上にスクリプト常駐) | `bufferorch.cpp:239-240` |

### 3.2 SAI capability 確定時 (`generateBufferPoolWatermarkCounterIdList()` — `FlexCounterOrch` から呼ばれる)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 | evidence |
|------|------------------|-----------------|------|----------|
| `setFlexCounterGroupStatsMode(group, STATS_MODE_READ_AND_CLEAR)` | FLEX_COUNTER_DB / `FLEX_COUNTER_GROUP_TABLE\|BUFFER_POOL_WATERMARK_STAT_COUNTER` | field=`STATS_MODE` | 全 pool が watermark clear をサポートする (`noWmClrCapability == 0`) | `bufferorch.cpp:332-336` |
| `startFlexCounterPolling(gSwitchId, key, statList, BUFFER_POOL_COUNTER_ID_LIST, stats_mode)` | FLEX_COUNTER_DB / `FLEX_COUNTER_TABLE\|<group>:<sai_pool_oid>` | fields: `BUFFER_POOL_COUNTER_ID_LIST` (= 全 buffer pool watermark stat id カンマ区切り), `STATS_MODE` | `m_buffer_type_maps[APP_BUFFER_POOL_TABLE_NAME]` 内の全 pool に対して 1 回ずつ。clear 非対応 pool だけ `STATS_MODE_READ` を個別設定 | `bufferorch.cpp:340-359` |

`m_isBufferPoolWatermarkCounterIdListGenerated` フラグで 2 回目以降の呼出を抑止する (FLEX_COUNTER 更新による再エコーを避けるため)。

### 3.3 BufferPool 削除時 (`clearBufferPoolWatermarkCounterIdList()`)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 | evidence |
|------|------------------|-----------------|------|----------|
| `stopFlexCounterPolling(gSwitchId, "<group>:<sai_pool_oid>")` | FLEX_COUNTER_DB / `FLEX_COUNTER_TABLE\|<group>:<sai_pool_oid>` | キー全体を DEL | `processBufferPool()` の DEL 経路、`m_isBufferPoolWatermarkCounterIdListGenerated` が true のときのみ | `bufferorch.cpp:276-284`, `bufferorch.cpp:571` |

---

## 4. APPL_DB への自己再 publish (ResponsePublisher)

`Orch::m_publisher.publish()` 経由で APPL_STATE_DB (`APPL_DB` の応答チャネル) に成功応答を流す。SAI 反映完了を上位（buffermgrdyn の SHP 計算同期や config-validator）に通知するための「副次 publish」だが、データ DB への書込みではなくレスポンスチャネルへの書込みである。

| 操作 | 対象 | 条件 | evidence |
|------|------|------|----------|
| `m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, name, [{xoff}], SAI_STATUS_SUCCESS, force=true)` | APPL_STATE_DB ResponsePublisher | `processBufferPool()` SET 成功 かつ `xoff` 非空（SHP 有効時） | `bufferorch.cpp:551-556` |
| `m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, name, [], SAI_STATUS_SUCCESS, force=true)` | 同上 | `processBufferPool()` DEL 成功 | `bufferorch.cpp:587-589` |
| `m_publisher.publish(APP_BUFFER_PROFILE_TABLE_NAME, name, fvs, SAI_STATUS_SUCCESS, force=true)` | 同上 | `processBufferProfile()` SET 成功時 (新規 + 更新) | `bufferorch.cpp:832, 880` |

---

## 5. SAI 呼出 (ASIC_DB へ反映 — 参考)

副次 DB ではないが ASIC_DB への書込みも併記:

- `sai_buffer_api->create_buffer_pool()` / `remove_buffer_pool()` / `set_buffer_pool_attribute()`
- `sai_buffer_api->create_buffer_profile()` / `remove_buffer_profile()` / `set_buffer_profile_attribute()`
- `sai_buffer_api->clear_buffer_pool_stats()` (watermark clear capability probe)
- `sai_queue_api->set_queue_attribute(SAI_QUEUE_ATTR_BUFFER_PROFILE_ID)`
- `sai_buffer_api->set_ingress_priority_group_attribute(SAI_INGRESS_PRIORITY_GROUP_ATTR_BUFFER_PROFILE)`
- `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST / EGRESS_...)`

---

## 6. 副次書込の発火順序（典型: BUFFER_POOL 新規 SET）

1. APPL_DB から `BUFFER_POOL_TABLE|<name>` SET を consume
2. `sai_buffer_api->create_buffer_pool()` → ASIC_DB
3. `m_buffer_type_maps[APP_BUFFER_POOL_TABLE_NAME][name]` 更新 (in-memory)
4. **`m_counterNameMapUpdater->setCounterNameMap(name, oid)` → COUNTERS_DB `COUNTERS_BUFFER_POOL_NAME_MAP`**
5. (xoff 非空時) **`m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, ...)` → APPL_STATE_DB**
6. (FlexCounterOrch から後段呼出時) **`startFlexCounterPolling(...)` → FLEX_COUNTER_DB**

---

## 7. 検証コマンド (実機 dump)

```sh
# STATE_DB 全 BUFFER_MAX_PARAM 行
redis-cli -n 6 hgetall 'BUFFER_MAX_PARAM_TABLE|global'

# COUNTERS_DB buffer pool name map
redis-cli -n 2 hgetall COUNTERS_BUFFER_POOL_NAME_MAP

# FLEX_COUNTER_DB buffer pool watermark group / table エントリ
redis-cli -n 5 keys 'FLEX_COUNTER_GROUP_TABLE|BUFFER_POOL_WATERMARK*'
redis-cli -n 5 keys 'FLEX_COUNTER_TABLE|BUFFER_POOL_WATERMARK*'
```

---

## 8. 証跡カバレッジ

grep `bufferorch.cpp` 内 hit:

- `STATE_BUFFER_MAXIMUM_VALUE_TABLE` × 2 (ctor / member init / SET 1)
- `m_counterNameMapUpdater` × 3 (ctor / setCounterNameMap / delCounterNameMap)
- `setFlexCounterGroup*` × 2 (init / statsMode)
- `startFlexCounterPolling` × 1 / `stopFlexCounterPolling` × 1
- `m_publisher.publish` × 4
- `gPortsOrch->createPortBufferQueueCounters` / `removePortBufferQueueCounters` × 各 1
- `gPortsOrch->createPortBufferPgCounters` / `removePortBufferPgCounters` × 各 1

全 hit を本書のマトリクス各行で網羅。
