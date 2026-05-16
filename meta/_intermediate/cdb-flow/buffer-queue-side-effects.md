# buffer-queue — Phase F 副次 DB 書込 調査メモ

## 調査対象ソース

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 主フロー（副次書込の起点）

`BUFFER_QUEUE` の SET/DEL イベントは以下の経路で副次書き込みを発生させる。

```
CONFIG_DB BUFFER_QUEUE
  → BufferMgrDynamic::handleBufferQueueTable()
  → APPL_DB APP_BUFFER_QUEUE_TABLE
  → BufferOrch::processQueue() / processQueuePost()
      → gPortsOrch->createPortBufferQueueCounters() [SET, 非zero profile]
          → addPortBufferQueueCounters()
              → COUNTERS_DB: QUEUE_NAME_MAP, QUEUE_PORT_MAP, QUEUE_INDEX_MAP, QUEUE_TYPE_MAP
              → FLEX_COUNTER_DB: QUEUE_STAT_COUNTER, QUEUE_WATERMARK_STAT_COUNTER, WRED_ECN_QUEUE_STAT_COUNTER
      → gPortsOrch->removePortBufferQueueCounters() [DEL, 非zero profile]
          → deletePortBufferQueueCounters()
              → COUNTERS_DB: (上記 4 マップから削除)
              → FLEX_COUNTER_DB: (上記 3 グループから削除)
```

## APPL_DB — APP_BUFFER_QUEUE_TABLE への書込

`BufferMgrDynamic::updateBufferObjectToDb()` が `m_applBufferObjectTables[BUFFER_QUEUE]`（`ProducerStateTable`）経由で書き込む。

| 操作 | 対象テーブル | フィールド | 条件 |
|------|------------|----------|------|
| `table.set(key, {profile})` | APPL_DB / `APP_BUFFER_QUEUE_TABLE` | `profile` | SET 操作かつ `m_bufferPoolReady == true` |
| `table.del(key)` | APPL_DB / `APP_BUFFER_QUEUE_TABLE` | — | DEL 操作 |

`m_bufferPoolReady == false` の場合、書き込みは保留され `m_bufferObjectsPending = true` をセット（`buffermgrdyn.cpp:933-936`）。

## COUNTERS_DB 副次書込

### 書込テーブル

| テーブル名定数 | 実テーブル名 | 操作 | ソース行 |
|---|---|---|---|
| `COUNTERS_QUEUE_NAME_MAP` | `COUNTERS_QUEUE_NAME_MAP` | SET/DEL | `portsorch.cpp:778, 8749, 8789` |
| `COUNTERS_QUEUE_PORT_MAP` | `COUNTERS_QUEUE_PORT_MAP` | SET/DEL | `portsorch.cpp:780, 8750, 8790` |
| `COUNTERS_QUEUE_INDEX_MAP` | `COUNTERS_QUEUE_INDEX_MAP` | SET/DEL | `portsorch.cpp:781, 8751, 8796` |
| `COUNTERS_QUEUE_TYPE_MAP` | `COUNTERS_QUEUE_TYPE_MAP` | SET/DEL | `portsorch.cpp:782, 8752, 8797` |

### SET 時の書込内容

`COUNTERS_QUEUE_NAME_MAP`: field=`"<port_alias>:<queueIndex>"`, value=`sai_serialize_object_id(queue_oid)`

`COUNTERS_QUEUE_PORT_MAP`: field=`sai_serialize_object_id(queue_oid)`, value=`sai_serialize_object_id(port_oid)`

`COUNTERS_QUEUE_INDEX_MAP`: field=`sai_serialize_object_id(queue_oid)`, value=`to_string(queueRealIndex)`

`COUNTERS_QUEUE_TYPE_MAP`: field=`sai_serialize_object_id(queue_oid)`, value=`sai_queue_type_string_map[queueType]`

## FLEX_COUNTER_DB 副次書込

### 書込グループ

| グループ名定数 | 実グループ名 | 読み取りモード | poll 間隔 | ソース行 |
|---|---|---|---|---|
| `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `QUEUE_STAT_COUNTER` | READ | 10000ms | `portsorch.h:34, portsorch.cpp:734` |
| `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `QUEUE_WATERMARK_STAT_COUNTER` | READ_AND_CLEAR | 60000ms | `portsorch.h:35, portsorch.cpp:735` |
| `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `WRED_ECN_QUEUE_STAT_COUNTER` | READ | 10000ms | `portsorch.h:42, portsorch.cpp:738` |

### トリガー条件

```cpp
// bufferorch.cpp:1139-1158 (processQueuePost)
if (flexCounterOrch->isCreateOnlyConfigDbBuffers()) {
    if (!counter_was_added && counter_needs_to_add &&
        (flexCounterOrch->getQueueCountersState() || flexCounterOrch->getQueueWatermarkCountersState())) {
        gPortsOrch->createPortBufferQueueCounters(port, queues);  // ADD
    } else if (counter_was_added && !counter_needs_to_add &&
               (flexCounterOrch->getQueueCountersState() || flexCounterOrch->getQueueWatermarkCountersState())) {
        gPortsOrch->removePortBufferQueueCounters(port, queues);  // REMOVE
    }
}
```

`counter_needs_to_add` は SET 操作時に `true`（zero profile 以外）。`bufferorch.cpp:988`

`counter_was_added` は旧プロファイルが存在し `_zero_` を含まない場合 `true`。`bufferorch.cpp:1017`

## VOQ 例外

`gMySwitchType == "voq"` の場合、副次 DB 書き込み全体がスキップされる。

```cpp
// bufferorch.cpp:1134-1136
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE
// configuration. So Port Queue counter needs to be updated only for non VOQ switch.
else if (gMySwitchType != "voq")
{
    ...createPortBufferQueueCounters / removePortBufferQueueCounters...
}
```

## zero profile 例外

プロファイル名に `_zero_` を含む場合、`counter_needs_to_add = false` となりカウンタ追加は行われない（`bufferorch.cpp:988, 1017`）。既存カウンタがあれば削除する。

## STATE_DB

`buffermgrdyn.cpp` は `BUFFER_MAX_PARAM` テーブル（STATE_DB）を参照するが、BUFFER_QUEUE 処理で STATE_DB への書き込みは確認されなかった。STATE_DB への書き込みは `PortsOrch` が port 初期化時に行う別フロー。

## APPL_STATE_DB / ResponsePublisher

`buffermgrdyn.cpp` の `m_applStateBufferPoolTable` / `m_applStateBufferProfileTable` は BUFFER_POOL / BUFFER_PROFILE 向けの APPL_STATE_DB テーブル。`bufferorch.cpp` の `m_publisher.publish()` 呼び出しも BUFFER_POOL / BUFFER_PROFILE テーブル向け。BUFFER_QUEUE の SET/DEL 処理で APPL_STATE_DB への書き込みは確認されなかった。

## まとめ

BUFFER_QUEUE の副次 DB 書込:

1. **APPL_DB** `APP_BUFFER_QUEUE_TABLE` — `buffermgrd` が profile を転送（pool 準備完了後）
2. **COUNTERS_DB** 4 マップ — queue OID ↔ 名前/ポート/インデックス/タイプの対応表（非 VOQ かつ `isCreateOnlyConfigDbBuffers()` が true の場合のみ）
3. **FLEX_COUNTER_DB** 最大 3 グループ — queue stat / watermark / WRED カウンタ登録（FlexCounterOrch の有効化状態に依存）
4. **STATE_DB** — 書き込みなし
5. **APPL_STATE_DB** — 書き込みなし（ResponsePublisher は BUFFER_POOL/PROFILE 向けのみ）
