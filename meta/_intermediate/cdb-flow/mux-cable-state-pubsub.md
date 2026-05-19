# mux-cable-state — pubsub 調査メモ (Phase G)

## 調査対象

STATE_DB テーブル:
- `MUX_CABLE_TABLE` (DB 6) — orchagent `MuxStateOrch::updateMuxState()` が書き込み
- `HW_MUX_CABLE_TABLE` (STATE_DB 6) — orchagent が書き込む STATE_DB 側は mux_state_table_ 経由

## 書き込み側 (Publisher)

### MUX_CABLE_TABLE (STATE_DB)

書き込みは `swss::Table::hset()` (非 ProducerStateTable) 経由:

```cpp
// muxorch.cpp:2638-2641
void MuxStateOrch::updateMuxState(string portName, string muxState)
{
    mux_state_table_.hset(portName, "state", muxState);
}
```

`mux_state_table_` は `MuxStateOrch` コンストラクタで `swss::Table(db, STATE_MUX_CABLE_TABLE_NAME)` として初期化される (muxorch.cpp:2633)。`hset()` は直接 HSET コマンドを実行し、swsscommon の `__keyspace@6__:MUX_CABLE_TABLE|<ifname>` keyspace 通知を Redis が発行する。ProducerStateTable の `_CHANNEL@` PUBLISH は行わない。

### HW_MUX_CABLE_TABLE (STATE_DB 書き込み)

ycabled が `swsscommon.Table` を通じて直接 hset する (y_cable_helper.py:621-626)。同様に `__keyspace@6__:HW_MUX_CABLE_TABLE|<ifname>` keyspace 通知が発行される。

## 購読側 (Subscriber)

### 1. linkmgrd — STATE_DB MUX_CABLE_TABLE を SubscriberStateTable で購読

```cpp
// DbInterface.cpp:1833
swss::SubscriberStateTable stateDbPortTable(stateDbPtr.get(), STATE_MUX_CABLE_TABLE_NAME);
// ... DbInterface.cpp:1866
swssSelect.addSelectable(&stateDbPortTable);
```

`SubscriberStateTable` は内部で `__keyspace@6__:MUX_CABLE_TABLE|*` を PSUBSCRIBE する。

**dispatch ループ** (DbInterface.cpp:1873-1912):
- select timeout: `DEFAULT_TIMEOUT_MSEC = 1000` ms (DbInterface.cpp:48)
- イベント受信 → `handleMuxStateNotifiction(stateDbPortTable)` → `processMuxStateNotifiction(entries)` → `mMuxManagerPtr->addOrUpdateMuxPortMuxState(port, v)` → `muxPortPtr->handleMuxState(muxState)`

### 2. orchagent — STATE_DB HW_MUX_CABLE_TABLE を Orch2 + SubscriberStateTable で購読

```cpp
// orchdaemon.cpp:477
MuxStateOrch *mux_st_orch = new MuxStateOrch(m_stateDb, STATE_HW_MUX_CABLE_TABLE_NAME);
```

`MuxStateOrch` は `Orch2(db, tableName, request_)` を継承。`orch.cpp:1188-1190` の `addConsumer()` ロジックにより STATE_DB (dbId=6) は `SubscriberStateTable` 経路が選択される:

```cpp
// orch.cpp:1188-1190
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
```

`HW_MUX_CABLE_TABLE` 変化 → `MuxStateOrch::addOperation()` → `MUX_CABLE_TABLE.state` 更新。
orchdaemon select timeout: `SELECT_TIMEOUT = 1000` ms (orchdaemon.cpp:23,959)。

### 3. show mux status (CLI) — poll ベース（非購読）

`show/muxcable.py:724,747` で `sonic-db-cli STATE_DB hgetall 'MUX_CABLE_TABLE|*'` 相当の一回読みを実行する。常時購読ではない。

## MUX_LINKMGR_TABLE 購読なし

`MUX_LINKMGR_TABLE` (STATE_DB) は別テーブルで `linkmgrd` が読み書きするが、外部コンポーネントの keyspace 購読は確認されていない。

## keyspace notification の前提

`SubscriberStateTable` 購読が機能するには Redis keyspace notification が有効 (`notify-keyspace-events` に `K` + `g`/`s`/`h` 等) である必要がある。SONiC では `sonic-db-cli CONFIG_DB CONFIG redis.conf` 経由でデフォルト有効。
