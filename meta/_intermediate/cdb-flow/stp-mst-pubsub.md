# STP_MST / STP_MST_INST / STP_MST_PORT — Phase G pub/sub 調査メモ

## 消費プロセス

`stpmgrd` (`sonic-swss/cfgmgr/stpmgrd.cpp`) が `StpMgr` を起動する。
`StpMgr` は `Orch(tables)` を継承し、`Orch::addConsumer()` 経由で各テーブルを購読する。

## addConsumer の分岐ロジック

`sonic-swss/orchagent/orch.cpp:1186-1194`:

```cpp
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

CONFIG_DB (dbId=4) → `SubscriberStateTable` (keyspace notification PSUBSCRIBE)

## TableConnector 一覧 (stpmgrd.cpp:47-65)

```cpp
TableConnector conf_mst_global_table(&conf_db, "STP_MST");
TableConnector conf_mst_inst_table(&conf_db, "STP_MST_INST");
TableConnector conf_mst_inst_port_table(&conf_db, "STP_MST_PORT");
```

すべて `conf_db` (CONFIG_DB, dbId=4)。

## 購読パラメータ

| パラメータ | 値 |
|---|---|
| 購読クラス | `SubscriberStateTable` |
| POP_BATCH_SIZE | `DEFAULT_POP_BATCH_SIZE` = 128 (`sonic-swss-common/common/table.h:164`) |
| 優先度 | 0 (`TableConnector` 第2引数省略 = デフォルト 0) |
| keyspace パターン (STP_MST) | `__keyspace@4__:STP_MST\|*` |
| keyspace パターン (STP_MST_INST) | `__keyspace@4__:STP_MST_INST\|*` |
| keyspace パターン (STP_MST_PORT) | `__keyspace@4__:STP_MST_PORT\|*` |

## 主ループ (stpmgrd.cpp:92-115)

```cpp
#define SELECT_TIMEOUT 1000   // 1秒

Select s;
for (Orch *o: cfgOrchList)
    s.addSelectables(o->getSelectables());

while (true) {
    Selectable *sel;
    int ret = s.select(&sel, SELECT_TIMEOUT);
    if (ret == Select::ERROR) { ... break; }
    if (ret == Select::TIMEOUT) { continue; }
    stpmgr.execute(((Executor *)sel)->getName());
}
```

タイムアウト 1000 ms で polling。ペイロード受信時は `StpMgr::doTask(Consumer&)` が `consumer.getTableName()` で分岐。

## ディスパッチ経路

`doTask(Consumer&)` (stpmgr.cpp:51-79):
- `"STP_MST"` → `doStpMstGlobalTask(consumer)`
- `"STP_MST_INST"` → `doStpMstInstTask(consumer)`
- `"STP_MST_PORT"` → `doStpMstInstPortTask(consumer)`

## 参照コード

- `stpmgrd.cpp`: `sonic-swss` ref `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `stpmgr.cpp`: 同上
- `orch.cpp:1186`: `sonic-swss` 同上
- `table.h:164`: `sonic-swss-common` ref 不明（DEFAULT_POP_BATCH_SIZE = 128）
