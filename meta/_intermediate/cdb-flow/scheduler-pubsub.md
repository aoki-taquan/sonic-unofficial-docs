# SCHEDULER — Phase G 通信メカニズム調査ノート

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp` — QosOrch コンストラクタ・doTask・handleSchedulerTable
- `sonic-swss/orchagent/orchdaemon.cpp` — QosOrch 初期化・Select ループ
- `sonic-swss/orchagent/orch.cpp` — addConsumer / Consumer / SubscriberStateTable
- `sonic-swss/orchagent/qosorch.h` — 定数定義

## 購読方式の確定

### addConsumer 分岐（orch.cpp:1186-1196）

```cpp
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

QosOrch は `m_configDb`（CONFIG_DB、dbId=4）に接続。よって `SCHEDULER` テーブルは **SubscriberStateTable** で購読される。

### QosOrch 初期化（orchdaemon.cpp:367-384）

```cpp
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,     // "SCHEDULER"
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`QosOrch::QosOrch(DBConnector *db, vector<string> &tableNames) : Orch(db, tableNames)` — 基底クラス `Orch` が tableNames をイテレートして各テーブルに `addConsumer()` を呼ぶ。

### SubscriberStateTable の仕組み

Redis keyspace 通知を使わない。`__keyevent@<dbId>__:hset` 等ではなく、swsscommon 独自の **Pub/Sub チャンネル** を使う：

- 書き込み側（`sonic-cfggen`、CLI `config qos reload`）は ConfigDB クライアントの `set()` メソッド経由で CONFIG_DB に HSET、同時にチャンネル `"SCHEDULER_CHANNEL@4"` に `"G"` を PUBLISH する。
- `SubscriberStateTable` は Redis SUBSCRIBE でそのチャンネルを購読し、通知を受けたら `pops()` で変更エントリを取り出す。

### Select ループ（orchdaemon.cpp:943-959）

```cpp
m_select->addSelectables(o->getSelectables());  // QosOrch の Consumer を登録
...
ret = m_select->select(&s, SELECT_TIMEOUT);      // 1000ms タイムアウト
```

タイムアウトは 1000ms。Consumer が Selectable として登録され、Redis 通知受信時にディスパッチされる。

### doTask ディスパッチ（qosorch.cpp:2254-2300）

```
QosOrch::doTask(Consumer& consumer)
  └─ allPortsReady() チェック（false なら即 return）
  └─ consumer.getTableName() == "SCHEDULER"
       → m_qos_handler_map["SCHEDULER"] = &QosOrch::handleSchedulerTable
            → handleSchedulerTable(consumer, tuple)
```

## 書き込み側（Producer 側）

CONFIG_DB SCHEDULER テーブルへの書き込み元：

1. **`config qos reload`** — `sonic-cfggen` が `qos_config.j2` テンプレートを展開し SCHEDULER エントリ群を CONFIG_DB に投入
2. **各プラットフォームの `qos.json.j2`** — ビルド時に SCHEDULER エントリが定義される
3. **直接 `sonic-db-cli CONFIG_DB HSET "SCHEDULER|<name>" ...`** — 手動操作

いずれも swsscommon `ConfigDBConnector.set()` を経由し、CONFIG_DB への HSET と同時に `SCHEDULER_CHANNEL@4` へ PUBLISH が発行される。

## まとめ

| 項目 | 値 |
|-----|---|
| Consumer 型 | `swss::SubscriberStateTable` |
| 購読 DB | CONFIG_DB（dbId=4） |
| 購読テーブル / チャンネル | `SCHEDULER` / `SCHEDULER_CHANNEL@4` |
| バッチサイズ | `DEFAULT_POP_BATCH_SIZE`（設定依存） |
| Select タイムアウト | 1000ms |
| 起動時 allPortsReady 待ち | あり（false なら doTask 全体が早期 return） |
| Producer 側 API | `ConfigDBConnector.set()` → HSET + PUBLISH |
| APPL_DB 書き込み | なし（CONFIG_DB → SAI 直結） |
