# SWITCH_TRIMMING テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SWITCH_TRIMMING` テーブル（`SWITCH_TRIMMING|GLOBAL` シングルトン）。

## 1. 購読方式 — swsscommon SubscriberStateTable (Consumer パターン)

`orchagent` の `SwitchOrch` が `SWITCH_TRIMMING` テーブルを `swsscommon.SubscriberStateTable` で購読する。

```cpp
// orchdaemon.cpp L200
TableConnector conf_switch_trim(m_configDb, CFG_SWITCH_TRIMMING_TABLE_NAME);

// orchdaemon.cpp L204-212 (switch_tables vector に追加)
vector<TableConnector> switch_tables = {
    conf_switch_hash,
    conf_switch_trim,   // ← SWITCH_TRIMMING
    ...
};
gSwitchOrch = new SwitchOrch(m_applDb, switch_tables, stateDbSwitchTable);
```

`SwitchOrch` は `Orch(connectors)` を継承し、`Orch` コンストラクタが各 `TableConnector` について `addConsumer()` → `SubscriberStateTable` を生成する（`orch.cpp:1190`）。

```cpp
// orch.cpp L1186-1190
void Orch::addConsumer(DBConnector *db, string tableName, int pri) {
    addExecutor(new Consumer(
        new SubscriberStateTable(db, tableName, ...),
        this, tableName));
}
```

## 2. keyspace 通知方式との違い

CONFIG_DB (`hostcfgd` 側のテーブル群) が Redis keyspace 通知 (PSUBSCRIBE) ベースなのに対し、orchagent 系テーブルは `swsscommon.SubscriberStateTable` を使用する。`SubscriberStateTable` は内部で keyspace notification に PSUBSCRIBE し、pop された (key, op, fields) タプルを `Consumer::execute()` → `SwitchOrch::doTask()` → `doCfgSwitchTrimmingTableTask()` にディスパッチする。

## 3. ディスパッチフロー

```cpp
// switchorch.cpp L1505-1515
void SwitchOrch::doTask(Consumer &consumer) {
    const string &tableName = consumer.getTableName();
    ...
    else if (tableName == CFG_SWITCH_TRIMMING_TABLE_NAME)
        doCfgSwitchTrimmingTableTask(consumer);
    ...
}
```

`doCfgSwitchTrimmingTableTask()` が pop した各エントリを処理する:

```
CONFIG_DB SWITCH_TRIMMING|GLOBAL  HSET
  ↓ SubscriberStateTable: keyspace notification
  ↓ orchagent select() ループ
  ↓ Consumer::execute() → SwitchOrch::doTask()
  ↓ doCfgSwitchTrimmingTableTask(consumer)
  ↓ parseTrimConfig() + validateTrimConfig()
  ↓ setSwitchTrimming() → sai_switch_api->set_switch_attribute()
```

## 4. 購読者一覧

| 購読者 | 購読方式 | 購読テーブル | ハンドラ |
|--------|---------|------------|--------|
| `orchagent` (`SwitchOrch`) | `SubscriberStateTable` (keyspace PSUBSCRIBE) | `SWITCH_TRIMMING` (CONFIG_DB) | `doCfgSwitchTrimmingTableTask()` |

他のプロセス (hostcfgd / mgrd / syncd 等) は `SWITCH_TRIMMING` を購読しない。

## 5. 通知発行側 (生産者)

- `config switch-trimming ...` CLI が `sonic-cfggen` / `ConfigDBConnector` 経由で `HSET` を発行。
- `ProducerStateTable` / `NotificationProducer` は使用しない（CONFIG_DB テーブルへの直接 `HSET`）。

## 6. select タイムアウト

`orchdaemon.cpp` の主ループは `SELECT_TIMEOUT = 1000` ms で `select()` を呼ぶ。`SWITCH_TRIMMING` エントリが来るとタイムアウトより先に返り、`SwitchOrch::doTask()` がディスパッチされる。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `SWITCH_TRIMMING` テーブルへの `ProducerStateTable` 書き込みはなし（channel ベースではない）。
- `NotificationProducer` で `SWITCH_TRIMMING` 関連通知を送出するプロセスはなし。
- 結論: `SWITCH_TRIMMING` は **CONFIG_DB → SubscriberStateTable (orchagent) → SAI** の一方向で完結する。

## 8. 参考行番号

- `sonic-swss/orchagent/orchdaemon.cpp`
  - L200: `conf_switch_trim` 宣言
  - L204-212: `switch_tables` ベクタと `SwitchOrch` 生成
- `sonic-swss/orchagent/orch.cpp`
  - L127-132: `Orch(vector<TableConnector>)` コンストラクタ
  - L1186-1190: `addConsumer` → `SubscriberStateTable` 生成
- `sonic-swss/orchagent/switchorch.cpp`
  - L1505-1515: `doTask()` テーブル名ルーティング
  - L1309-1371: `doCfgSwitchTrimmingTableTask()`
