# stp-port ordering phase

## 調査対象
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgrd.cpp`

## CONFIG_DB テーブル購読順序

`stpmgrd.cpp` では以下の順序で `TableConnector` を登録し、`Select` ループに渡す:

1. `STP` (CFG_STP_GLOBAL_TABLE_NAME)
2. `STP_VLAN`
3. `STP_VLAN_PORT`
4. `STP_PORT`
5. `LAG_MEMBER`
6. `STATE_VLAN_MEMBER`
7. `STP_MST`
8. `STP_MST_INST`
9. `STP_MST_PORT`

## doTask() ディスパッチ

`stpmgr.cpp:51-75` の `doTask()` でテーブル名によって処理関数を振り分ける:

- `STP` → `doStpGlobalTask()`
- `STP_VLAN` → `doStpVlanTask()`
- `STP_VLAN_PORT` → `doStpVlanPortTask()`
- `STP_PORT` → `doStpPortTask()`
- `LAG_MEMBER` → `doLagMemUpdateTask()`
- `STATE_VLAN_MEMBER` → `doVlanMemUpdateTask()`
- `STP_MST` → `doStpMstGlobalTask()`
- `STP_MST_INST` → `doStpMstInstTask()`
- `STP_MST_PORT` → `doStpMstInstPortTask()`

## STP_PORT の起動順序ガード

`doStpPortTask()` (stpmgr.cpp:630-634):
```cpp
if (stpGlobalTask == false)
    return;
```

`STP_PORT` イベントは `STP|GLOBAL` 受信完了 (`stpGlobalTask = true`) 前は無視される。
`stpPortTask` フラグはこの関数内で `true` にセットされる (stpmgr.cpp:637-638)。

## STP_VLAN の起動順序ガード

`doStpVlanTask()` (stpmgr.cpp:183):
```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
```

`STP_VLAN` は `STP` 受信 **かつ** (`STP_PORT` 受信済み **または** CONFIG_DB の `STP_PORT` テーブルが空) の条件を満たすまで保留される。

## STP_VLAN_PORT の起動順序ガード

`doStpVlanPortTask()` (stpmgr.cpp:448-450):
```cpp
if (stpGlobalTask == false || stpVlanTask == false || stpPortTask == false)
    return;
```

`STP_VLAN_PORT` は STP/STP_VLAN/STP_PORT の全テーブルが受信済みになるまで保留される。

## MST 系の起動順序ガード

`doStpMstGlobalTask()` → `stpGlobalTask` のみ必要。
`doStpMstInstPortTask()` (stpmgr.cpp:1160):
```cpp
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```

## L2 プロトコル未確定時の STP_PORT 処理

`doStpPortTask()` は `l2ProtoEnabled == L2_NONE` (STP 未設定) の場合:
- SET イベント: `it++` でスキップ (待機キューに残す)
- DEL イベント: 即座に消費してドロップ

STP モード (`pvst` または `mst`) が `STP|GLOBAL` から確定した後に SET イベントが処理される。

## 依存関係の要約

```
STP|GLOBAL (stpGlobalTask=true)
    └─ STP_PORT 受信可能になる (stpPortTask=true)
          └─ STP_VLAN 受信可能になる (stpVlanTask=true)
                └─ STP_VLAN_PORT 受信可能になる
```

MST 系:
```
STP|GLOBAL (stpGlobalTask=true)
    └─ STP_MST 受信可能
    └─ STP_MST_INST (stpMstInstTask=true)
          └─ STP_MST_PORT (stpPortTask=true も必要)
```
