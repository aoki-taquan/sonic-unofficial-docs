# BUFFER_PROFILE テーブル — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `BUFFER_PROFILE` テーブル（スキーマ定数: `CFG_BUFFER_PROFILE_TABLE_NAME`）および APPL_DB の `BUFFER_PROFILE_TABLE`（`APP_BUFFER_PROFILE_TABLE_NAME`）。

ソース確認: `sonic-swss/cfgmgr/buffermgrdyn.cpp`、`cfgmgr/buffermgr.cpp`、`cfgmgr/buffermgrd.cpp`、`orchagent/bufferorch.cpp`、`orchagent/orchdaemon.cpp`、`orchagent/orch.cpp`（`addConsumer`）、`orchagent/response_publisher.h`。

## 1. CONFIG_DB → buffermgr/buffermgrdyn: SubscriberStateTable

`buffermgrd.cpp` の dynamic buffer model パスでは `CFG_BUFFER_PROFILE_TABLE_NAME` を含む `vector<TableConnector>` を構築し `BufferMgrDynamic` コンストラクタに渡す。

```cpp
// sonic-swss/cfgmgr/buffermgrd.cpp:174-187
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),   // ← BUFFER_PROFILE
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_QUEUE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER),
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME),
};
cfgOrchList.emplace_back(new BufferMgrDynamic(&cfgDb, &stateDb, &applDb, &applStateDb, buffer_table_connectors, ...));
```

`BufferMgrDynamic` は `Orch(tables)` を継承し、`Orch::addConsumer()` が各 `TableConnector` を処理する。

```cpp
// sonic-swss/orchagent/orch.cpp:1186-1196
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

CONFIG_DB は DB ID チェックにマッチするため **`SubscriberStateTable`** が選択される。これは Redis の **keyspace 通知**（`__keyspace@4__:BUFFER_PROFILE|*` の `PSUBSCRIBE`）を購読し、変更検知後に `HGETALL` で値を再取得して `pops()` で `(key, op, fvs)` タプルを返す。

- バッチサイズ: `DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`）。`cfgmgrd -b` フラグは `gBatchSize` のみ変更するため、CONFIG_DB 側には影響しない。
- TTL: CONFIG_DB の全エントリで未設定（永続前提）。

static buffer model（`BufferMgr`）も同様に `CFG_BUFFER_PROFILE_TABLE_NAME` を `Orch(cfgDb, tableNames)` ベースで登録し、CONFIG_DB は `SubscriberStateTable` で購読される（`buffermgr.cpp:21-22`、`buffermgrd.cpp:191-204`）。

ハンドラへのディスパッチ: `buffermgrdyn.cpp:444` で `CFG_BUFFER_PROFILE_TABLE_NAME` を `handleBufferProfileTable()` にマッピング。

## 2. buffermgr/buffermgrdyn → APPL_DB: ProducerStateTable

`BufferMgrDynamic` は CONFIG_DB の変更を `handleBufferProfileTable()` で処理し、結果を APPL_DB に書き込む。

```cpp
// sonic-swss/cfgmgr/buffermgrdyn.cpp:44-45
m_applBufferProfileTable(applDb, APP_BUFFER_PROFILE_TABLE_NAME),       // ProducerStateTable
m_applStateBufferProfileTable(applStateDb, APP_BUFFER_PROFILE_TABLE_NAME),
```

書き込みは `updateBufferProfileToDb()` 経由で行われる:

```cpp
// buffermgrdyn.cpp:890-922 (updateBufferProfileToDb)
m_applBufferProfileTable.set(profile_name, fvVector);  // SET: プロファイル確定後
m_applBufferProfileTable.del(profile_name);            // DEL: プロファイル削除時
```

`ProducerStateTable` は Redis の `LPUSH <TABLE>_KEY_SET` + `HSET` によるチャネルベース通知（channel 書き込み + DB 更新の組み合わせ）を行う。

注意: `headroom_type=dynamic` かつポート未参照のプロファイルは APPL_DB への書き込みが **保留** される（`buffermgrdyn.cpp:2820`）。ポート参照が確定してから書き込まれる。

## 3. APPL_DB BUFFER_PROFILE_TABLE → bufferorch: ConsumerStateTable

`orchdaemon.cpp` は `APP_BUFFER_PROFILE_TABLE_NAME` を含む `buffer_tables` ベクタで `BufferOrch` を構築する。

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:386-394
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,
    APP_BUFFER_PROFILE_TABLE_NAME,   // ← APPL_DB 側
    APP_BUFFER_QUEUE_TABLE_NAME,
    APP_BUFFER_PG_TABLE_NAME,
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`BufferOrch` のコンストラクタが `Orch(applDb, tableNames)` を呼ぶと `addConsumer()` が各テーブル名を `applDb`（APPL_DB、DB ID ≠ CONFIG_DB）で処理するため **`ConsumerStateTable`** が選択される。

- チャネルベース: `<TABLE>_CHANNEL`（`BUFFER_PROFILE_TABLE_CHANNEL`）を `SUBSCRIBE` し、`ProducerStateTable` の `LPUSH` 通知をリアルタイムで受信する。
- バッチサイズ: `gBatchSize`（`orchagent -b` オプションで調整可）。

ディスパッチは `BufferOrch::doTask(Consumer &consumer)` → `processBufferProfile()` へ（`bufferorch.cpp:74`）。

## 4. bufferorch → APPL_STATE_DB: ResponsePublisher

`bufferorch.cpp` は SAI 処理成功後に `m_publisher.publish()` で結果を APPL_STATE_DB の `BUFFER_PROFILE_TABLE` エントリに書き戻す。`m_publisher` は `Orch` 基底クラスの `ResponsePublisher m_publisher{"APPL_STATE_DB"}`（`orch.h:382`）。

```cpp
// sonic-swss/orchagent/bufferorch.cpp:831-832
// SET 操作成功後（lossless プロファイル）
SWSS_LOG_INFO("Publishing the result after applying lossless buffer profile %s to SAI", object_name.c_str());
m_publisher.publish(APP_BUFFER_PROFILE_TABLE_NAME, object_name, fvs, ReturnCode(SAI_STATUS_SUCCESS), true);

// bufferorch.cpp:879-880
// DEL 操作完了後
m_publisher.publish(APP_BUFFER_PROFILE_TABLE_NAME, object_name, fvs, ReturnCode(SAI_STATUS_SUCCESS), true);
```

`ResponsePublisher::publish()` は:
1. Redis channel への `NotificationProducer` 経由 PUBLISH（処理結果通知）
2. APPL_STATE_DB への `HSET` / `DEL`（状態書き込み）

の両方を実行する（`response_publisher.h:44-50`）。

## 5. keyspace 通知パターン

| Redis 通知 | 受信プロセス |
|-----------|-------------|
| `__keyspace@4__:BUFFER_PROFILE\|pg_lossless_100000_5m_profile` `hset` | `buffermgrd(yn)` の `SubscriberStateTable` |
| `__keyspace@4__:BUFFER_PROFILE\|pg_lossless_100000_5m_profile` `del` | `buffermgrd(yn)` の `SubscriberStateTable` |
| `BUFFER_PROFILE_TABLE_CHANNEL` PUBLISH（APPL_DB） | `bufferorch` の `ConsumerStateTable` |

## 6. データフロー全体サマリ

```
CONFIG_DB:BUFFER_PROFILE
  │  keyspace通知 (__keyspace@4__:BUFFER_PROFILE|*)
  ↓  SubscriberStateTable (buffermgrd/buffermgrdyn)
buffermgrdyn: handleBufferProfileTable()
  │  updateBufferProfileToDb(): ProducerStateTable.set() / LPUSH + HSET
  │  ※ headroom_type=dynamic かつポート未参照時は保留
  ↓  BUFFER_PROFILE_TABLE_CHANNEL 通知
APPL_DB:BUFFER_PROFILE_TABLE
  │  ConsumerStateTable (bufferorch)
  ↓  doTask() → processBufferProfile()
SAI: sai_buffer_api->sai_create_buffer_profile()
  │  SET/DEL 完了時
  ↓  ResponsePublisher.publish()
APPL_STATE_DB:BUFFER_PROFILE_TABLE  (全フィールドを書き戻し)
```

## 7. ConsumerStateTable 非使用の確認 (CONFIG_DB 側)

CONFIG_DB の `BUFFER_PROFILE` は `orch.cpp:1188` の DB ID 分岐により `SubscriberStateTable` が選択される。`ConsumerStateTable`（channel ベース）は **APPL_DB 側のみ**に使用される。`NotificationProducer` による CONFIG_DB への明示的 PUBLISH は行われない。

## 8. Evidence サマリ

- `sonic-swss/cfgmgr/buffermgrd.cpp` L174-187 — `buffer_table_connectors` 構築と `BufferMgrDynamic` 生成
- `sonic-swss/cfgmgr/buffermgrd.cpp` L191-204 — static model の `CFG_BUFFER_PROFILE_TABLE_NAME` 登録
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` DB ID 分岐
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L31-58, L444, L890-922, L2820 — コンストラクタ、ハンドラ登録、APPL_DB 書き込み、defer 条件
- `sonic-swss/cfgmgr/buffermgr.cpp` L21-33 — static model のテーブル購読
- `sonic-swss/orchagent/orchdaemon.cpp` L386-394 — `gBufferOrch` 構築
- `sonic-swss/orchagent/bufferorch.cpp` L74 — `APP_BUFFER_PROFILE_TABLE_NAME` ハンドラ登録
- `sonic-swss/orchagent/bufferorch.cpp` L831-832, L879-880 — `m_publisher.publish()` 呼び出し
- `sonic-swss/orchagent/orch.h` L382 — `ResponsePublisher m_publisher{"APPL_STATE_DB"}`
- `sonic-swss/orchagent/response_publisher.h` L44-50 — `publish()` シグネチャ
