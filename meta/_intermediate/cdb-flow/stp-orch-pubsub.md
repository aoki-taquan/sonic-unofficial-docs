# stp-orch pubsub — Phase G 分析メモ

## 概要

StpOrch が購読する APPL_DB 4 テーブルと、STATE_DB `STP_TABLE` の通知メカニズムを整理する。

## APPL_DB 書き手 (stpd / stpmgrd)

stpd は STP デーモンで `stpmgrd` (`cfgmgr/stpmgrd.cpp`) を介して APPL_DB に書き込む。
stpmgrd は stpd からの IPC メッセージ (Unix Domain Socket) をもとに APPL_DB の 4 テーブルへ書き込む。

SONiC の APPL_DB 書き込み標準は `ProducerStateTable` 経由であり、書き込みごとに
`<TABLE>_CHANNEL@0` へ PUBLISH が発行される。

参照: sonic-swss-common `common/schema.h:113-124` (テーブル名定数)

## APPL_DB 消費側 (StpOrch)

`orchdaemon.cpp:262` で StpOrch を APPL_DB + stateDb で初期化。
`Orch::addConsumer()` (`orch.cpp:1186-1197`) で APPL_DB (db ID ≠ CONFIG_DB/STATE_DB) の場合は
`ConsumerStateTable` を使用する。

```cpp
// orch.cpp:1186-1197
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

→ 4 テーブルはすべて `ConsumerStateTable` で購読 (`__keyspace` 通知ではなく `<TABLE>_CHANNEL` SUBSCRIBE)

## orchdaemon select タイムアウト

```cpp
// orchdaemon.cpp:23, 959
#define SELECT_TIMEOUT 1000  // ms
ret = m_select->select(&s, SELECT_TIMEOUT);
```

APPL_DB からのイベントは最大 1000 ms 以内に StpOrch の doTask() に到達する。

## STATE_DB STP_TABLE 書き手

StpOrch コンストラクタで `m_stpTable = unique_ptr<Table>(new Table(stateDb, STATE_STP_TABLE_NAME))` として初期化 (stporch.cpp:26)。
書き込みは `m_stpTable->set("GLOBAL", tuples)` (stporch.cpp:612) の 1 箇所のみ。
`swss::Table` は HSET のみで PUBLISH を発行しない。

## STATE_DB STP_TABLE 読み手 (stpmgrd)

stpmgrd は `m_stateStpTable(statDb, STATE_STP_TABLE_NAME)` として `swss::Table` で保持 (stpmgr.h:253)。
`getStpMaxInstances()` (stpmgr.cpp:1381) でポーリング: `m_stateStpTable.get("GLOBAL", vmEntry)` を
最大 60 秒間 1 秒おきに繰り返す。keyspace 通知は使わない。

```cpp
// stpmgr.cpp:1388-1407
while(max_delay) {
    if (m_stateStpTable.get(key, vmEntry)) { /* parse max_stp_inst */ break; }
    sleep(1);
    max_delay--;
}
```

フォールバック: max_delay 消尽後は `STP_DEFAULT_MAX_INSTANCES = 255` を使用 (stpmgr.h:38)。
