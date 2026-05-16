# buffer-queue: Phase G — 通信メカニズム (pubsub) スキャンノート

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`

## 購読チェーン概要

```
CONFIG_DB (BUFFER_QUEUE)
  └─ SubscriberStateTable (Consumer) ← buffermgrd (dynamic)
       └─ ProducerStateTable → APPL_DB (APP_BUFFER_QUEUE_TABLE)
            └─ ConsumerStateTable (Consumer) ← orchagent BufferOrch
                 └─ sai_queue_api → ASIC_DB (SAI 経由)
```

## 1. CONFIG_DB 購読 (buffermgrd)

### 購読方式

`BufferMgrDynamic` は `Orch(tables)` 基底クラス経由で **SubscriberStateTable** として CONFIG_DB の複数テーブルを購読する。

`buffermgrd.cpp:174-186` にて `vector<TableConnector>` を構築し `BufferMgrDynamic` コンストラクタに渡す:

```cpp
// buffermgrd.cpp:174-186
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_QUEUE_TABLE_NAME),   // ← BUFFER_QUEUE
    TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER),
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME),
};
```

`CFG_BUFFER_QUEUE_TABLE_NAME` = `"BUFFER_QUEUE"` が CONFIG_DB に対して SubscriberStateTable として登録される。

### ハンドラ登録

`initTableHandlerMap()` にて:
- `CFG_BUFFER_QUEUE_TABLE_NAME` → `handleBufferQueueTable` (複数ポート対応)
- `CFG_BUFFER_QUEUE_TABLE_NAME` → `handleSingleBufferQueueEntry` (シングルエントリ)

`handleBufferQueueTable` は `handleBufferObjectTables(tuple, CFG_BUFFER_QUEUE_TABLE_NAME, true)` に委譲（`keyWithIds=true` = queue range 必須）。
evidence: `buffermgrdyn.cpp:445, 453`

### 受信→APPL_DB 書き込み

`doTask(Consumer&)` が consumer の `m_toSync` を処理し（`buffermgrdyn.cpp:3574`）、
最終的に `updateBufferObjectToDb(key, profile, add, BUFFER_QUEUE)` を呼び出す。

`updateBufferObjectToDb` は `m_applBufferObjectTables[BUFFER_QUEUE]` (= `ProducerStateTable(applDb, APP_BUFFER_QUEUE_TABLE_NAME)`) を介して APPL_DB に書き込む。
evidence: `buffermgrdyn.cpp:926-940, 46`

## 2. APPL_DB 購読 (orchagent BufferOrch)

### 購読方式

`BufferOrch` は `Orch(applDb, tableNames)` 基底クラス経由で APPL_DB テーブルを **ConsumerStateTable** として購読する。

`orchdaemon.cpp:386-394` にて `vector<string> buffer_tables` を構築し `BufferOrch` コンストラクタに渡す:

```cpp
// orchdaemon.cpp:386-394
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,
    APP_BUFFER_PROFILE_TABLE_NAME,
    APP_BUFFER_QUEUE_TABLE_NAME,   // ← APP_BUFFER_QUEUE_TABLE
    APP_BUFFER_PG_TABLE_NAME,
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`APP_BUFFER_QUEUE_TABLE_NAME` = `"APP_BUFFER_QUEUE_TABLE"` が APPL_DB に対して ConsumerStateTable として登録される。

### ハンドラ登録

`initTableHandlers()` にて:
- `APP_BUFFER_QUEUE_TABLE_NAME` → `processQueue` (per-entry)
- `APP_BUFFER_QUEUE_TABLE_NAME` → `processQueueBulk` (bulk flush)

evidence: `bufferorch.cpp:75, 83`

### 受信→SAI 書き込み

`doTask(Consumer&)` (`bufferorch.cpp:2075`) が `processQueue` を呼び出し、
`sai_queue_api->set_queues_attribute()` (bulk API) 経由で ASIC_DB（syncd 経由の SAI）へ書き込む。
SAI 属性: `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID`。
evidence: `bufferorch.cpp:1021, 1269`

## 3. ASIC_DB notification

BUFFER_QUEUE に関して bufferorch が ASIC_DB からの通知を直接購読する仕組みは検出されない。
SAI への書き込みは syncd が ASIC_DB に転送し結果をオペレーションで受け取る（通常フロー）。

BUFFER_POOL に関しては `SubscriberStateTable` が `BUFFER_POOL_WATERMARK` キースペースを購読しており
watermark 更新を受信するが、これは BUFFER_QUEUE のフローとは無関係。
evidence: `bufferorch.cpp:290`

## 4. 購読テーブル一覧

| デーモン | DB | テーブル名 | 方式 | evidence |
|---|---|---|---|---|
| `buffermgrd` (dynamic) | CONFIG_DB | `BUFFER_QUEUE` | SubscriberStateTable (TableConnector 経由) | `buffermgrd.cpp:180` |
| `buffermgrd` (static) | CONFIG_DB | `BUFFER_QUEUE` | SubscriberStateTable | `buffermgr.cpp:499` |
| `orchagent` (BufferOrch) | APPL_DB | `APP_BUFFER_QUEUE_TABLE` | ConsumerStateTable (Orch 基底) | `orchdaemon.cpp:389` |

## 5. 書き込みテーブル一覧

| デーモン | DB | テーブル名 | 方式 | evidence |
|---|---|---|---|---|
| `buffermgrd` (dynamic) | APPL_DB | `APP_BUFFER_QUEUE_TABLE` | ProducerStateTable | `buffermgrdyn.cpp:46` |
| `orchagent` (BufferOrch) | ASIC_DB | SAI queue buffer attr | sai_queue_api (bulk SET) | `bufferorch.cpp:1269` |
