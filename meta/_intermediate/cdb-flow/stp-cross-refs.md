# STP cross-refs (Phase C)

## 調査対象
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h`   (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## コンストラクタで初期化されるテーブル接続 (stpmgr.cpp:25-37)

stpmgr.cpp のコンストラクタが保持するテーブル一覧:

| メンバ変数 | DB | テーブル定数 | 役割 |
|---|---|---|---|
| `m_cfgStpGlobalTable` | CONFIG_DB | `CFG_STP_GLOBAL_TABLE_NAME` (`STP`) | 購読対象 (主キー) |
| `m_cfgStpVlanTable` | CONFIG_DB | `CFG_STP_VLAN_TABLE_NAME` (`STP_VLAN`) | 購読対象 |
| `m_cfgStpVlanPortTable` | CONFIG_DB | `CFG_STP_VLAN_PORT_TABLE_NAME` (`STP_VLAN_PORT`) | 購読対象 |
| `m_cfgStpPortTable` | CONFIG_DB | `CFG_STP_PORT_TABLE_NAME` (`STP_PORT`) | 購読対象 + getKeys で空判定 |
| `m_cfgLagMemberTable` | CONFIG_DB | `CFG_LAG_MEMBER_TABLE_NAME` | LAG メンバー参照 |
| `m_cfgVlanMemberTable` | CONFIG_DB | `CFG_VLAN_MEMBER_TABLE_NAME` | VLAN メンバーポート解決 |
| `m_stateVlanTable` | STATE_DB | `STATE_VLAN_TABLE_NAME` | VLAN 状態確認 (isVlanStateOk) |
| `m_stateLagTable` | STATE_DB | `STATE_LAG_TABLE_NAME` | LAG 状態確認 (isLagStateOk) |
| `m_stateStpTable` | STATE_DB | `STATE_STP_TABLE_NAME` | STP ポート状態確認 |
| `m_stateVlanMemberTable` | STATE_DB | `STATE_VLAN_MEMBER_TABLE_NAME` | VLAN メンバー状態 |
| `m_cfgMstGlobalTable` | CONFIG_DB | `STP_MST` | MST グローバル設定 |
| `m_cfgMstInstTable` | CONFIG_DB | `STP_MST_INST` | MST インスタンス設定 |
| `m_cfgMstInstPortTable` | CONFIG_DB | `STP_MST_PORT` | MST インスタンスポート設定 |

## APPL_DB クロス参照 — PORT_INIT_DONE 待機 (stpmgr.cpp:1257-1273)

`isPortInitDone()` (stpmgr.cpp:1257):
```cpp
Table portTable(app_db, APP_PORT_TABLE_NAME);
portInit = portTable.get("PortInitDone", tuples);
```
`APPL_DB:APP_PORT_TABLE|PortInitDone` の存在を `stpmgrd` 起動ループ内で 1 秒おきにポーリングする。
このエントリは `portsyncd` + `orchagent` の初期化完了後に書かれる。stpmgrd は CONFIG_DB の STP イベントを消費する前にこの参照に依存する。

## STATE_DB クロス参照

### isVlanStateOk (stpmgr.cpp:1276-1290)

`doStpVlanTask()` から呼ばれ、STP_VLAN の各 SET 前に `STATE_VLAN_TABLE` を参照する:
```cpp
if (m_stateVlanTable.get(alias, temp)) return true;
```
対応するエントリが STATE_DB に存在しない VLAN は SET がスキップされる (silent skip)。

### isLagStateOk / isLagEmpty (stpmgr.cpp:1291-1330)

`doStpPortTask()` / `doStpVlanPortTask()` がポートが PortChannel の場合に `m_lagMap` を参照。
LAG にメンバーがなければ SET をスキップし、`doLagMemUpdateTask()` による更新後に再処理される。

### m_stateStpTable (stpmgr.cpp:1391)

`doStpVlanPortTask()` 内で既存エントリ確認のために `STATE_STP_TABLE` を参照する可能性がある。
```cpp
if (m_stateStpTable.get(key, vmEntry))
```

## CONFIG_DB クロス参照

### VLAN_MEMBER (stpmgr.cpp:1366)

`m_cfgVlanMemberTable.get(key, vmEntry)` で STP_PORT 処理時に VLAN メンバーシップを確認する。
ポートが VLAN メンバーになっていない状態での STP_PORT SET は実際のポート設定が遅延する。

## 依存グラフ要約

```
CONFIG_DB: STP|GLOBAL, STP_VLAN, STP_PORT, STP_VLAN_PORT   ← 主購読
CONFIG_DB: LAG_MEMBER, VLAN_MEMBER                           ← 補助参照
CONFIG_DB: STP_MST, STP_MST_INST, STP_MST_PORT             ← MST 購読

APPL_DB:   APP_PORT_TABLE|PortInitDone                       ← 起動ガード

STATE_DB:  STATE_VLAN_TABLE                                  ← VLAN 存在確認
STATE_DB:  STATE_LAG_TABLE                                   ← LAG 状態確認
STATE_DB:  STATE_STP_TABLE                                   ← STP ポート確認
STATE_DB:  STATE_VLAN_MEMBER_TABLE                           ← VLAN メンバー状態
```
