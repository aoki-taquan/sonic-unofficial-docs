# stp-mst ordering phase

## 調査対象
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp`

## CONFIG_DB テーブル購読順序

`stpmgrd.cpp` では `TableConnector` 登録順序:

1. `STP`
2. `STP_VLAN`
3. `STP_VLAN_PORT`
4. `STP_PORT`
5. `LAG_MEMBER`
6. `STATE_VLAN_MEMBER`
7. `STP_MST`
8. `STP_MST_INST`
9. `STP_MST_PORT`

## doTask() ディスパッチ

`stpmgr.cpp:69-74`:

- `STP_MST` → `doStpMstGlobalTask()`
- `STP_MST_INST` → `doStpMstInstTask()`
- `STP_MST_PORT` → `doStpMstInstPortTask()`

## STP_MST の起動ガード

`doStpMstGlobalTask()` (`stpmgr.cpp:344`):

```cpp
if (stpGlobalTask == false)
    return;
```

`STP|GLOBAL` 受信完了 (`stpGlobalTask = true`) が先行必須。

## STP_MST_INST の起動ガード

`doStpMstInstTask()` (`stpmgr.cpp:1027-1031`):

```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
if (stpMstInstTask == false)
    stpMstInstTask = true;
```

条件: `stpGlobalTask=true` かつ (`stpPortTask=true` または STP_PORT テーブルが空)。

## STP_MST_PORT の起動ガード

`doStpMstInstPortTask()` (`stpmgr.cpp:1160`):

```cpp
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

## 依存関係の要約

```
STP|GLOBAL (stpGlobalTask=true)
    ├─ STP_MST 受信可能
    ├─ STP_PORT (stpPortTask=true)
    │       └─ STP_MST_INST (stpMstInstTask=true)
    │                 └─ STP_MST_PORT
    └─ (STP_PORT が空なら STP_MST_INST も直接処理可能)
```
