# COPP_GROUP — Phase F 副次 DB 書き込み調査

## 調査対象

- `sonic-swss/cfgmgr/coppmgr.cpp`
- `sonic-swss/orchagent/copporch.cpp`

## 副次書き込み一覧

### 1. APPL_DB — COPP_TABLE (coppmgr.cpp)

COPP_GROUP の SET 処理で `CoppMgr::doCoppGroupTask()` が
`m_appCoppTable.set(key, modified_fvs)` を呼び出し、APPL_DB の
`COPP_TABLE|<group>` を作成・更新する（coppmgr.cpp:874）。

DEL 処理では init_cfg に同名エントリが存在する場合は init 値で `set()`
（実質リセット）、存在しない場合は `m_appCoppTable.del(key)` で削除する
（coppmgr.cpp:891, 914）。

### 2. STATE_DB — COPP_GROUP_TABLE (coppmgr.cpp)

SET 成功後: `setCoppGroupStateOk(key)` → `m_stateCoppGroupTable.set(alias, {state: ok})`
（coppmgr.cpp:875, 915）

DEL 後: `delCoppGroupStateOk(key)` → `m_stateCoppGroupTable.del(alias)`
（coppmgr.cpp:892）

### 3. SAI — HOSTIF_TRAP_GROUP (copporch.cpp)

`CoppOrch::processCoppRule()` が APPL_DB の変化を受けて
`sai_hostif_api->create_hostif_trap_group()` を呼ぶ（copporch.cpp:780）。
DEL 時は `remove_hostif_trap_group()` を呼ぶ（copporch.cpp:1138）。

### 4. SAI — POLICER (copporch.cpp)

`cir`/`cbs`/`meter_type`/`mode`/`color` フィールドが設定されている場合、
`sai_policer_api->create_policer()` で policer を作成し trap group に bind する
（copporch.cpp:604, 621）。
DEL 時または policer フィールドが削除された場合は `remove_policer()` → `sai_policer_api->remove_policer()` （copporch.cpp:563）。

### 5. SAI — Genetlink HOSTIF (copporch.cpp)

`genetlink_name` / `genetlink_mcgrp_name` フィールドが設定されている場合、
`sai_hostif_api->create_hostif()` でカーネル Genetlink ソケットを作成し、
`create_hostif_table_entry()` で trap → hostif のマッピングを登録する
（copporch.cpp:664, 453）。
DEL 時は `removeGenetlinkHostIf()` → `remove_hostif_table_entry()` + `remove_hostif()` （copporch.cpp:481, 698）。

### 6. STATE_DB — COPP_TRAP_TABLE (hw_status) — 連動

COPP_GROUP に属するトラップが削除・リセットされる際に
`CoppOrch::updateTrapOperStatus()` が `COPP_TRAP_TABLE|<trap_name>.hw_status` を
`not-installed` に更新する（copporch.cpp:1413）。

### 7. COUNTERS_DB — COUNTERS_TRAP_NAME_MAP (間接)

COPP_GROUP DEL 時に属するトラップが `removeTrap()` → `unbindTrapCounter()` を経由して
`COUNTERS_TRAP_NAME_MAP` から trap エントリを削除し、FlexCounter から counter を除去する
（copporch.cpp:1487-1495）。

## 証跡

- coppmgr.cpp:874, 875, 891, 892, 914, 915
- copporch.cpp:563, 604, 621, 664, 780, 1107, 1113, 1138, 1413, 1487-1495
