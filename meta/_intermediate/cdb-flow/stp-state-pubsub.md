# stp-state Phase G pubsub 調査証跡

## 調査対象

- `sonic-swss/orchagent/stporch.cpp` — updateMaxStpInstance(), constructor
- `sonic-swss/orchagent/orchdaemon.cpp` — StpOrch 登録, stp_tables 定義
- `sonic-swss/cfgmgr/stpmgrd.cpp` — main(), TableConnector 登録, Select ループ
- `sonic-swss/cfgmgr/stpmgr.cpp` — StpMgr constructor, getStpMaxInstances()
- `sonic-swss/cfgmgr/stpmgr.h` — m_stateStpTable 型定義

## 主要発見事項

### STP_TABLE は pub/sub を使わない

`stpmgrd` は `STP_TABLE|GLOBAL` に対して `SubscriberStateTable` を使用しない。
`StpMgr::getStpMaxInstances()` (`stpmgr.cpp:1381-1413`) が `swss::Table::get()` を
1 秒間隔で最大 60 回呼び出すポーリングループ。

```cpp
// stpmgr.h:33
swss::Table m_stateStpTable;
// 初期化: stpmgr.cpp:33
m_stateStpTable(statDb, STATE_STP_TABLE_NAME)
// 使用: stpmgr.cpp:1391
if (m_stateStpTable.get(key, vmEntry))
```

### StpOrch の書き込みパス

`orchdaemon.cpp:262`:
```cpp
gStpOrch = new StpOrch(m_applDb, m_stateDb, stp_tables);
```

`stporch.cpp:603-617` `updateMaxStpInstance()` が `swss::Table::set("GLOBAL", ...)` で書く。
コンストラクタからのみ呼ばれる（起動時 1 回）。

### StpOrch の APPL_DB 購読テーブル (orchdaemon.cpp:256-261)

```cpp
vector<string> stp_tables = {
    APP_STP_VLAN_INSTANCE_TABLE_NAME,
    APP_STP_PORT_STATE_TABLE_NAME,
    APP_STP_FASTAGEING_FLUSH_TABLE_NAME,
    APP_STP_INST_PORT_FLUSH_TABLE_NAME
};
```

これらは stpd → APPL_DB → StpOrch の経路で、STATE_DB STP_TABLE 書き込みとは別系統。

### stpmgrd の CONFIG_DB 購読 (stpmgrd.cpp:43-65)

TableConnector × 6 テーブルを `Orch(tables)` に渡す。
SubscriberStateTable として keyspace 通知を受信する。

STATE_VLAN_MEMBER_TABLE_NAME も購読対象（VLAN メンバー変化を検知するため STATE_DB も 1 テーブル購読する）。
