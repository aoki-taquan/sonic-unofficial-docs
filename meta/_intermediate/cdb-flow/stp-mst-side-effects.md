# stp-mst side-effects phase (Phase F)

## 調査対象

- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 調査方針

`stpmgrd` が `STP_MST_INST` / `STP_MST_PORT` イベントを処理する際に、CONFIG_DB 以外の DB
(APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB) へ副次的な書き込みを行うか確認する。

## stpmgr.h — メンバー変数スキャン

```
Table m_cfgStpGlobalTable;      // CONFIG_DB read
Table m_cfgStpVlanTable;        // CONFIG_DB read
Table m_cfgStpVlanPortTable;    // CONFIG_DB read
Table m_cfgStpPortTable;        // CONFIG_DB read
Table m_cfgLagMemberTable;      // CONFIG_DB read
Table m_cfgVlanMemberTable;     // CONFIG_DB read
Table m_stateVlanTable;         // STATE_DB read
Table m_stateVlanMemberTable;   // STATE_DB read (subscribed via TableConnector)
Table m_stateLagTable;          // STATE_DB read
Table m_stateStpTable;          // STATE_DB read (getStpMaxInstances at init)
Table m_cfgMstGlobalTable;      // CONFIG_DB read
Table m_cfgMstInstTable;        // CONFIG_DB read
Table m_cfgMstInstPortTable;    // CONFIG_DB read
```

`ProducerStateTable` / `NotificationProducer` のメンバー変数は **0 件**。

## stpmgr.cpp — DB 書込みスキャン

grep `\.set(`, `setEntry`, `ProducerState`, `Notification`, `hset` で全行スキャン:

- 結果 0 件（構造体メンバー `msg->opcode = STP_SET_COMMAND;` のみ。DB API 呼出ではない）

## doStpMstInstTask() 挙動 (stpmgr.cpp:1023-1113)

1. 起動ガード確認 (stpGlobalTask / stpPortTask)
2. `stpMstInstTask = true` をセット (初回のみ)
3. `STP_MST_INST` の SET/DEL イベントをパース
4. `STP_MST_INST_CONFIG_MSG` 構造体を alloc
5. `sendMsgStpd(STP_MST_INST_CONFIG, ...)` で Unix Domain Socket 経由で `stpd` へ送信
6. メッセージを free

DB への書き込みは **一切なし**。

## doStpMstInstPortTask() 挙動 (stpmgr.cpp:1156-末尾)

1. 起動ガード確認 (stpGlobalTask / stpMstInstTask / stpPortTask)
2. `STP_MST_PORT` の SET/DEL イベントをパース → `processStpMstInstPortAttr()` 呼出
3. `processStpMstInstPortAttr()` (stpmgr.cpp:1116-1153) は `STP_MST_INST_PORT_CONFIG_MSG` を構築し `sendMsgStpd(STP_MST_INST_PORT_CONFIG, ...)` で送信

DB への書き込みは **一切なし**。

## STATE_DB m_stateStpTable の使われ方

`getStpMaxInstances()` (stpmgr.cpp:1381-1410):
- `m_stateStpTable.get("GLOBAL", vmEntry)` で **読み取り**のみ
- 初期化時 (stpmgrd.cpp:77-78) に呼ばれ、stpd に `STP_INIT_READY` メッセージを送信
- MST テーブルの SET/DEL 処理時には呼ばれない

## APPL_DB の使われ方

`isPortInitDone()` (stpmgr.cpp:1263):
```cpp
Table portTable(app_db, APP_PORT_TABLE_NAME);
portInit = portTable.get("PortInitDone", tuples);
```
- 起動時に `APP_PORT_TABLE` から `PortInitDone` を **読み取り**のみ
- MST テーブルの SET/DEL 処理時には関与しない

## 結論

`stpmgrd` の `STP_MST_INST` / `STP_MST_PORT` ハンドラは、CONFIG_DB テーブルの読み取りと
Unix Domain Socket 経由の `stpd` へのメッセージ送信のみを行う。

副次的な DB 書き込み:
- APPL_DB: **なし**
- STATE_DB: **なし** (読み取りのみ)
- COUNTERS_DB: **なし**
- FLEX_COUNTER_DB: **なし**
- ASIC_DB: **なし**

全変更は IPC (Unix Domain Socket) 経由でユーザースペースの `stpd` デーモンへ伝達される。
