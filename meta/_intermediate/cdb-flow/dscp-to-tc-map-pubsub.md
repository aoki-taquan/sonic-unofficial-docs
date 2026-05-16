# CONFIG_DB DSCP_TO_TC_MAP — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `DSCP_TO_TC_MAP` テーブル（スキーマ定数: `CFG_DSCP_TO_TC_MAP_TABLE_NAME`、`sonic-swss-common/common/schema.h`）。

ソース確認: `sonic-swss/orchagent/qosorch.cpp`、`sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/orchagent/orch.cpp`、`sonic-swss-common/common/subscriberstatetable.{h,cpp}`、`sonic-swss-common/common/table.h`。

## 1. 購読 API — `SubscriberStateTable` (keyspace 通知ベース)

CONFIG_DB の `DSCP_TO_TC_MAP` は `orchdaemon.cpp:367-384` で `qos_tables` ベクタの一員として `CFG_DSCP_TO_TC_MAP_TABLE_NAME` を指定し、`gQosOrch = new QosOrch(m_configDb, qos_tables)` に渡される。

```cpp
// orchdaemon.cpp:367-384
vector<string> qos_tables = {
    CFG_TC_TO_QUEUE_MAP_TABLE_NAME,
    CFG_SCHEDULER_TABLE_NAME,
    CFG_DSCP_TO_TC_MAP_TABLE_NAME,   // ← ここ
    CFG_MPLS_TC_TO_TC_MAP_TABLE_NAME,
    CFG_DOT1P_TO_TC_MAP_TABLE_NAME,
    ...
};
gQosOrch = new QosOrch(m_configDb, qos_tables);
```

`QosOrch::QosOrch(DBConnector *db, vector<string> &tableNames)` は基底 `Orch(db, tableNames)` を呼び出す。`Orch(DBConnector*, vector<string>&)` は各テーブル名に対して `Orch::addConsumer(db, tableName)` を呼ぶ。

`addConsumer()` は DB ID で分岐する（`orch.cpp:1186-1196`）:

```cpp
// orch.cpp:1186-1196
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

CONFIG_DB (`dbId == 4`) はこの分岐の最初の if 節にマッチするため、**`SubscriberStateTable`** が選択される。

- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:DSCP_TO_TC_MAP|*` への `PSUBSCRIBE`) を購読し、通知 (`set` / `hset` / `del` / `hdel` 等) を受信したら **`HGETALL` で値を再取得**してから `pops()` で `(key, op, fvs)` タプル列を返す (`subscriberstatetable.cpp:45-165`)。
- バッチサイズは **`TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`** (`table.h:164`、ハードコード)。`orchagent -b` オプションの `gBatchSize` は APPL_DB 側 (`ConsumerStateTable`) にのみ作用し、CONFIG_DB 側には影響しない。
- TTL は CONFIG_DB の全エントリで未設定（CONFIG_DB は永続前提）。

## 2. 書き込み側 (publisher)

CONFIG_DB の `DSCP_TO_TC_MAP` は以下の経路で書き込まれる:

- `config qos map dscp-tc add/del <map-name> <dscp> <tc>` — `sonic-utilities` の CLI が `swss.Table.set()` / `del()` を発行
- `sonic-cfggen` / `qos_config.j2` テンプレート — ビルド時 / minigraph 適用時に AZURE 等のマップを一括 `HSET`
- `gNMI` / REST 経由（`sonic-mgmt-common` YANG transformer 対応分のみ）

明示的な `PUBLISH` は行われず、Redis の keyspace 通知設定が `__keyspace@<dbId>__:DSCP_TO_TC_MAP|<name>` イベントを発行し、購読者 (`QosOrch`) がそれを受信する。

## 3. 購読側ディスパッチ

`QosOrch` は `m_qos_handler_map` で各テーブル名 → ハンドラ関数ポインタをマッピングする。`DSCP_TO_TC_MAP` 用のハンドラは `initTableHandlers()` で登録される:

```cpp
// qosorch.cpp:1329
m_qos_handler_map.insert(qos_handler_pair(CFG_DSCP_TO_TC_MAP_TABLE_NAME,
    &QosOrch::handleDscpToTcTable));
```

`OrchDaemon` のメインループ (`orchdaemon.cpp:959`) が `m_select->select(&s, SELECT_TIMEOUT)` で待ち、keyspace 通知到着時に対象 Consumer が wake up し `doTask(Consumer&)` が呼ばれる。

```cpp
// qosorch.cpp:2254-2295 (QosOrch::doTask(Consumer&))
void QosOrch::doTask(Consumer &consumer)
{
    auto qos_map_type_name = consumer.getTableName();
    auto task_status = (this->*(m_qos_handler_map[qos_map_type_name]))(consumer, it->second);
    // task_success → erase; task_need_retry → keep; task_failed → erase + return
}
```

`QosOrch::doTask()` (引数なし版) は `PORT_QOS_MAP` / `QUEUE` を後回しにするため、それ以外の consumer（`DSCP_TO_TC_MAP` を含む）を先に drain する (`qosorch.cpp:2231-2252`)。これは依存関係上 DSCP map が PORT_QOS_MAP より先に処理される順序保証になっている。

`handleDscpToTcTable()` は `DscpToTcMapHandler::processWorkItem()` → `DscpToTcMapHandler::createAttributeList()` を呼び、`sai_qos_map_api->create_qos_map()` / `set_qos_map_attribute()` / `remove_qos_map()` で SAI に反映する。

## 4. select タイムアウト

```cpp
// orchdaemon.cpp:22-23
#define SELECT_TIMEOUT 1000
```

`m_select->select(&s, SELECT_TIMEOUT)` は **1000 ms (1 秒)** で wake up し heartbeat 処理を回す。keyspace 通知到着時は即座に wake up する。

## 5. リトライ機構

リトライキャッシュは使用しない。`task_need_retry` の場合は consumer の `m_toSync` にエントリを残し、次回 `doTask()` 呼び出し時に再処理される。主なリトライトリガー:

- `PORT_QOS_MAP` が `dscp_to_tc_map` フィールドを参照中に `DSCP_TO_TC_MAP|<name>` DEL → `m_pendingRemove = true` + `task_need_retry`
- `TUNNEL_DECAP_TABLE` が未解決の DSCP map を参照 → `task_need_retry`（`tunneldecaporch.cpp:217-221`）

## 6. サマリ

| 観点 | CONFIG_DB 側 `DSCP_TO_TC_MAP` |
|---|---|
| 購読方式 | `swss::SubscriberStateTable`（Redis keyspace 通知 `__keyspace@<dbId>__:DSCP_TO_TC_MAP|*` の `PSUBSCRIBE`） |
| バッチサイズ | `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`、ハードコード） |
| select タイムアウト | 1000 ms (`SELECT_TIMEOUT`、`orchdaemon.cpp:23`) |
| 書き込み側 API | `swss::Table::set()` / `del()`; CLI / `sonic-cfggen` / gNMI 経由 |
| ハンドラ登録 | `initTableHandlers()` → `m_qos_handler_map[CFG_DSCP_TO_TC_MAP_TABLE_NAME]` = `&QosOrch::handleDscpToTcTable` |
| SAI 呼び出し | `sai_qos_map_api->create_qos_map()` / `set_qos_map_attribute()` / `remove_qos_map()` |
| リトライキャッシュ | 未使用（`m_toSync` 残留方式） |
| keyspace 通知 | **使う**（`SubscriberStateTable` の基盤プロトコル） |
| channel `<TABLE>_CHANNEL` PUBLISH | 使わない |
| TTL | 未使用（CONFIG_DB は永続） |
| `orchagent -b` 影響 | なし（CONFIG_DB は `DEFAULT_POP_BATCH_SIZE` 固定） |
| 処理順序保証 | `QosOrch::doTask()` が `DSCP_TO_TC_MAP` を `PORT_QOS_MAP` / `QUEUE` より先に drain |

## 7. サービス再起動トリガー

なし。`QosOrch` は orchagent プロセス内のハンドラで、`DSCP_TO_TC_MAP` の追加・変更・削除は SAI QoS map オブジェクトのライブ操作のみで反映され、プロセス再起動を伴わない。参照中 map への DEL は pending_remove ロックで保護される。

## 8. Evidence サマリ

- `sonic-swss/orchagent/orchdaemon.cpp` L22-23, L367-384 — `SELECT_TIMEOUT`、`qos_tables` ベクタと `gQosOrch` 生成
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` の DB ID 分岐（CONFIG_DB → `SubscriberStateTable`）
- `sonic-swss/orchagent/qosorch.cpp` L1313-1345 — `QosOrch::QosOrch()` / `initTableHandlers()` / `m_qos_handler_map` 登録
- `sonic-swss/orchagent/qosorch.cpp` L2231-2295 — `QosOrch::doTask()` / `doTask(Consumer&)` ディスパッチ
- `sonic-swss/orchagent/qosorch.cpp` L124-194 — `QosMapHandler::processWorkItem()` / pending_remove ロック
- `sonic-swss/orchagent/qosorch.cpp` L239-292 — `DscpToTcMapHandler::createAttributeList()` / `removePriorityGroup()` / SAI API 呼び出し
- `sonic-swss-common/common/subscriberstatetable.{h,cpp}` — `SubscriberStateTable` コンストラクタと `PSUBSCRIBE` + `HGETALL` 動作
- `sonic-swss-common/common/table.h` L164 — `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`
