# scheduler-orch Phase G — Redis 通知メカニズム 調査メモ

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp` (handleSchedulerTable / doTask)
- `sonic-swss/orchagent/orchdaemon.cpp` (OrchDaemon::orchMain, addConsumer)
- `sonic-swss/orchagent/orch.cpp` (Orch::addConsumer, Consumer::execute)
- `sonic-swss-common/common/subscriberstatetable.cpp` (SubscriberStateTable)

## 購読方式

QosOrch は `Orch::addConsumer()` から `SubscriberStateTable` を使用して CONFIG_DB (DB 4) の SCHEDULER テーブルを購読する。

```cpp
// orch.cpp:1186-1190
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || ...)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

CONFIG_DB (DB 4) なので `SubscriberStateTable` が選択される。

## SubscriberStateTable の PSUBSCRIBE

```cpp
// subscriberstatetable.cpp:17-24
SubscriberStateTable::SubscriberStateTable(DBConnector *db, const string &tableName, ...)
{
    m_keyspace = "__keyspace@";
    m_keyspace += to_string(db->getDbId()) + "__:" + tableName + m_table.getTableNameSeparator() + "*";
    psubscribe(m_db, m_keyspace);
    // m_keyspace = "__keyspace@4__:SCHEDULER|*"
}
```

CONFIG_DB (DB 4) の SCHEDULER テーブルに対するパターン:
```
PSUBSCRIBE __keyspace@4__:SCHEDULER|*
```

## orchdaemon メインループ

```cpp
// orchdaemon.cpp:959
ret = m_select->select(&s, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000ms
```

`swss::Select` は Linux epoll を使用。Redis Keyspace Notification 到着 → epoll_wait() wakeup → Consumer::execute() → QosOrch::doTask() → handleSchedulerTable() の順で処理される。

## allPortsReady ガード

```cpp
// qosorch.cpp:2258-2261
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

PortsOrch 初期化前は SCHEDULER イベントが到着しても `m_toSync` に蓄積され処理されない。

## 調査日

2026-05-19
