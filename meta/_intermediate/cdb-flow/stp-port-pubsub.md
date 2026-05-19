# STP_PORT — Redis 通知メカニズム調査 (Phase G)

## 消費側: stpmgrd / StpMgr

`CONFIG_DB` の `STP_PORT` テーブルは `stpmgrd` プロセス内の `StpMgr` が消費する。

### 購読方式: SubscriberStateTable (via Orch base class)

`StpMgr` は `Orch(tables)` コンストラクタ経由で各テーブルを購読する。
`Orch::Orch(const vector<TableConnector>& tables)` は各 `TableConnector` に対して
`addConsumer(it.first, it.second)` を呼び (`orchagent/orch.cpp:127-133`)、
`addConsumer` 内部では `SubscriberStateTable` を生成して `Consumer` に渡す
(`orchagent/orch.cpp:1190`)。

```cpp
// orchagent/orch.cpp:1190
addExecutor(new Consumer(
    new SubscriberStateTable(db, tableName,
        TableConsumable::DEFAULT_POP_BATCH_SIZE, pri),
    this, tableName));
```

`SubscriberStateTable` は Redis keyspace notification を PSUBSCRIBE する
(`subscriberstatetable.cpp:20-24`):

```cpp
m_keyspace = "__keyspace@";
m_keyspace += to_string(db->getDbId()) + "__:" + tableName + m_table.getTableNameSeparator() + "*";
psubscribe(m_db, m_keyspace);
```

CONFIG_DB の DB ID = 4 (`schema.h:16`)、テーブルセパレータ = `"|"` のため、
実際の PSUBSCRIBE パターンは `__keyspace@4__:STP_PORT|*` となる。

### stpmgrd 主ループ

`stpmgrd.cpp:43-46` で `TableConnector` を生成し、`StpMgr` に渡す:

```cpp
TableConnector conf_stp_port_table(&conf_db, CFG_STP_PORT_TABLE_NAME);
// ...
vector<TableConnector> tables = { ..., conf_stp_port_table, ... };
StpMgr stpmgr(&conf_db, &app_db, &state_db, tables);
```

主ループ (`stpmgrd.cpp:93-117`):

```cpp
#define SELECT_TIMEOUT 1000  // stpmgrd.cpp:17
while (true) {
    ret = s.select(&sel, SELECT_TIMEOUT);
    if (ret == Select::TIMEOUT) {
        stpmgr.doTask();
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();
    // ...
}
```

タイムアウト値は **1000 ms** (`stpmgrd.cpp:17`)。タイムアウト時は `stpmgr.doTask()` を直接呼び出してキューに残ったエントリを再処理する。

### doStpPortTask 処理フロー

`StpMgr::doTask()` が table 名で分岐して `doStpPortTask(consumer)` を呼ぶ
(`stpmgr.cpp:63-64`)。`doStpPortTask` は以下の順に処理する:

1. `stpGlobalTask == false` なら即 `return`（STP グローバル設定が先行必要）
2. LAG が空 (`isLagEmpty(key)`) なら `erase(it)` で破棄
3. SET 操作かつ `l2ProtoEnabled == L2_NONE`（STP 未設定）なら `++it` で保留
4. DEL 操作かつ `l2ProtoEnabled == L2_NONE` なら `erase(it)` で破棄
5. それ以外: `processStpPortAttr(op, fvs, key)` → `sendMsgStpd(STP_PORT_CONFIG)` で stpd へ IPC 送信

キューに残ったエントリは次の SELECT_TIMEOUT 発火時の `doTask()` で再処理される。

## 書き込み側

`STP_PORT` テーブルへの書き込み元は **SONiC CLI (`config/stp.py`)** のみ。
`redis-cli -n 4 HSET "STP_PORT|<interface>" ...` 相当の書き込みが `click`
フレームワーク経由で実行される。`ProducerStateTable` / ZMQ は使用されない（CONFIG_DB
への直接書き込み）。

## 定数サマリー

| パラメータ | 値 | ソース |
|-----------|-----|--------|
| CONFIG_DB ID | `4` | `schema.h:16` |
| PSUBSCRIBE パターン | `__keyspace@4__:STP_PORT|*` | `subscriberstatetable.cpp:20-24` |
| SELECT_TIMEOUT | `1000` ms | `stpmgrd.cpp:17` |
| DEFAULT_POP_BATCH_SIZE | `128` | `common/table.h:164` |
