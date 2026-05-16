# CONFIG_DB TC_TO_QUEUE_MAP — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `TC_TO_QUEUE_MAP` テーブル（スキーマ定数: `CFG_TC_TO_QUEUE_MAP_TABLE_NAME`、`sonic-swss-common/common/schema.h`）。

ソース確認: `sonic-swss/orchagent/qosorch.cpp`、`sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/orchagent/orch.cpp`、`sonic-swss-common/common/subscriberstatetable.{h,cpp}`、`sonic-swss-common/common/table.h`。

## 1. 購読 API — `SubscriberStateTable` (keyspace 通知ベース)

CONFIG_DB の `TC_TO_QUEUE_MAP` は `orchdaemon.cpp` で以下のように `qos_tables` ベクタの先頭エントリとして `QosOrch` に登録される（`orchdaemon.cpp:367-384`）。

```cpp
// orchdaemon.cpp:367-384
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    // ... (省略)
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`QosOrch::QosOrch(DBConnector *db, vector<string> &tableNames)` は基底 `Orch(db, tableNames)` を呼び出し、各テーブル名ごとに `Orch::addConsumer()` が実行される。`addConsumer()` は DB ID で分岐する（`orch.cpp:1186-1196`）:

```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

CONFIG_DB はこの分岐の最初の if 節にマッチするため、**`SubscriberStateTable`** が選択される。

- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` への `PSUBSCRIBE`) を購読し、通知 (`set` / `hset` / `del` / `hdel` 等の op 名) を受信したら **`HGETALL` で値を再取得**してから `pops()` で `(key, op, fvs)` タプル列を返す。
- バッチサイズは **`TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`** (`table.h:164`、ハードコード)。`Orch::addConsumer()` がハードコードで渡しており、`orchagent -b` オプションの影響を受けない（`-b` は `gBatchSize` のみを変えるため APPL_DB 側 `ConsumerStateTable` だけに作用する）。
- TTL は CONFIG_DB の全エントリで未設定（CONFIG_DB は永続前提）。

## 2. 書き込み側 (publisher)

CONFIG_DB の `TC_TO_QUEUE_MAP` は CLI `config qos reload`（`sonic-cfggen` + `qos_config.j2`）または各プラットフォームの `qos.json` 投入時に `Table::set()` / `swsssdk` ベースで `HSET <CONFIG_DB>:TC_TO_QUEUE_MAP|<name>|<tc> qindex <value>` を発行する。明示的な `PUBLISH` は行われず、Redis の keyspace 通知設定が `__keyspace@<dbId>__:TC_TO_QUEUE_MAP|<name>|<tc>` イベントを発行し、購読者 (`QosOrch`) がそれを受信する。

## 3. 購読側ディスパッチ

`QosOrch::doTask(Consumer &consumer)` は `consumer.getTableName()` でテーブル名を取得し、`m_qos_handler_map` で登録済みハンドラを検索してディスパッチする（`qosorch.cpp:2254-2296`）:

```cpp
// qosorch.cpp:2254-2296 (概略)
void QosOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return;
    // ...
    auto qos_map_type_name = consumer.getTableName();
    auto task_status = (this->*(m_qos_handler_map[qos_map_type_name]))(consumer, it->second);
    // ...
}
```

`m_qos_handler_map` への `TC_TO_QUEUE_MAP` 登録は `initTableHandlers()` 内で行われる（`qosorch.cpp:1332`）:

```cpp
m_qos_handler_map.insert(qos_handler_pair(CFG_TC_TO_QUEUE_MAP_TABLE_NAME, &QosOrch::handleTcToQueueTable));
```

`QosOrch::handleTcToQueueTable()` は `TcToQueueMapHandler::processWorkItem()` に委譲し、SET 時は `addQosItem()` → `sai_qos_map_api->create_qos_map()` (SAI_QOS_MAP_TYPE_TC_TO_QUEUE)、DEL 時は参照チェック後 `remove_qos_map()` を呼ぶ。

`QosOrch::doTask()` (引数なし版、`qosorch.cpp:2231`) は PORT_QOS_MAP / QUEUE テーブルを最後に処理する特殊な順序制御を行い、それ以外（`TC_TO_QUEUE_MAP` を含む）を先に drain する。

## 4. select タイムアウト

```cpp
// orchdaemon.cpp:22-23
#define SELECT_TIMEOUT 1000
```

`m_select->select(&s, SELECT_TIMEOUT)` は **1000 ms (1 秒)** で wake up し、retry / heartbeat 処理を回す。keyspace 通知到着時は即座に wake up し、`execute()` → `pops()` (HGETALL) → `doTask()` が走る。

## 5. リトライキャッシュ

QosOrch は `task_need_retry` を返した場合、`it` のインクリメントをスキップして `m_toSync` にエントリを残す（`qosorch.cpp:2295`）。参照ポート解放待ちや SAI 一時エラー時に再試行される。専用 `createRetryCache()` は呼ばれないが、`m_toSync` が事実上のリトライキャッシュとして機能する。

## 6. サマリ

| 観点 | CONFIG_DB 側 `TC_TO_QUEUE_MAP` |
|---|---|
| 購読方式 | `swss::SubscriberStateTable`（Redis keyspace 通知 `__keyspace@<dbId>__:TC_TO_QUEUE_MAP|*` の `PSUBSCRIBE`） |
| バッチサイズ | `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128` (`table.h:164`、ハードコード) |
| select タイムアウト | 1000 ms (`SELECT_TIMEOUT`, `orchdaemon.cpp:23`) |
| 書き込み側 API | `swss::Table::set()` / `swsssdk` (`HSET`); CLI `config qos reload` / `qos.json` 投入経由 |
| ハンドラ | `QosOrch::handleTcToQueueTable()` → `TcToQueueMapHandler::processWorkItem()` |
| リトライキャッシュ | `m_toSync` 残置（`task_need_retry` 時） |
| keyspace 通知 (`__keyspace@<dbId>__:...`) | **使う**（`SubscriberStateTable` の基盤プロトコル） |
| channel `<TABLE>_CHANNEL` PUBLISH | 使わない |
| TTL | 未使用 (CONFIG_DB は永続) |
| `orchagent -b` 影響 | なし（CONFIG_DB は `gBatchSize` ではなく `DEFAULT_POP_BATCH_SIZE` 固定） |
| doTask 処理順 | `TC_TO_QUEUE_MAP` は PORT_QOS_MAP / QUEUE より先に drain される (`qosorch.cpp:2231-2252`) |

## 7. サービス再起動トリガー

なし。`QosOrch` は orchagent プロセス内のハンドラで、`TC_TO_QUEUE_MAP` の追加・変更・削除は SAI QoS map のライブ操作 (`sai_qos_map_api->create_qos_map` / `remove_qos_map`) のみで反映され、プロセス再起動・サービス restart を伴わない。

## 8. Evidence サマリ

- `sonic-swss/orchagent/orchdaemon.cpp` L22-23, L367-384, L959 — SELECT_TIMEOUT、`qos_tables` ベクタ構成、`new QosOrch(m_configDb, qos_tables)`、select ループ
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` の DB ID 分岐（CONFIG_DB → `SubscriberStateTable`）
- `sonic-swss/orchagent/qosorch.cpp` L1332, L2231-2252, L2254-2296, L475-479 — `initTableHandlers()` への登録、`doTask()` 実装、`handleTcToQueueTable()` → `TcToQueueMapHandler`、SAI `create_qos_map` 呼び出し
- `sonic-swss-common/common/table.h` L164 — `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`
- `sonic-swss-common/common/schema.h` — `CFG_TC_TO_QUEUE_MAP_TABLE_NAME` 定数
