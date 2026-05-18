# stp-vlan pubsub phase (Phase G)

## 調査対象
- `sonic-swss/cfgmgr/stpmgrd.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/stpmgr.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h`

## stpmgrd の購読方式

`stpmgrd` は swsscommon の `Orch` + `TableConnector` フレームワークを使用する。
`TableConnector` は内部で `ConsumerStateTable` (PUBLISH/SUBSCRIBE チャネルベース) を使い、
各テーブルへの書き込みを `__keyspace` ではなく専用チャネル経由で受け取る。

### 購読登録 (stpmgrd.cpp:43-65)

```cpp
TableConnector conf_stp_global_table(&conf_db, CFG_STP_GLOBAL_TABLE_NAME);  // "STP"
TableConnector conf_stp_vlan_table(&conf_db, CFG_STP_VLAN_TABLE_NAME);      // "STP_VLAN"
TableConnector conf_stp_vlan_port_table(&conf_db, CFG_STP_VLAN_PORT_TABLE_NAME); // "STP_VLAN_PORT"
TableConnector conf_stp_port_table(&conf_db, CFG_STP_PORT_TABLE_NAME);      // "STP_PORT"
TableConnector conf_lag_member_table(&conf_db, CFG_LAG_MEMBER_TABLE_NAME);  // "LAG_MEMBER"
TableConnector state_vlan_member_table(&state_db, STATE_VLAN_MEMBER_TABLE_NAME); // "VLAN_MEMBER_TABLE"
TableConnector conf_mst_global_table(&conf_db, "STP_MST");
TableConnector conf_mst_inst_table(&conf_db, "STP_MST_INST");
TableConnector conf_mst_inst_port_table(&conf_db, "STP_MST_PORT");
```

`state_vlan_member_table` だけが STATE_DB、他は全て CONFIG_DB からの購読。

### 購読一覧

| 購読者 | DB | テーブル名 (schema.h 定数) | マクロ名 |
|--------|----|-----------------------------|----------|
| `stpmgrd` | CONFIG_DB | `STP` | `CFG_STP_GLOBAL_TABLE_NAME` |
| `stpmgrd` | CONFIG_DB | `STP_VLAN` | `CFG_STP_VLAN_TABLE_NAME` |
| `stpmgrd` | CONFIG_DB | `STP_VLAN_PORT` | `CFG_STP_VLAN_PORT_TABLE_NAME` |
| `stpmgrd` | CONFIG_DB | `STP_PORT` | `CFG_STP_PORT_TABLE_NAME` |
| `stpmgrd` | CONFIG_DB | `LAG_MEMBER` | `CFG_LAG_MEMBER_TABLE_NAME` |
| `stpmgrd` | STATE_DB | `VLAN_MEMBER_TABLE` | `STATE_VLAN_MEMBER_TABLE_NAME` |
| `stpmgrd` | CONFIG_DB | `STP_MST` / `STP_MST_INST` / `STP_MST_PORT` | (直書き文字列) |

`STP_VLAN` テーブルを購読するプロセスは `stpmgrd` のみ。
`stporch` (`orchagent`) は `STP_VLAN` を CONFIG_DB から直接読まず、
stpmgrd→stpd→stporch の IPC 経路を介して情報を受け取る。

## イベントループ (stpmgrd.cpp:92-117)

```cpp
Select s;
for (Orch *o: cfgOrchList)
    s.addSelectables(o->getSelectables());

while (true)
{
    Selectable *sel;
    int ret = s.select(&sel, SELECT_TIMEOUT);  // 1000ms タイムアウト
    if (ret == Select::ERROR) { ... continue; }
    if (ret == Select::TIMEOUT)
    {
        stpmgr.doTask();  // タイムアウト時: pending キューを再スキャン
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();
}
```

`SELECT_TIMEOUT = 1000 ms` (stpmgrd.cpp:17)。
タイムアウトごとに `doTask()` が呼ばれ、silent defer されたエントリが再試行される。

## stpmgr が読み取る STATE_DB テーブル

stpmgr は書き込み先としてではなく、参照用に以下の STATE_DB テーブルを直接 `Table::get()` で読む:

| STATE_DB テーブル | マクロ | 用途 |
|-----------------|--------|------|
| `VLAN_TABLE` | `STATE_VLAN_TABLE_NAME` | `isVlanStateOk()` — VLAN の ASIC 適用確認 |
| `VLAN_MEMBER_TABLE` | `STATE_VLAN_MEMBER_TABLE_NAME` | `doVlanMemUpdateTask()` — ポート VLAN 参加/離脱イベント受信 |
| `LAG_TABLE` | `STATE_LAG_TABLE_NAME` | LAG の状態確認 |
| `STP_TABLE` | `STATE_STP_TABLE_NAME` | `getStpMaxInstances()` — 起動時の `max_stp_instances` 取得 |

`STATE_STP_TABLE` (`STP_TABLE`) は stpmgrd が **読む** テーブルで、
`stporch` (`orchagent/stporch.cpp:26`) が **書く** テーブル。
stpmgrd は STATE_DB に書き込まない (書き込みは全て stpd → stporch 経由で ASIC_DB に反映)。

## STP_VLAN_TABLE チャネル構造

`ProducerStateTable` / `ConsumerStateTable` を使う場合:
- 書き込み側: `<TABLE>_KEY_SET` + `__keyspace@<db>__:<TABLE>_KEY_CHANNEL@<db>` に PUBLISH
- 読み取り側 (stpmgrd): SUBSCRIBE して `pops()` でバッチ取得

stpmgrd はこの `ConsumerStateTable` の仕組みを `TableConnector` + `Orch` フレームワーク経由で透過的に利用する。

## まとめ

| 項目 | 内容 |
|------|------|
| 購読方式 | `TableConnector` (ConsumerStateTable ベース PUBLISH/SUBSCRIBE) |
| 購読元 DB | CONFIG_DB (`STP_VLAN`) + STATE_DB (`VLAN_MEMBER_TABLE`) |
| イベントループ | `swss::Select::select()` + 1000ms タイムアウト |
| 購読者 | `stpmgrd` のみ (`stporch` は IPC 経由で間接取得) |
| STATE_DB 書込 | stpmgrd は書き込まない (読み取り専用) |
| TTL | なし (CONFIG_DB は永続ストレージ前提) |
