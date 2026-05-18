# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP 通信メカニズム調査 (Phase G)

## 購読方式

CONFIG_DB の `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` は `orchdaemon.cpp:367-384` の `qos_tables`
ベクタの一員として `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` を指定され、
`new QosOrch(m_configDb, qos_tables)` に渡される。

基底 `Orch::addConsumer()` が CONFIG_DB ID を検出し **`swss::SubscriberStateTable`** を選択
(`orch.cpp:1186-1196`)。

`SubscriberStateTable` は Redis keyspace 通知
`__keyspace@<dbId>__:PFC_PRIORITY_TO_PRIORITY_GROUP_MAP|*` を **`PSUBSCRIBE`** で購読し、
通知受信後に `HGETALL` で値を再取得して `(key, op, fvs)` タプルを返す。

バッチサイズ: `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128` (`table.h:164`、ハードコード)。
`orchagent -b` オプションの影響なし（APPL_DB 側 ConsumerStateTable のみに作用）。

## ハンドラ登録とディスパッチ

```
orchdaemon.cpp:377     qos_tables に CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME を追加
qosorch.cpp:1343       initTableHandlers() で
                        m_qos_handler_map[CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME]
                        = &QosOrch::handlePfcPrioToPgTable を登録
qosorch.cpp:2231-2252  QosOrch::doTask() が PORT_QOS_MAP / QUEUE より先に本テーブルを drain
qosorch.cpp:2254-2295  ハンドラ関数ポインタ経由でディスパッチ
```

`handlePfcPrioToPgTable()` → `PfcPrioToPgHandler::processWorkItem()`
→ `PfcPrioToPgHandler::createAttributeList()`
→ `sai_qos_map_api->create_qos_map()` [SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP]
/ `set_qos_map_attribute()` / `remove_qos_map()`。

## select タイムアウト・リトライ

select タイムアウト: **1000 ms** (`SELECT_TIMEOUT`, `orchdaemon.cpp:23`)。
keyspace 通知到着時は即時 wake up。`task_need_retry` 時は `m_toSync` にエントリを残置し
次サイクルで再処理。

## 証跡ソース

- `sonic-swss/orchagent/orchdaemon.cpp` L367-384
- `sonic-swss/orchagent/qosorch.cpp` L984, L1343, L2231-2295
- `sonic-swss/orchagent/orch.cpp` L1186-1196
- `swss-common/common/table.h` L164
