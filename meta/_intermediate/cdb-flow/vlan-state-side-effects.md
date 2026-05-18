# vlan-state Phase F — 副次 DB 書込スキャン

## 対象

`STATE_DB VLAN_TABLE` を書き込む主体: `vlanmgrd` (`cfgmgr/vlanmgr.cpp`)

## スキャン方法

`vlanmgr.cpp` 全体で以下の書き込み先を列挙:
- `m_stateVlanTable` — STATE_DB `VLAN_TABLE` (主作用)
- `m_stateVlanMemberTable` — STATE_DB `VLAN_MEMBER_TABLE`
- `m_appVlanTableProducer` — APP_DB `VLAN_TABLE`
- `m_appVlanMemberTableProducer` — APP_DB `VLAN_MEMBER_TABLE`

## 調査結果

### doVlanTask() での書込み順序 (vlanmgr.cpp:437-443)

```cpp
m_appVlanTableProducer.set(key, fvVector);   // APP_DB VLAN_TABLE (先)
m_stateVlanTable.set(key, fvVector);          // STATE_DB VLAN_TABLE (後・主作用)
```

### DEL 時 (vlanmgr.cpp:462-463)

```cpp
m_appVlanTableProducer.del(key);  // APP_DB VLAN_TABLE 削除
m_stateVlanTable.del(key);        // STATE_DB VLAN_TABLE 削除
```

### VLAN_MEMBER 処理での副次書込 (vlanmgr.cpp:672-698, 889-907, 942-973)

VLAN_MEMBER の SET/DEL 処理では:
- `m_appVlanMemberTableProducer.set/del` → APP_DB `VLAN_MEMBER_TABLE`
- `m_stateVlanMemberTable.set/del` → STATE_DB `VLAN_MEMBER_TABLE`

これらは VLAN_TABLE ページの主作用ではなく VLAN_MEMBER_TABLE ページの主作用。

### COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB

vlanmgrd は cfgmgr デーモンであり SAI を呼ばない。COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB への書き込みは存在しない。

### ResponsePublisher / NotificationProducer

vlanmgr.cpp 全体で `ResponsePublisher` / `NotificationProducer` の使用なし。

## 結論

`VLAN_TABLE` (STATE_DB) の書き込みに付随する主な副次 DB 書込みは:
1. **APP_DB `VLAN_TABLE`**: VLAN_TABLE SET の直前に書き込まれる (主トリガと同一タスク内)
2. **その他**: 存在しない

`STATE_DB VLAN_MEMBER_TABLE` / `APP_DB VLAN_MEMBER_TABLE` は別テーブルの主作用であり、VLAN_TABLE の副次 DB 書込みではない。

## evidence

- `sonic-swss/cfgmgr/vlanmgr.cpp:437-443` — APP_DB → STATE_DB の順序書込み
- `sonic-swss/cfgmgr/vlanmgr.cpp:462-463` — DEL 時の APP_DB → STATE_DB 削除順序
