# BUFFER_PORT_INGRESS_PROFILE_LIST — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/buffer-port-ingress-profile-list.md`

## 1. subscribe 経路の全体像

`BUFFER_PORT_INGRESS_PROFILE_LIST` テーブルは **2 段階中継**:

```
CONFIG_DB → buffermgrd (SubscriberStateTable) → APPL_DB → BufferOrch (ConsumerStateTable) → SAI
```

途中で `ResponsePublisher` による上り ack は **このテーブルには存在しない**（BUFFER_POOL / BUFFER_PROFILE のみ ack あり）。

## 2. CONFIG_DB → buffermgrd (SubscriberStateTable)

`buffermgrdyn` (dynamic model) は `Orch(tables)` 基底クラスを通じて CONFIG_DB テーブルを購読する。

`sonic-swss/cfgmgr/buffermgrdyn.cpp` L447:

```cpp
m_bufferTableHandlerMap.insert(buffer_handler_pair(
    CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferMgrDynamic::handleBufferPortIngressProfileListTable));
```

`Orch::addConsumer()` (`orch.cpp:1186-1196`) で CONFIG_DB の場合:

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
{
    addExecutor(new Consumer(
        new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri),
        this, tableName));
}
```

→ `BUFFER_PORT_INGRESS_PROFILE_LIST` に対して **`SubscriberStateTable`** を生成。

`SubscriberStateTable` は Redis keyspace notification:

```
PSUBSCRIBE __keyspace@{config_db_id}__:BUFFER_PORT_INGRESS_PROFILE_LIST|*
```

を発行し、SET / DEL のたびに `pops()` で変化エントリを取得する。

### ハンドラ登録 (L455)

```cpp
m_bufferSingleItemHandlerMap.insert(buffer_single_item_handler_pair(
    CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferMgrDynamic::handleSingleBufferPortIngressProfileListEntry));
```

`handleBufferPortIngressProfileListTable` は `handleBufferObjectTables(tuple, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME, false)` に委譲し (`buffermgrdyn.cpp:3566`)、コンマ区切りポートキーを分解して各ポートに `handleSingleBufferPortIngressProfileListEntry` を呼ぶ (`L3536-3547`)。

### static model (`buffermgr.cpp`)

static model は `BUFFER_PORT_INGRESS_PROFILE_LIST` を同様に SubscriberStateTable で購読し CONFIG_DB 値をそのまま APPL_DB に書く（direction / profile 存在検証なし）。ただし `DEVICE_METADATA.buffer_model == "dynamic"` の環境では `L476-480` の早期 return によりスキップされる。

## 3. buffermgrd → APPL_DB (ProducerStateTable)

`buffermgrdyn.cpp` L47:

```cpp
m_applBufferProfileListTables{
    ProducerStateTable(applDb, APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    ProducerStateTable(applDb, APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME)},
```

`APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` = `"BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE"` に **`ProducerStateTable`** で書き込む。

`ProducerStateTable::set()` は key を `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_KEY_SET` ハッシュに格納し、`BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL@0` に PUBLISH する。

## 4. APPL_DB → BufferOrch (ConsumerStateTable)

`sonic-swss/orchagent/orchdaemon.cpp` L385-L394（抜粋）:

```cpp
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,
    APP_BUFFER_PROFILE_TABLE_NAME,
    APP_BUFFER_QUEUE_TABLE_NAME,
    APP_BUFFER_PG_TABLE_NAME,
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,   // ← ここで登録
    APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`BufferOrch::BufferOrch` は `Orch(applDb, tableNames)` を呼ぶ (`bufferorch.cpp:53`)。APPL_DB (DB id = 0) は `addConsumer()` の `else` 分岐に落ちて **`ConsumerStateTable`** を生成する。

```
SUBSCRIBE BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL@0
```

`ConsumerStateTable::pops()` が Lua SCRIPT で `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_KEY_SET` からエントリを取り出す（最大 `DEFAULT_POP_BATCH_SIZE = 128` keys/回）。

### ハンドラ登録 (`bufferorch.cpp` L77/L80)

```cpp
m_bufferHandlerMap.insert(buffer_handler_pair(
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferOrch::processIngressBufferProfileList));
m_bufferFlushHandlerMap.insert(buffer_flush_handler_pair(
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferOrch::processIngressBufferProfileListBulk));
```

`processIngressBufferProfileList` → SAI `sai_port_api` `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` を更新。Bulk 経路（`processIngressBufferProfileListBulk`）では `sai_port_api->set_ports_attribute()` を使い複数ポートを一括で SET する。

## 5. Bulk SET の詳細

`bufferorch.cpp:1796-1848` (`processIngressBufferProfileListBulk`):

- DEL → SET の順でループ（DEL 優先順序）。
- `m_portIngressBufferProfileListBulk[op]` に蓄積されたタスクを取り出し、oid/attr/status 配列を構築。
- `sai_port_api->set_ports_attribute(count, oids, attrs, SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR, statuses)` を呼ぶ。
- 部分失敗ポートは `consumer.m_toSync` に再投入されリトライ。

## 6. ResponsePublisher — BUFFER_PORT_INGRESS_PROFILE_LIST には上り ack なし

`orch.h` L382 に `ResponsePublisher m_publisher{"APPL_STATE_DB"}` を持つが、`bufferorch.cpp` の `processIngressBufferProfileList` / `processIngressBufferProfileListBulk` は `m_publisher.publish()` を呼ばない。

ResponsePublisher が使われるのは **BUFFER_POOL** (L555, L589) と **BUFFER_PROFILE** (L832, L880) のみ。

## 7. doTask と drain 順序

`bufferorch.cpp:2040-2073`:

```cpp
void BufferOrch::doTask()
{
    auto pool_consumer    = getExecutor(APP_BUFFER_POOL_TABLE_NAME);
    auto profile_consumer = getExecutor(APP_BUFFER_PROFILE_TABLE_NAME);
    pool_consumer->drain();
    profile_consumer->drain();
    for (auto &it : m_consumerMap) {
        if (consumer == profile_consumer || consumer == pool_consumer) continue;
        consumer->drain();   // ← BUFFER_PORT_INGRESS_PROFILE_LIST もここで処理
    }
}
```

`BUFFER_PORT_INGRESS_PROFILE_LIST` は pool / profile の後に drain される（参照依存順）。

## 8. PUBSUB チャンネルまとめ

| 区間 | 方式 | チャンネル/パターン |
|------|------|---------------------|
| CONFIG_DB → buffermgrd | `SubscriberStateTable` | `PSUBSCRIBE __keyspace@{cfg_db_id}__:BUFFER_PORT_INGRESS_PROFILE_LIST\|*` |
| buffermgrd → APPL_DB | `ProducerStateTable` | `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL@0` に PUBLISH |
| APPL_DB → BufferOrch | `ConsumerStateTable` | `SUBSCRIBE BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL@0` |
| BufferOrch → APPL_STATE_DB | `ResponsePublisher` | **なし**（POOL/PROFILE のみ） |

## 9. 参照

- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L42-L51, L447-L455, L3536-3547, L3566
- `sonic-swss/cfgmgr/buffermgrd.cpp` L174-L187
- `sonic-swss/orchagent/bufferorch.cpp` L40, L53-L80, L1796-1848, L2040-L2073
- `sonic-swss/orchagent/orchdaemon.cpp` L385-L394
- `sonic-swss/orchagent/orch.cpp` L97-L103, L1186-L1196
- `sonic-swss/orchagent/orch.h` L382
