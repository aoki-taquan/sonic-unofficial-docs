# MAP_PFC_PRIORITY_TO_QUEUE テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `MAP_PFC_PRIORITY_TO_QUEUE` テーブル。
ソース: `sonic-swss/orchagent/qosorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`

## 1. 購読 API — `ConsumerStateTable` (orchagent 直接 CFG 購読)

`QosOrch` は `swsscommon::ConsumerStateTable` を通じて CONFIG_DB の `MAP_PFC_PRIORITY_TO_QUEUE` テーブルを直接購読する。APPL_DB 経由の中継はなく、CONFIG_DB の変化が直接 orchagent に伝わる。

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:370-384
vector<string> qos_tables = {
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    ...
    CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME,   // "MAP_PFC_PRIORITY_TO_QUEUE"
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

- `QosOrch` コンストラクタ内で `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME` を含む全テーブルの `ConsumerStateTable` を作成し、orchagent の select ループに登録する。
- Redis の keyspace 通知ではなく、swsscommon の **SUBSCRIBE / PSUBSCRIBE** ベースの channel 型通知 (`ConsumerStateTable`) を使用。`HSET`/`DEL` 操作は swsscommon がキュー (`m_toSync`) に積み、`select()` で取得される。
- TTL なし（CONFIG_DB は永続前提）。

## 2. メッセージフロー

```
[config CLI / config qos reload / minigraph / sonic-cfggen]
    │  HSET MAP_PFC_PRIORITY_TO_QUEUE|<name> <pfc_priority> <qindex>
    ▼
CONFIG_DB (Redis db=4)
    │  swsscommon ConsumerStateTable
    ▼
QosOrch::doTask(Consumer &consumer)         # orchdaemon select ループから呼出
    │  consumer.getTableName() == "MAP_PFC_PRIORITY_TO_QUEUE"
    │  → m_qos_handler_map ルックアップ
    ▼
QosOrch::handlePfcToQueueTable(consumer, tuple)  # qosorch.cpp:1299-1304
    │
    ▼
PfcToQueueHandler::processWorkItem(consumer, tuple)  # qosorch.cpp:124+
    │  convertFieldValuesToAttributes() — stoi(pfc_priority) / stoi(qindex)
    │  → sai_qos_map_list_t 構築 (key.prio / value.queue_index)
    ▼
sai_qos_map_api->create_qos_map() / set_qos_map()
    │  SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE     # qosorch.cpp:1021
    ▼
ASIC (ASIC Driver / SAI adapter)
```

- APPL_DB への書き込みなし。CONFIG_DB → orchagent → SAI の 2 ホップ経路。
- `m_qos_handler_map` への登録: `qosorch.cpp:1344`
  ```cpp
  m_qos_handler_map.insert(qos_handler_pair(
      CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME,
      &QosOrch::handlePfcToQueueTable));
  ```

## 3. キー単位ディスパッチ

- `consumer.getTableName()` = `"MAP_PFC_PRIORITY_TO_QUEUE"`
- `kfvKey(tuple)` = マップ名（例: `"AZURE"`）
- `kfvOp(tuple)` = `"SET"` (追加/更新) / `"DEL"` (削除)
- `kfvFieldsValues(tuple)` = PFC priority → queue index のペアリスト
  - field: `"0"`.`"7"` (pfc_priority)
  - value: `"0"`.`"7"` (qindex)

## 4. SAI 経路詳細

```cpp
// qosorch.cpp:991-1035 (PfcToQueueHandler::convertFieldValuesToAttributes / addQosItem)
sai_qos_map_list_t pfc_to_queue_map_list;
pfc_to_queue_map_list.count = kfvFieldsValues(tuple).size();
for each (field, value) in kfvFieldsValues(tuple):
    pfc_to_queue_map_list.list[ind].key.prio         = (uint8_t)stoi(field);
    pfc_to_queue_map_list.list[ind].value.queue_index = (uint8_t)stoi(value);

// SAI 属性組み立て
list_attr.id = SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST;
list_attr.value.qosmap = pfc_to_queue_map_list;
qos_map_attr.id = SAI_QOS_MAP_ATTR_TYPE;
qos_map_attr.value.s32 = SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE;

// SAI API 呼び出し
sai_qos_map_api->create_qos_map(&map_id, gSwitchId, 2, attrs);
// エラー時: SWSS_LOG_ERROR("Failed to create pfc_priority_to_queue map. status:%d", sai_status)
```

## 5. タスク処理結果とリトライ

| 状態 | 条件 | 動作 |
|------|------|------|
| `task_success` | SAI 操作成功 | `m_toSync` から除去、完了 |
| `task_invalid_entry` | `stoi()` 失敗（空文字・非数値）または SAI オブジェクト不在 (DEL) | エントリ破棄、エラーログ |
| `task_failed` | SAI API 返値 ≠ `SAI_STATUS_SUCCESS` | エントリ破棄、`doTask` リターン（後続処理中断） |
| `task_need_retry` | DEL 時に `isObjectBeingReferenced()` = true | `m_pendingRemove=true`、キュー末尾に残し再試行 |

## 6. 関連オブジェクト参照追跡

`PORT_QOS_MAP.pfc_to_queue_map` が `MAP_PFC_PRIORITY_TO_QUEUE` エントリを参照する。DEL 操作時に `isObjectBeingReferenced()` が true を返す場合、`task_need_retry` で保留される（`qosorch.cpp:180-186`）。

参照解除（`PORT_QOS_MAP` 側でマップ名が外れる）後、次回 orchagent ループで DEL が再試行される。

## 7. gPortsOrch 依存

`QosOrch::doTask()` の先頭で `gPortsOrch->allPortsReady()` を確認する（`qosorch.cpp:2259-2262`）。ポート初期化完了前は全 QoS テーブル処理をスキップし、次回ループに持ち越す。
