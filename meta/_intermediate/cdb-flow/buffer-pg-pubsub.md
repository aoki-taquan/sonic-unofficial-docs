# BUFFER_PG 通信メカニズム調査 (Phase G)

調査対象ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/cfgmgr/buffermgrd.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 1. CONFIG_DB → buffermgr/buffermgrdyn

### 動的モード (BufferMgrDynamic)

`buffermgrd.cpp:174-187` で `buffer_table_connectors` ベクタを構築し、`CFG_BUFFER_PG_TABLE_NAME` を含む `TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME)` を追加する。

`BufferMgrDynamic` のコンストラクタは `Orch(tables)` を呼び出し（`buffermgrdyn.cpp:32`）、`Orch` 基底クラスが各 `TableConnector` を `SubscriberStateTable` としてラップし Redis keyspace notification で受信待ちする。

ハンドラ登録:
- `buffermgrdyn.cpp:446`: `m_bufferTableHandlerMap.insert(buffer_handler_pair(CFG_BUFFER_PG_TABLE_NAME, &BufferMgrDynamic::handleBufferPgTable))`
- `buffermgrdyn.cpp:454`: シングルポートハンドラ `handleSingleBufferPgEntry`

### 静的モード (BufferMgr)

`buffermgrd.cpp:191-203` で `cfg_buffer_tables` ベクタに `CFG_BUFFER_PG_TABLE_NAME` を追加して `BufferMgr` を生成する。

`buffermgr.cpp:22`: `Orch(cfgDb, tableNames)` コンストラクタ。

`buffermgr.cpp:493`: `doTask()` 内で `table_name == CFG_BUFFER_PG_TABLE_NAME` を判定して処理分岐。

## 2. APPL_DB → BufferOrch

`orchdaemon.cpp:386-394`:
```cpp
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,
    APP_BUFFER_PROFILE_TABLE_NAME,
    APP_BUFFER_QUEUE_TABLE_NAME,
    APP_BUFFER_PG_TABLE_NAME,      // ← ここが BUFFER_PG
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`bufferorch.cpp:54`: `Orch(applDb, tableNames)` — `Orch` 基底クラスが `ConsumerStateTable` を `applDb` に対して生成し BUFFER_PG_TABLE 変更を受信する。

`bufferorch.cpp:76`: `m_bufferHandlerMap.insert(buffer_handler_pair(APP_BUFFER_PG_TABLE_NAME, &BufferOrch::processPriorityGroup))`
`bufferorch.cpp:82`: flush ハンドラ `processPriorityGroupBulk`

## 3. 書き込み方向

`buffermgrdyn.cpp:46`: `m_applBufferObjectTables{ProducerStateTable(applDb, APP_BUFFER_PG_TABLE_NAME), ...}` — APPL_DB への書き込みは `ProducerStateTable` 経由。

`buffermgr.cpp:30`: `m_applBufferPgTable(applDb, APP_BUFFER_PG_TABLE_NAME)` — 静的モードも同様に `ProducerStateTable`。

## subscribe 方式サマリ

| 区間 | 購読方式 | クラス | evidence |
|---|---|---|---|
| CONFIG_DB BUFFER_PG → buffermgrdyn | `SubscriberStateTable` (Orch 基底) | `BufferMgrDynamic` | `buffermgrd.cpp:179`, `buffermgrdyn.cpp:32` |
| CONFIG_DB BUFFER_PG → buffermgr | `SubscriberStateTable` (Orch 基底) | `BufferMgr` | `buffermgrd.cpp:196`, `buffermgr.cpp:22` |
| APPL_DB BUFFER_PG_TABLE → BufferOrch | `ConsumerStateTable` (Orch 基底) | `BufferOrch` | `orchdaemon.cpp:390`, `bufferorch.cpp:54` |
| buffermgr → APPL_DB BUFFER_PG_TABLE | `ProducerStateTable` (書き込み) | `BufferMgrDynamic` / `BufferMgr` | `buffermgrdyn.cpp:46`, `buffermgr.cpp:30` |
