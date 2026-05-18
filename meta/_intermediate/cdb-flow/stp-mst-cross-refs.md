# STP_MST_INST / STP_MST_PORT — Phase C 暗黙参照テーブル調査メモ

調査対象: `sonic-swss/cfgmgr/stpmgr.cpp`
SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

## STP_MST_INST 処理が参照するテーブル

### 1. STP|GLOBAL (CONFIG_DB)

`doStpMstGlobalTask()` および `doStpMstInstTask()` の起動ガード:
```cpp
if (stpGlobalTask == false)
    return;
```
`STP|GLOBAL` イベントを受信して `stpGlobalTask = true` になるまで、
`STP_MST` / `STP_MST_INST` のイベントは保留される。
証跡: `stpmgr.cpp:85-86, 344-345, 1027-1028`

### 2. STP_PORT (CONFIG_DB)

`doStpMstInstTask()` の起動ガード:
```cpp
if (stpGlobalTask == false || (stpPortTask == false && !isStpPortEmpty()))
    return;
```
`STP_PORT` が存在する場合、そのイベントを受信して `stpPortTask = true` になるまで保留。
`isStpPortEmpty()` が `true`（STP_PORT テーブルが空）の場合はガードをスキップ。
証跡: `stpmgr.cpp:1027-1028, 1326-1339`

### 3. STP_MST_INST (→ STP_MST_PORT)

`doStpMstInstPortTask()` の起動ガード:
```cpp
if (stpGlobalTask == false || stpMstInstTask == false || stpPortTask == false)
    return;
```
`STP_MST_PORT` は `STP_MST_INST` の最初のイベント処理後 (`stpMstInstTask = true`) まで保留。
証跡: `stpmgr.cpp:1160-1161`

## 内部マップ

`m_vlanInstMap[MAX_VLANS]` — VLAN ID → MST インスタンス ID のインメモリマップ:
- `STP_MST_INST` SET/DEL 処理時に `updateVlanInstanceMap()` で更新
- PVST モードの `STP_VLAN` 処理でも参照 (`m_vlanInstMap[vlan_id]`)
- DB テーブルへの直接参照はなく、stpmgr 内部状態のみ
証跡: `stpmgr.cpp:1067, 1105, 1454-1470`

## STP_MST_PORT が参照するテーブル (直接 DB 読み出し)

`doStpMstInstPortTask()` の処理内で直接 DB クエリは発生しない。
キーパース (`key.substr(9)`) のみでインスタンス ID とインタフェース名を取得し、
`sendMsgStpd()` でデーモンに転送する。
