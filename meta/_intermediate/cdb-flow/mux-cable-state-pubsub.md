# mux-cable-state pubsub 調査証跡 (Phase G)

## 調査対象ファイル

- `sonic-linkmgrd/src/DbInterface.cpp` — handleSwssNotification, handleMuxStateNotifiction, processMuxStateNotifiction, handlePeerMuxStateNotification
- `sonic-swss/orchagent/muxorch.cpp` — MuxStateOrch constructor, addOperation
- `sonic-swss/orchagent/orchdaemon.cpp` — MuxStateOrch 登録
- `sonic-utilities/show/muxcable.py` — hgetall ポーリング

## 主要な購読関係

### linkmgrd (STATE_DB MUX_CABLE_TABLE)

DbInterface.cpp:1833:
```cpp
swss::SubscriberStateTable stateDbPortTable(stateDbPtr.get(), STATE_MUX_CABLE_TABLE_NAME);
```

DbInterface.cpp:1861:
```cpp
swssSelect.addSelectable(&stateDbPortTable);
```

DbInterface.cpp:1900:
```cpp
} else if (selectable == static_cast<swss::Selectable *> (&stateDbPortTable)) {
    handleMuxStateNotifiction(stateDbPortTable);
```

DbInterface.cpp:1479-1507 `processMuxStateNotifiction`:
```cpp
mMuxManagerPtr->addOrUpdateMuxPortMuxState(port, v);
```

### linkmgrd (STATE_DB HW_MUX_CABLE_TABLE_PEER)

DbInterface.cpp:1839:
```cpp
swss::SubscriberStateTable stateDbPeerMuxTable(stateDbPtr.get(), STATE_PEER_HW_FORWARDING_STATE_TABLE_NAME);
```

### MuxStateOrch (STATE_DB HW_MUX_CABLE_TABLE)

orchdaemon.cpp:477:
```cpp
MuxStateOrch *mux_st_orch = new MuxStateOrch(m_stateDb, STATE_HW_MUX_CABLE_TABLE_NAME);
```

muxorch.cpp:2632-2634:
```cpp
MuxStateOrch::MuxStateOrch(DBConnector *db, const std::string& tableName) :
              Orch2(db, tableName, request_),
              mux_state_table_(db, STATE_MUX_CABLE_TABLE_NAME)
```

`Orch2` は `tableName` (= `STATE_HW_MUX_CABLE_TABLE_NAME`) を購読し、変更を `addOperation()` に配送する。

## ycabled は書き込み側のみ

y_cable_helper.py:597-631 の `put_init_values_for_grpc_states()` と
`update_table_mux_status_for_statedb_port_tbl()` が STATE_DB に直接 hset する。
ycabled は `HW_MUX_CABLE_TABLE` を購読しない（非対称構造）。

## CLI はポーリング

muxcable.py:722-747 で hgetall を使ったワンショット読み出し。
SubscriberStateTable は使用しない。
