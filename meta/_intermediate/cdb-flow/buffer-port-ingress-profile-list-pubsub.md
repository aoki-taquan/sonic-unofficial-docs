# BUFFER_PORT_INGRESS_PROFILE_LIST — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BUFFER_PORT_INGRESS_PROFILE_LIST` テーブル。
ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`

## 1. CONFIG_DB 購読 — `SubscriberStateTable` (TableConnector 経由)

`buffermgrd`（dynamic モード）は `swsscommon` の `Orch` 基底クラスを使用し、
`TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME)` で登録された
`SubscriberStateTable` を介して CONFIG_DB を購読する。

```cpp
// sonic-swss/cfgmgr/buffermgrd.cpp:181
vector<TableConnector> buffer_table_connectors = {
    ...
    TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME),
    ...
};
cfgOrchList.emplace_back(new BufferMgrDynamic(&cfgDb, &stateDb, &applDb, &applStateDb,
                          buffer_table_connectors, ...));
// buffermgrdyn.cpp:32
BufferMgrDynamic::BufferMgrDynamic(..., const vector<TableConnector> &tables, ...)
    : Orch(tables), ...   // Orch が各 TableConnector を SubscriberStateTable として登録
```

- `SubscriberStateTable` は Redis の **keyspace 通知**（`__keyspace@<dbId>__:BUFFER_PORT_INGRESS_PROFILE_LIST|*`）を PSUBSCRIBE し、`SET` / `DEL` 操作の変更を `KeyOpFieldsValuesTuple` として受信する。
- CONFIG_DB は `sonic-db-cli CONFIG_DB HSET ...` や `sonic-cfggen` の `HSET` で書かれ、明示的な `PUBLISH` は行わない。

## 2. ハンドラ登録

```cpp
// buffermgrdyn.cpp:447
m_bufferTableHandlerMap.insert(buffer_handler_pair(
    CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferMgrDynamic::handleBufferPortIngressProfileListTable));
// buffermgrdyn.cpp:455
m_bufferSingleItemHandlerMap.insert(buffer_single_item_handler_pair(
    CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferMgrDynamic::handleSingleBufferPortIngressProfileListEntry));
```

`handleBufferPortIngressProfileListTable` は `handleBufferObjectTables(tuple, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME, false)` に委譲する（`buffermgrdyn.cpp:3566`）。

## 3. CONFIG_DB → APPL_DB 転送 — `ProducerStateTable`

`buffermgrdyn` は APPL_DB への書き込みに `ProducerStateTable` を使用する。
`ProducerStateTable` は **channel ベース**（`PUBLISH` + Redis Hash）であり、orchagent の
`ConsumerStateTable` へリアルタイムに通知が届く。

```cpp
// buffermgrdyn.cpp:47
m_applBufferProfileListTables{
    ProducerStateTable(applDb, APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    ProducerStateTable(applDb, APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME)
};
// buffermgrdyn.cpp:3384
ProducerStateTable &appTable = m_applBufferProfileListTables[dir]; // dir=BUFFER_INGRESS
appTable.set(port, fvVector);   // SET: profile_list をポートに紐付け
// or
appTable.del(port);             // DEL: ポートエントリ削除
```

`ProducerStateTable.set()` は内部で Redis MULTI/EXEC を用いて Hash(`BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE:Ethernet0`) の `HSET` と channel (`BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL`) への `PUBLISH` を原子的に実行する。

## 4. APPL_DB 購読 — `ConsumerStateTable` (orchagent)

`BufferOrch` は `Orch(applDb, tableNames)` で初期化され、
`APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` を `ConsumerStateTable` として購読する。

```cpp
// bufferorch.cpp:53-54
BufferOrch::BufferOrch(DBConnector *applDb, ..., vector<string> &tableNames)
    : Orch(applDb, tableNames),  // ConsumerStateTable が channel を SUBSCRIBE
// bufferorch.cpp:77,80
m_bufferHandlerMap.insert(...APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferOrch::processIngressBufferProfileList);
m_bufferFlushHandlerMap.insert(...APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    &BufferOrch::processIngressBufferProfileListBulk);
```

`ConsumerStateTable` は `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL` の `SUBSCRIBE` を行い、
`PUBLISH` 通知を受けたときに対応する Hash からフィールドを `HGETALL` して
`KeyOpFieldsValuesTuple` に変換し、`doTask()` に渡す。

## 5. Bulk Set 経路 — `sai_port_api->set_ports_attribute`

orchagent は個別ポート SET ではなく、複数ポートをまとめて SAI Bulk API で処理する。

```cpp
// bufferorch.cpp:1796-1848  processIngressBufferProfileListBulk
sai_port_api->set_ports_attribute(
    objectCount,
    oids.data(),           // ポート OID 配列
    attrs.data(),          // SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST 配列
    SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR,
    statuses.data());
```

- `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR`: 部分失敗を許容し、失敗ポートは `task_need_retry` 再投入（`bufferorch.cpp:1840-1843`）。
- 属性 ID: `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST`（`bufferorch.cpp:1675`）。
- Bulk flush は `processIngressBufferProfileListBulk` が `m_portIngressBufferProfileListBulk[op]` バッファを使用し、通常の `doTask()` ループ後にまとめて実行される。

## 6. メッセージフロー全体像

```
CONFIG_DB
  BUFFER_PORT_INGRESS_PROFILE_LIST|<port>
        │  keyspace 通知 (SubscriberStateTable / Orch)
        ▼
  buffermgrd (BufferMgrDynamic)
    handleBufferPortIngressProfileListTable()
      → handleBufferObjectTables()
        → handleSingleBufferPortIngressProfileListEntry()
              [バリデーション: プロファイル存在確認, 方向チェック, trim 禁止]
        │  ProducerStateTable.set()
        │  (HSET + PUBLISH on BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL)
        ▼
  APPL_DB
    BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE:<port>
        │  SUBSCRIBE (ConsumerStateTable / Orch)
        ▼
  orchagent (BufferOrch)
    processIngressBufferProfileList()    ← 個別 SET/DEL 処理 + キャッシュ更新
    processIngressBufferProfileListBulk() ← Bulk SAI 呼び出し
        │  sai_port_api->set_ports_attribute() (Bulk)
        ▼
  syncd → SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST
```

## 7. 静的バッファモデル (`buffermgr.cpp`) の差異

static モードでは `BufferMgr` が `CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME` を
`ConsumerStateTable`（cfgDb）として購読し、バリデーションなしに直接 APPL_DB へ転送する。
dynamic モードの方向チェック・trim チェックは行われない（`buffermgr.cpp:doBufferTableTask`）。

## 8. 参考行番号

- `sonic-swss/cfgmgr/buffermgrd.cpp`:174-187（TableConnector 配列構築）、197-203（static モード）
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`:31-58（コンストラクタ・ProducerStateTable 初期化）、447,455（ハンドラ登録）、3383-3437（APPL_DB 書き込み）、3566（委譲）
- `sonic-swss/orchagent/bufferorch.cpp`:53-84（コンストラクタ・ConsumerStateTable 登録）、1675（SAI 属性 ID）、1695-1754（processIngressBufferProfileList）、1796-1848（Bulk flush）
