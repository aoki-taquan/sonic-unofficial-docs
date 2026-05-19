# switch-trimming — Phase G 通信メカニズム 調査ノート

## 調査対象

- `sonic-swss/orchagent/orchdaemon.cpp` L196-214
- `sonic-swss/orchagent/switchorch.cpp`
- `sonic-swss/orchagent/orch.cpp` L1186-1196

## 購読方式

`SWITCH_TRIMMING` は CONFIG_DB テーブルであり、`SwitchOrch` は `SubscriberStateTable` (keyspace 通知) で購読する。

### orchdaemon.cpp による登録

```cpp
// orchdaemon.cpp L200
TableConnector conf_switch_trim(m_configDb, CFG_SWITCH_TRIMMING_TABLE_NAME);

vector<TableConnector> switch_tables = {
    conf_switch_hash,
    conf_switch_trim,          // ← SWITCH_TRIMMING
    conf_switch_fast_linkup,
    conf_asic_sensors,
    conf_suppress_asic_sdk_health_categories,
    app_switch_table
};

gSwitchOrch = new SwitchOrch(m_applDb, switch_tables, stateDbSwitchTable);
```

### orch.cpp での Consumer 選択

```cpp
// orch.cpp L1186-1196
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || ...)
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ...), this, tableName));
else
    addExecutor(new Consumer(new ConsumerStateTable(db, tableName, ...), this, tableName));
```

CONFIG_DB (dbId=4) のため `SubscriberStateTable` が選択される。これは `PSUBSCRIBE __keyspace@4__:SWITCH_TRIMMING|*` を使用。

## 他の購読者

- `orchagent` (SwitchOrch) のみ
- syncd / STATE_DB publisher / mgrd 等は SWITCH_TRIMMING を購読しない

## ハンドラ

`switchorch.cpp:1511` で `tableName == CFG_SWITCH_TRIMMING_TABLE_NAME` を判定し `doCfgSwitchTrimmingTableTask()` を呼び出す。

## 下流通知

- ProducerStateTable / NotificationProducer は使用しない
- APPL_DB への転送なし
- STATE_DB 書込みは起動時 capability のみ（CONFIG_DB SET 操作とは無関係）
