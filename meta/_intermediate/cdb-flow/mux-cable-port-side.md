# mux-cable-port Phase F (side-effects) 調査証跡

## 調査対象

- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-swss-common/common/schema.h`
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`

## orchagent 側副次書込

### STATE_DB MUX_CABLE_TABLE: neighbor_mode

```
muxorch.cpp:2198-2199
  std::unique_ptr<DBConnector> state_db = std::make_unique<DBConnector>("STATE_DB", 0);
  state_mux_cable_table_ = std::make_unique<Table>(state_db.get(), STATE_MUX_CABLE_TABLE_NAME);

muxorch.cpp:2283-2285
  state_mux_cable_table_->hset(port_name, "neighbor_mode", neighbor_mode_str);
  // neighbor_mode_str は "host-route" / "prefix-route"
  // handleMuxCfg() 内の MuxCable 新規作成時のみ呼ばれる
```

### APPL_DB HW_MUX_CABLE_TABLE: state

```
muxorch.cpp:2505
  mux_table_ = unique_ptr<Table>(new Table(db, APP_HW_MUX_CABLE_TABLE_NAME));
  // APP_HW_MUX_CABLE_TABLE_NAME = "HW_MUX_CABLE_TABLE" (schema.h:141)

muxorch.cpp:2513
  mux_table_->set(portName, tuples);
  // MuxCableOrch::updateMuxState() 内で state = "active" / "standby" を書込
```

### STATE_DB MUX_METRICS_TABLE: タイムスタンプ

```
muxorch.cpp:2503
  mux_metric_table_(sdb, STATE_MUX_METRICS_TABLE_NAME)
  // STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE" (schema.h:460)

muxorch.cpp:2544
  mux_metric_table_.hset(portName, msg, time);
  // msg = "orch_switch_active_start", "orch_switch_active_end", etc.
```

### STATE_DB MUX_CABLE_TABLE: state (MuxStateOrch)

```
muxorch.cpp:2633
  mux_state_table_(db, STATE_MUX_CABLE_TABLE_NAME)
  // STATE_MUX_CABLE_TABLE_NAME = "MUX_CABLE_TABLE" (schema.h:457)

muxorch.cpp:2640
  mux_state_table_.hset(portName, "state", muxState);
  // MuxStateOrch::updateMuxState() - APPL_DB HW_MUX_CABLE_TABLE 受信後
```

## linkmgrd 側副次書込

`DbInterface.cpp:317-346` のコンストラクタで初期化:
```cpp
// APPL_DB
mMuxPortPtr = std::make_shared<swss::ProducerStateTable>(mAppDbPtr.get(), APP_MUX_CABLE_TABLE_NAME);
mMuxPeerPortPtr = std::make_shared<swss::ProducerStateTable>(mAppDbPtr.get(), APP_PEER_HW_FORWARDING_STATE_TABLE_NAME);
mMuxPortCmdPtr = std::make_shared<swss::ProducerStateTable>(mAppDbPtr.get(), APP_MUX_CABLE_COMMAND_TABLE_NAME);
mFwdStateCmdPtr = std::make_shared<swss::ProducerStateTable>(mAppDbPtr.get(), APP_FORWARDING_STATE_COMMAND_TABLE_NAME);

// STATE_DB
mMuxLinkmgrTablePtr = std::make_shared<swss::Table>(mStateDbPtr.get(), STATE_MUX_LINKMGR_TABLE_NAME);
mMuxMetricsTablePtr = std::make_shared<swss::Table>(mStateDbPtr.get(), STATE_MUX_METRICS_TABLE_NAME);
mMuxSwitchCauseTablePtr = std::make_shared<swss::Table>(mStateDbPtr.get(), STATE_MUX_SWITCH_CAUSE_TABLE_NAME);
mMuxStateTablePtr = std::make_shared<swss::Table>(mStateDbPtr.get(), STATE_MUX_CABLE_TABLE_NAME);
```

## ycabled 側副次書込

```python
# y_cable_helper.py:741-744
hw_mux_cable_tbl[asic_id] = swsscommon.Table(
    state_db[asic_id], "HW_MUX_CABLE_TABLE")
hw_mux_cable_tbl_peer[asic_id] = swsscommon.Table(
    state_db[asic_id], "HW_MUX_CABLE_TABLE_PEER")

# y_cable_helper.py:607-608 (put_init_values_for_grpc_states)
hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
hw_mux_cable_tbl_peer[asic_index].set(port, fvs_updated)

# y_cable_helper.py:627-631 (update_grpc_states)
hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
hw_mux_cable_tbl_peer[asic_index].set(port, fvs_updated)

# y_cable_helper.py:1554
mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)
# MUX_CABLE_INFO_TABLE = "MUX_CABLE_INFO" (y_cable_helper.py:120)
```

## スキーマ定数 (schema.h)

| マクロ | 値 | 行 |
|--------|----|----|
| `APP_HW_MUX_CABLE_TABLE_NAME` | `"HW_MUX_CABLE_TABLE"` | 141 |
| `STATE_MUX_CABLE_TABLE_NAME` | `"MUX_CABLE_TABLE"` | 457 |
| `STATE_MUX_METRICS_TABLE_NAME` | `"MUX_METRICS_TABLE"` | 460 |
