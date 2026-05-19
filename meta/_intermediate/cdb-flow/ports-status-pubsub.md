# ports-status pubsub 調査ノート (Phase G)

## STATE_DB PORT_TABLE の購読デーモン一覧

STATE_DB `PORT_TABLE` は以下の 5 デーモンが `TableConnector` または `SubscriberStateTable` 経由で購読する。

### portmgrd
- `portmgr.cpp:19` — `m_statePortTable(stateDb, STATE_PORT_TABLE_NAME)` で Table を保持
- `portmgrd.cpp:16` — `SELECT_TIMEOUT = 1000` ms
- `portmgrd.cpp:50` — `s.select(&sel, SELECT_TIMEOUT)` でメインループ
- 購読方式: `Orch::getSelectables()` 経由。CONFIG_DB `PORT` と STATE_DB `PORT_TABLE` の両方を待ち受け

### teammgrd
- `teammgrd.cpp:57` — `TableConnector state_port_table(&state_db, STATE_PORT_TABLE_NAME)`
- `teammgrd.cpp:13` — `SELECT_TIMEOUT = 1000` ms
- 購読方式: `TableConnector` → `Executor` として `s.addSelectables()` 登録

### intfmgrd
- `intfmgr.cpp:45-48` — `SubscriberStateTable` を直接生成し `Consumer` として `Orch::addExecutor()` に登録
  - `DEFAULT_POP_BATCH_SIZE`, priority = 100
- `intfmgrd.cpp:17` — `SELECT_TIMEOUT = 1000` ms
- 購読方式: `SubscriberStateTable` → Redis keyspace notification PSUBSCRIBE

### sflowmgrd
- `sflowmgrd.cpp:32` — `TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME)`
- `sflowmgrd.cpp:16` — `SELECT_TIMEOUT = 1000` ms
- 注記: 起動時に `readPortConfig()` を手動呼び出し（CONFIG_DB と STATE_DB の通知順序が保証されないため）

### buffermgrd (dynamic)
- `buffermgrd.cpp:185` — `TableConnector(&stateDb, STATE_PORT_TABLE_NAME)` をテーブルリストに追加
- `buffermgrdyn.cpp:451` — `m_bufferTableHandlerMap` に `STATE_PORT_TABLE_NAME → handlePortStateTable` を登録
- `buffermgrd.cpp:22` — `SELECT_TIMEOUT = 1000` ms

## 書き込み側の通信方式

- `portsyncd/linksync.cpp` — `m_statePortTable` は `Table` 型（直接 hset / del を呼ぶ）
- `PortsOrch` — `m_portStateTable` は `Table` 型（直接 hset を呼ぶ）
- いずれも `ProducerStateTable` ではなく `Table`（= Redis HSET 直書き）

`Table` 型の書き込みは Redis keyspace notification を経由して購読側に到達する。`SubscriberStateTable` を使う intfmgrd はこの notification を直接受信する。`TableConnector` ベースの他デーモンは内部で `SubscriberStateTable` または `NotificationConsumer` 相当として機能する。

## SELECT_TIMEOUT まとめ

| デーモン | SELECT_TIMEOUT |
|---------|---------------|
| portmgrd | 1000 ms |
| teammgrd | 1000 ms |
| intfmgrd | 1000 ms |
| sflowmgrd | 1000 ms |
| buffermgrd | 1000 ms |

全デーモンで `SELECT_TIMEOUT = 1000` ms（コード定数 `#define SELECT_TIMEOUT 1000`）。
