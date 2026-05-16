# FLEX_COUNTER_TABLE — Phase G 通信メカニズム 証跡

## 調査ソース

- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/saihelper.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`

## CONFIG_DB Consumer 登録

`FlexCounterOrch::FlexCounterOrch(DBConnector *db, vector<string> &tableNames)` が `Orch(db, tableNames)` 基底を呼び出す。

`orchdaemon.cpp:620` で渡される tableNames:
- `CFG_FLEX_COUNTER_TABLE_NAME` — `FLEX_COUNTER_TABLE`
- `CFG_DEVICE_METADATA_TABLE_NAME` — `DEVICE_METADATA`

`Orch::addConsumer()` (orch.cpp:1188) の DB 種別分岐:

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
{
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
        TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
}
```

CONFIG_DB (dbId=4) のため `SubscriberStateTable` が選ばれ、Redis keyspace 通知 `__keyspace@4__:FLEX_COUNTER_TABLE:*` を PSUBSCRIBE する。

## FLEX_COUNTER_DB Writer

SAI 呼び出しの 2 系統:

### 新方式 (gTraditionalFlexCounter=false)

`saihelper.cpp:918` `setFlexCounterGroupOperation()`:

```cpp
sai_attribute_t attr;
sai_redis_flex_counter_group_parameter_t flex_counter_group_param;
attr.id = SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP;
attr.value.ptr = &flex_counter_group_param;
initSaiRedisCounterParameterFromString(flex_counter_group_param.counter_group_name, group);
initSaiRedisCounterParameterFromString(flex_counter_group_param.operation, operation);
notifySyncdCounterOperation(is_gearbox, attr);
```

`saihelper.cpp:941` `setFlexCounterGroupPollInterval()` も同様に `sai_redis_flex_counter_group_parameter_t` 経由。

### 旧方式 (gTraditionalFlexCounter=true)

`saihelper.cpp:868` `operateFlexCounterGroupDatabase()`:

```cpp
auto &flexCounterGroupTable = is_gearbox ? gGearBoxFlexCounterGroupTable : gFlexCounterGroupTable;
// gFlexCounterGroupTable = ProducerTable(FLEX_COUNTER_DB, FLEX_COUNTER_GROUP_TABLE)
```

`saihelper.cpp:323` で初期化:

```cpp
gFlexCounterDb = std::make_unique<DBConnector>("FLEX_COUNTER_DB", 0);
gFlexCounterTable = std::make_unique<ProducerTable>(gFlexCounterDb.get(), FLEX_COUNTER_TABLE);
gFlexCounterGroupTable = std::make_unique<ProducerTable>(gFlexCounterDb.get(), FLEX_COUNTER_GROUP_TABLE);
```

## SAI counter API 呼び出し

| API / 属性 | 用途 |
|---|---|
| `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` | flex counter グループのパラメータ設定 (新方式) |
| `sai_redis_flex_counter_group_parameter_t.operation` | `enable` / `disable` |
| `sai_redis_flex_counter_group_parameter_t.poll_interval` | ポーリング間隔 (ms) |
| `sai_redis_flex_counter_group_parameter_t.bulk_chunk_size` | bulk API チャンクサイズ |
| `FLEX_COUNTER_GROUP_TABLE` in FLEX_COUNTER_DB | 旧方式: syncd が ConsumerStateTable 経由で読む |

## メッセージフロー

```
CONFIG_DB FLEX_COUNTER_TABLE|PORT (FLEX_COUNTER_STATUS=enable)
  └─ FlexCounterOrch::doTask(Consumer&)
       ├─ ガード: m_delayTimerExpired, allPortsReady() チェック
       ├─ gPortsOrch->generatePortCounterMap()     (COUNTER_ID_LIST 生成)
       ├─ setFlexCounterGroupOperation(PORT_STAT_COUNTER_FLEX_COUNTER_GROUP, "enable")
       │    └─ [新方式] SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP → notifySyncdCounterOperation()
       │    └─ [旧方式] FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE|PORT → syncd
       └─ gPortsOrch->flushCounters()

CONFIG_DB FLEX_COUNTER_TABLE|PORT (POLL_INTERVAL=1000)
  └─ FlexCounterOrch::doTask(Consumer&)
       └─ setFlexCounterGroupPollInterval(PORT_STAT_COUNTER_FLEX_COUNTER_GROUP, "1000")
            └─ [新方式] SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP → notifySyncdCounterOperation()
            └─ [旧方式] FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE|PORT → syncd
```
