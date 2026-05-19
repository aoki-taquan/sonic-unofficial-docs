# TC_TO_DSCP_MAP — 通信メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/table.h`

## 購読 API

CONFIG_DB の `TC_TO_DSCP_MAP` は `orchdaemon.cpp` の `qos_tables` ベクタに含まれ、`QosOrch` コンストラクタで `addConsumer()` に渡される。`Orch::addConsumer()` は CONFIG_DB を検出し **`swss::SubscriberStateTable`** を選択する。

- 購読方式: Redis **keyspace 通知** (`PSUBSCRIBE __keyspace@<dbId>__:TC_TO_DSCP_MAP|*`)
- 通知到着時に `HGETALL` で値を再取得し `(key, op, fvs)` タプルとして `pops()` で返す
- バッチサイズ: `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`、ハードコード）
- `orchagent -b` オプションの影響なし（APPL_DB 側 `ConsumerStateTable` のみに作用）

## 書き込み側 (publisher)

`config qos reload`（`sonic-cfggen` + `qos_config.j2`）またはプラットフォーム `qos.json` 投入が `swss::Table::set()` / `HSET` を発行。明示的 `PUBLISH` は行われず Redis keyspace 通知で購読者に伝達。

## ディスパッチ経路

```
SubscriberStateTable (PSUBSCRIBE keyspace)
  → Consumer::execute() → pops() (HGETALL)
  → QosOrch::doTask(Consumer&)
  → m_qos_handler_map[CFG_TC_TO_DSCP_MAP_TABLE_NAME]
  → QosOrch::handleTcToDscpTable()
  → TcToDscpMapHandler::processWorkItem()
  → addQosItem(): sai_qos_map_api->create_qos_map() [SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP]
```

`QosOrch::doTask()` は `TC_TO_DSCP_MAP` を PORT_QOS_MAP / QUEUE より先に drain する順序制御あり（`qosorch.cpp:2231-2252`）。

## select タイムアウト・リトライ

- select タイムアウト: **1000 ms** (`SELECT_TIMEOUT`, `orchdaemon.cpp:23`)
- `task_need_retry` 時は `m_toSync` にエントリを残置して次サイクルで再処理
- サービス再起動トリガーなし（SAI ライブ操作のみで完結）
