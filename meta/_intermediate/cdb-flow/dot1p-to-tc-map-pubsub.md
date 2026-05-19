# DOT1P_TO_TC_MAP — 通信メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/orch.cpp`

## 1. 購読方式

`QosOrch` は `orchdaemon.cpp:367-384` で `qos_tables` ベクタの一員として
`CFG_DOT1P_TO_TC_MAP_TABLE_NAME` を指定され、`new QosOrch(m_configDb, qos_tables)` に渡される。

基底 `Orch(db, tableNames)` (orch.cpp:97-101) が各テーブル名を `addConsumer(db, it)` に渡す。
`addConsumer()` は `db->getDbId() == CONFIG_DB` 判定で **`swss::SubscriberStateTable`** を選択する
(orch.cpp:1186-1190)。

`SubscriberStateTable` は Redis keyspace 通知
`__keyspace@<dbId>__:DOT1P_TO_TC_MAP|*` を **`PSUBSCRIBE`** で購読し、
通知受信後に `HGETALL` で値を再取得して `(key, op, fvs)` タプルを返す。
バッチサイズは `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`（固定、`gBatchSize` 影響なし）。

## 2. ハンドラ登録とディスパッチ

```
orchdaemon.cpp:372  qos_tables[4] に CFG_DOT1P_TO_TC_MAP_TABLE_NAME を追加
qosorch.cpp:1331    initTableHandlers() で
                     m_qos_handler_map[CFG_DOT1P_TO_TC_MAP_TABLE_NAME]
                       = &QosOrch::handleDot1pToTcTable を登録
qosorch.cpp:2231-2251  QosOrch::doTask() が PORT_QOS_MAP / QUEUE より先に
                        DOT1P_TO_TC_MAP を drain（マップ先行登録を保証）
qosorch.cpp:2254-2295  QosOrch::doTask(Consumer&) がハンドラ関数ポインタ経由でディスパッチ
```

`handleDot1pToTcTable()` → `Dot1pToTcMapHandler::processWorkItem()`
→ `Dot1pToTcMapHandler::convertFieldValuesToAttributes()`
→ `sai_qos_map_api->create_qos_map()` / `set_qos_map_attribute()` / `remove_qos_map()`

## 3. doTask ドレイン順序

`QosOrch::doTask()` (qosorch.cpp:2231-2251) は明示的な drain 順序制御を持つ:

1. PORT_QOS_MAP / QUEUE **以外** の全テーブルを `m_consumerMap` 反復順に drain
   （`DOT1P_TO_TC_MAP` はここで処理される）
2. `CFG_PORT_QOS_MAP_TABLE_NAME` を drain
3. `CFG_QUEUE_TABLE_NAME` を drain

これにより `DOT1P_TO_TC_MAP` SAI オブジェクトが `PORT_QOS_MAP` 参照解決より先に生成される
ことが保証される（`resolveFieldRefValue()` の task_need_retry リトライが最小化される）。

## 4. select タイムアウト・リトライ

- select タイムアウト: **1000 ms** (`SELECT_TIMEOUT`, orchdaemon.cpp:23)
- keyspace 通知到着時は即時 wake up
- リトライキャッシュ: `m_toSync` 残留方式（`task_need_retry` 時はエントリ保持、次回 drain で再処理）
- `task_failed` / `task_invalid_entry` 時はエントリを削除してリトライしない

## 5. CHANNEL PUBLISH / gNMI / APPL_DB 経由なし

`DOT1P_TO_TC_MAP` は CONFIG_DB → orchagent 直結。
cfgmgr 経由の APPL_DB 中継・NotificationProducer PUBLISH は一切使わない。

## 6. SAI 呼び出しサマリ

| 操作 | SAI API | qosorch.cpp |
|------|---------|-------------|
| SET (新規) | `sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_DOT1P_TO_TC, ...)` | 399-415 |
| SET (更新) | `sai_qos_map_api->set_qos_map_attribute(SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST, ...)` | 141-155 |
| DEL | `sai_qos_map_api->remove_qos_map(sai_object)` | 157-172 |

## Evidence

- `sonic-swss/orchagent/orchdaemon.cpp:23,367-384`
- `sonic-swss/orchagent/orch.cpp:97-101,1186-1194`
- `sonic-swss/orchagent/qosorch.cpp:1313-1345,1331,2231-2295,399-415,141-155,157-172`
