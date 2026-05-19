# mux-cable-state Phase G pubsub 調査証跡

## 調査対象

- `sonic-net/sonic-swss` `orchagent/muxorch.cpp`, `orchagent/orchdaemon.cpp`
- `sonic-net/sonic-linkmgrd` `src/DbInterface.cpp`
- `sonic-net/sonic-platform-daemons` `sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`

## 主要発見事項

### MUX_CABLE_TABLE (STATE_DB) の書き込み経路

- `MuxOrch` は `orchdaemon.cpp:2199` で `state_mux_cable_table_` を `swss::Table(state_db.get(), STATE_MUX_CABLE_TABLE_NAME)` として構築
- `MuxStateOrch::updateMuxState()` が `mux_state_table_.hset(portName, "state", muxState)` で書き込む (`muxorch.cpp:2638-2641`)
- `MuxCableOrch::updateMuxState()` は APPL_DB `HW_MUX_CABLE_TABLE` に書き込む (副次書き込み)

### HW_MUX_CABLE_TABLE (STATE_DB) の書き込み経路

- ycabled が `swsscommon.Table(state_db[asic_id], STATE_HW_MUX_CABLE_TABLE_NAME)` を直接操作 (`y_cable_helper.py:740-742`)
- `put_init_values_for_grpc_states()` / `update_table_mux_status_for_statedb_port_tbl()` で `FieldValuePairs` を書き込む

### linkmgrd の購読経路

- `handleSwssNotification()` がバックグラウンドスレッドで `swss::Select` を使い多重待機 (`DbInterface.cpp:1813-1912`)
- `stateDbPortTable = SubscriberStateTable(stateDbPtr.get(), STATE_MUX_CABLE_TABLE_NAME)` を登録 (`DbInterface.cpp:1833`)
- イベント到着時に `handleMuxStateNotifiction()` → `processMuxStateNotifiction()` → `addOrUpdateMuxPortMuxState()` を呼ぶ

### orchagent MuxStateOrch の購読経路

- `orchdaemon.cpp:477`: `MuxStateOrch *mux_st_orch = new MuxStateOrch(m_stateDb, STATE_HW_MUX_CABLE_TABLE_NAME)`
- `Orch2` が STATE_DB `HW_MUX_CABLE_TABLE` を ConsumerStateTable 相当で購読
- `MuxStateOrch::addOperation()` が hw_state と mux_state を比較して `MUX_CABLE_TABLE.state` を更新 (`muxorch.cpp:2643-2691`)
