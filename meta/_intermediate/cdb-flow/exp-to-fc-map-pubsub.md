# EXP_TO_FC_MAP — Phase G 調査証跡 (pubsub)

## 調査対象

- テーブル: `EXP_TO_FC_MAP`
- Consumer: `QosOrch` (`handleExpToFcTable`)
- ソース: `sonic-swss/orchagent/orchdaemon.cpp:367-384`, `orch.cpp:1186-1196`, `qosorch.cpp:1317-1345,2231-2300`

## 購読登録の流れ

`orchdaemon.cpp:367-384` で `qos_tables` ベクタに `CFG_EXP_TO_FC_MAP_TABLE_NAME` が追加され、`new QosOrch(m_configDb, qos_tables)` に渡される。`QosOrch` コンストラクタは `Orch(db, tableNames)` を介して `Orch::addConsumer()` を呼ぶ。

```cpp
// orchdaemon.cpp:367-384
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    ...
    CFG_EXP_TO_FC_MAP_TABLE_NAME,
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`addConsumer()` は CONFIG_DB 向けに `swss::SubscriberStateTable` を生成する (`orch.cpp:1190`)。

```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    // CONFIG_DB は SubscriberStateTable
    addExecutor(new Consumer(
        new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri),
        this, tableName));
}
```

## ハンドラ登録とディスパッチ

```
orchdaemon.cpp:367-384  qos_tables に CFG_EXP_TO_FC_MAP_TABLE_NAME を追加
qosorch.cpp:1338        initTableHandlers() で m_qos_handler_map[CFG_EXP_TO_FC_MAP_TABLE_NAME]
                         = &QosOrch::handleExpToFcTable を登録
qosorch.cpp:2231-2252   QosOrch::doTask() が PORT_QOS_MAP / QUEUE より先に全 QoS map を drain
                         （EXP_TO_FC_MAP の先行処理を保証）
qosorch.cpp:2253-2300   QosOrch::doTask(Consumer&) がハンドラ関数ポインタ経由でディスパッチ
```

`handleExpToFcTable()` → `ExpToFcMapHandler::processWorkItem()` → `ExpToFcMapHandler::convertFieldValuesToAttributes()` → `sai_qos_map_api->create_qos_map()` / `set_qos_map_attribute()` / `remove_qos_map()`。

## drain 順序の実装詳細

`QosOrch::doTask()` (L2231-2252) は `PORT_QOS_MAP` と `QUEUE` を最後に drain するよう実装されており、`EXP_TO_FC_MAP` を含む全マップテーブルが先行して処理される。これにより同一イベントループ内で `EXP_TO_FC_MAP` SET → `PORT_QOS_MAP` SET の順に投入されても `task_need_retry` なしで処理できる。

## select タイムアウトとバッチサイズ

- select タイムアウト: **1000 ms** (`SELECT_TIMEOUT`, `orchdaemon.cpp:23`)
- バッチサイズ: **128** (`DEFAULT_POP_BATCH_SIZE`, `table.h:164`)
- リトライ: `m_toSync` 残留方式（`task_need_retry` 時はエントリを保持し次回 drain で再処理）

## 起動時スナップショット

`Orch` 基底クラスは SELECT ループ開始前に既存エントリをスナップショット取得して `m_toSync` に積む。`allPortsReady()` が false の間は `doTask()` が即 return するため、スナップショット分は全ポート ready 後に一括処理される（silent defer）。

## Evidence

- `orchdaemon.cpp:367-384` — qos_tables 登録
- `orch.cpp:1186-1196` — SubscriberStateTable 生成
- `qosorch.cpp:1317-1345` — initTableHandlers / handleExpToFcTable 登録
- `qosorch.cpp:2231-2300` — doTask drain 順序
- `table.h:164` — DEFAULT_POP_BATCH_SIZE = 128
