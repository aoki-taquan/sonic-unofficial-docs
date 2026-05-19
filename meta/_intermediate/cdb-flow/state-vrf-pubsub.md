# state-vrf Phase G — pubsub 調査メモ

調査日: 2026-05-19
ソース: sonic-swss/cfgmgr/vrfmgr.cpp, vrfmgr.h, intfmgr.cpp, intfmgr.h, vxlanmgr.cpp, orchagent/vrforch.cpp

## 結論

VRF_TABLE / VRF_OBJECT_TABLE はすべて swss::Table (素の HSET/HDEL) で書き込み、
consumer 側は doTask() イテレーション内の Table::get() ポーリングで読み出す。
ProducerStateTable / NotificationProducer / SubscriberStateTable は不使用。

## 根拠コード

### 書き手
- vrfmgr.h:43: `Table m_stateVrfTable, m_stateVrfObjectTable;`
- vrfmgr.cpp:25-26: 初期化 `m_stateVrfTable(stateDb, STATE_VRF_TABLE_NAME), m_stateVrfObjectTable(stateDb, STATE_VRF_OBJECT_TABLE_NAME)`
- vrfmgr.cpp:289: `m_stateVrfTable.set(vrfName, fvVector)` — VRF SET 時
- vrfmgr.cpp:308: `m_stateVrfTable.set(vrfName, ...)` — VNET VRF
- vrfmgr.cpp:339, 351: `m_stateVrfTable.del(vrfName)` — VRF DEL 時
- vrforch.cpp:120, 150: `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` — SAI 成功後
- vrforch.cpp:193: `m_stateVrfObjectTable.del(vrf_name)` — SAI remove 成功後

### 読み手
- intfmgr.h:33: `Table m_stateVrfTable;` (plain Table, not SubscriberStateTable)
- intfmgr.cpp:40: `m_stateVrfTable(stateDb, STATE_VRF_TABLE_NAME)`
- intfmgr.cpp:671, 680: `m_stateVrfTable.get(alias, temp)` — polling

- vxlanmgr.cpp:192: `m_stateVrfTable(stateDb, STATE_VRF_TABLE_NAME)` (plain Table)
- vxlanmgr.cpp:744: `isVrfStateOk()` → `m_stateVrfTable.get(vrfName, temp)` — polling

- vrfmgr.cpp:204-208: `isVrfObjExist()` → `m_stateVrfObjectTable.get(vrfName, temp)` — polling

## 注意事項

intfmgr.cpp:45-52 では STATE_PORT_TABLE と STATE_LAG_TABLE に SubscriberStateTable を使っているが、
STATE_VRF_TABLE には SubscriberStateTable を使っていない（plain Table のみ）。
