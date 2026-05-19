# state-db-port Phase G 調査メモ

調査日: 2026-05-19  
対象ページ: docs/reference/config-db/state-db-port.md

## 書き込み側

`STATE_DB PORT_TABLE` は `swss::Table` 直接操作で書き込まれる（ProducerStateTable は不使用）。

- `portsyncd/linksync.cpp:205` — `m_statePortTable.set(key, vector)`
- `portsyncd/linksync.cpp:184` — `m_statePortTable.del(key)`
- `orchagent/portsorch.cpp:3172`, `3320`, `9857`, `9870` — `m_portStateTable.set()` / `.hset()`

## 読み取り側の購読方式

### intfmgrd (SubscriberStateTable)

`intfmgr.cpp:45-47`:
```cpp
auto subscriberStateTable = new swss::SubscriberStateTable(stateDb,
    STATE_PORT_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 100);
auto stateConsumer = new Consumer(subscriberStateTable, this, STATE_PORT_TABLE_NAME);
```

Redis keyspace 通知 (`__keyevent@6__:hset` 等) を受信し `doPortTableTask()` へ dispatch。

### teammgrd (TableConnector)

`teammgrd.cpp:57`:
```cpp
TableConnector state_port_table(&state_db, STATE_PORT_TABLE_NAME);
```

### buffermgrd (TableConnector)

`buffermgrd.cpp:185`:
```cpp
TableConnector(&stateDb, STATE_PORT_TABLE_NAME)
```

`m_bufferTableHandlerMap` 経由で `handlePortStateTable()` を呼ぶ (`buffermgrdyn.cpp:451`)。

## Select タイムアウト

- intfmgrd: `SELECT_TIMEOUT = 1000 ms` (`intfmgrd.cpp:17`)
