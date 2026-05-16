# BUFFER_POOL テーブル — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `BUFFER_POOL` テーブル（スキーマ定数: `CFG_BUFFER_POOL_TABLE_NAME`）および APPL_DB の `BUFFER_POOL_TABLE`（`APP_BUFFER_POOL_TABLE_NAME`）。

ソース確認: `sonic-swss/cfgmgr/buffermgrdyn.cpp`、`cfgmgr/buffermgr.cpp`、`cfgmgr/buffermgrd.cpp`、`orchagent/bufferorch.cpp`、`orchagent/orch.cpp`（`addConsumer`）、`orchagent/response_publisher.h`。

## 1. CONFIG_DB → buffermgr/buffermgrdyn: SubscriberStateTable

`buffermgrd.cpp` の dynamic buffer model パスでは `CFG_BUFFER_POOL_TABLE_NAME` を含む `vector<TableConnector>` を構築し `BufferMgrDynamic` コンストラクタに渡す。

```cpp
// sonic-swss/cfgmgr/buffermgrd.cpp:174-187
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),   // ← BUFFER_POOL
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    ...
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME),
};
cfgOrchList.emplace_back(new BufferMgrDynamic(..., buffer_table_connectors, ...));
```

`BufferMgrDynamic` は `Orch(tables)` を継承し、`Orch::addConsumer()` が各 `TableConnector` を処理する。

```cpp
// sonic-swss/orchagent/orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || ...)
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

CONFIG_DB は DB ID チェックにマッチするため **`SubscriberStateTable`** が選択される。これは Redis の **keyspace 通知** (`__keyspace@4__:BUFFER_POOL|*` の `PSUBSCRIBE`) を購読し、変更検知後に `HGETALL` で値を再取得して `pops()` で `(key, op, fvs)` タプルを返す。

- バッチサイズ: `DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`）。`cfgmgrd -b` フラグは `gBatchSize` のみ変更するため、CONFIG_DB 側には影響しない。
- TTL: CONFIG_DB の全エントリで未設定（永続前提）。

static buffer model (`BufferMgr`) も同様に `CFG_BUFFER_POOL_TABLE_NAME` を `Orch(cfgDb, tableNames)` ベースで登録し、CONFIG_DB は `SubscriberStateTable` で購読される。

## 2. buffermgr/buffermgrdyn → APPL_DB: ProducerStateTable

`BufferMgrDynamic` は CONFIG_DB の変更を `handleBufferPoolTable()` で処理し、結果を APPL_DB に書き込む。

```cpp
// sonic-swss/cfgmgr/buffermgrdyn.cpp:42-43
m_applBufferPoolTable(applDb, APP_BUFFER_POOL_TABLE_NAME),       // ProducerStateTable
m_applStateBufferPoolTable(applStateDb, APP_BUFFER_POOL_TABLE_NAME),
```

書き込みは以下の形式:

```cpp
// buffermgrdyn.cpp:2630, 2637, 885
m_applBufferPoolTable.set(pool, fvVector);  // SET: pool サイズ確定後
m_applBufferPoolTable.del(pool);            // DEL: pool 削除時
```

`ProducerStateTable` は Redis の `LPUSH <TABLE>_KEY_SET` + `HSET` によるチャネルベース通知（channel 書き込み + DB 更新の組み合わせ）を行う。

## 3. APPL_DB BUFFER_POOL_TABLE → bufferorch: ConsumerStateTable

`orchdaemon.cpp` は `APP_BUFFER_POOL_TABLE_NAME` を含む `buffer_tables` ベクタで `BufferOrch` を構築する。

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:386-394
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,   // ← APPL_DB 側
    ...
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`BufferOrch` のコンストラクタが `Orch(applDb, tableNames)` を呼ぶと `addConsumer()` が各テーブル名を `applDb`（APPL_DB、DB ID ≠ CONFIG_DB）で処理するため **`ConsumerStateTable`** が選択される。

- チャネルベース: `<TABLE>_CHANNEL` (`BUFFER_POOL_TABLE_CHANNEL`) を `SUBSCRIBE` し、`ProducerStateTable` の `LPUSH` 通知をリアルタイムで受信する。
- バッチサイズ: `gBatchSize`（`orchagent -b` オプションで調整可）。

ディスパッチは `BufferOrch::doTask(Consumer &consumer)` → `processBufferPool()` へ。

## 4. bufferorch → APPL_STATE_DB: ResponsePublisher

`bufferorch.cpp` は SAI 処理成功後に `m_publisher.publish()` で結果を APPL_STATE_DB の `BUFFER_POOL_TABLE` エントリに書き戻す。`m_publisher` は `Orch` 基底クラスの `ResponsePublisher m_publisher{"APPL_STATE_DB"}` （`orch.h:382`）。

```cpp
// sonic-swss/orchagent/bufferorch.cpp:554-555
// xoff (SHP) が有効な場合のみ結果を publish
if (!xoff.empty())
{
    vector<FieldValueTuple> fvs;
    fvs.emplace_back("xoff", xoff);
    m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, object_name, fvs,
                        ReturnCode(SAI_STATUS_SUCCESS), true);
}

// bufferorch.cpp:588-589
// DEL 操作完了後
m_publisher.publish(APP_BUFFER_POOL_TABLE_NAME, object_name, fvs,
                    ReturnCode(SAI_STATUS_SUCCESS), true);
```

`ResponsePublisher::publish()` は:
1. Redis channel への `NotificationProducer` 経由 PUBLISH（処理結果通知）
2. APPL_STATE_DB への `HSET` / `DEL`（状態書き込み）

の両方を実行する（`response_publisher.h:44-50`）。

xoff が空（SHP 無効）の通常 SET 操作では `m_publisher.publish()` は**呼ばれない**（`bufferorch.cpp:549-556`）。

## 5. keyspace 通知パターン

| Redis 通知 | 受信プロセス |
|-----------|-------------|
| `__keyspace@4__:BUFFER_POOL\|ingress_lossless_pool` `hset` | `buffermgrd(yn)` の `SubscriberStateTable` |
| `__keyspace@4__:BUFFER_POOL\|egress_lossy_pool` `del` | `buffermgrd(yn)` の `SubscriberStateTable` |
| `BUFFER_POOL_TABLE_CHANNEL` PUBLISH (`APP_BUFFER_POOL_TABLE`) | `bufferorch` の `ConsumerStateTable` |

## 6. データフロー全体サマリ

```
CONFIG_DB:BUFFER_POOL
  │  keyspace通知 (__keyspace@4__:BUFFER_POOL|*)
  ↓  SubscriberStateTable (buffermgrd/buffermgrdyn)
buffermgrdyn: handleBufferPoolTable()
  │  ProducerStateTable.set() / LPUSH + HSET
  ↓  BUFFER_POOL_TABLE_CHANNEL 通知
APPL_DB:BUFFER_POOL_TABLE
  │  ConsumerStateTable (bufferorch)
  ↓  doTask() → processBufferPool()
SAI: sai_buffer_api->create/set/remove_buffer_pool()
  │  (xoff 非空かつ SET / DEL 完了時のみ)
  ↓  ResponsePublisher.publish()
APPL_STATE_DB:BUFFER_POOL_TABLE  (xoff フィールドのみ書き戻し)
```

## 7. ConsumerStateTable 非使用の確認 (CONFIG_DB 側)

CONFIG_DB の `BUFFER_POOL` は `orch.cpp:1188` の DB ID 分岐により `SubscriberStateTable` が選択される。`ConsumerStateTable`（channel ベース）は **APPL_DB 側のみ**に使用される。`NotificationProducer` による CONFIG_DB への明示的 PUBLISH は行われない。

## 8. Evidence サマリ

- `sonic-swss/cfgmgr/buffermgrd.cpp` L174-187 — `buffer_table_connectors` 構築と `BufferMgrDynamic` 生成
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` DB ID 分岐
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L31-58, L443, L2630, L2637, L885 — コンストラクタ、ハンドラ登録、APPL_DB 書き込み
- `sonic-swss/cfgmgr/buffermgr.cpp` L21-33, L481 — static model のテーブル購読
- `sonic-swss/orchagent/orchdaemon.cpp` L387-394 — `gBufferOrch` 構築
- `sonic-swss/orchagent/bufferorch.cpp` L549-555, L588-589 — `m_publisher.publish()` 呼び出し条件
- `sonic-swss/orchagent/orch.h` L382 — `ResponsePublisher m_publisher{"APPL_STATE_DB"}`
- `sonic-swss/orchagent/response_publisher.h` L44-50 — `publish()` シグネチャ
