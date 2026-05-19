# stp-state pubsub — Phase G 分析メモ

## 概要

`STATE_DB STP_TABLE|GLOBAL` の通知メカニズムを整理する。

書き手: `StpOrch` (`orchagent/stporch.cpp`)
読み手: `stpmgrd` (`cfgmgr/stpmgr.cpp`)

## 書き手側: swss::Table (PUBLISH 非発行)

`StpOrch` は `m_stpTable` を `swss::Table` として保持する (`stporch.cpp:26`):

```cpp
m_stpTable = unique_ptr<Table>(new Table(stateDb, STATE_STP_TABLE_NAME));
```

書き込みは `m_stpTable->set("GLOBAL", tuples)` (`stporch.cpp:612`) の 1 箇所のみ。
`swss::Table::set()` は内部で `HSET` を発行するが、`ProducerStateTable` のような
`_KEY_SET` + `PUBLISH <TABLE>_CHANNEL` 通知は発行しない。

## 読み手側: swss::Table + ポーリング (購読なし)

`stpmgrd` は `m_stateStpTable` を `swss::Table` として保持する (`stpmgr.h:253`):

```cpp
m_stateStpTable(statDb, STATE_STP_TABLE_NAME)
```

`getStpMaxInstances()` (`stpmgr.cpp:1381-1413`) は `HGET` ベースのポーリングループで読み取る:

```cpp
while(max_delay) {
    if (m_stateStpTable.get(key, vmEntry)) { /* max_stp_inst 取得 */ break; }
    sleep(1);
    max_delay--;
}
```

`SubscriberStateTable` / `ConsumerStateTable` / keyspace 通知は使用しない。
フォールバック: max_delay 消尽後は `STP_DEFAULT_MAX_INSTANCES = 255` を使用 (`stpmgr.h:38`)。

## 結論

`STP_TABLE|GLOBAL` は Pub/Sub を使用しない純粋な「書き出し専用のステータスレジスタ」。
読み手 (`stpmgrd`) は起動時の 1 回のみポーリングで読み取り、以後は再読み取りしない。
keyspace 通知に依存する consumer は存在しない。

証跡: `stporch.cpp:26, 603-617`, `stpmgr.h:253`, `stpmgr.cpp:1381-1413`
