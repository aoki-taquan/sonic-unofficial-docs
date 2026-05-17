# DASH_ENI_TABLE — Phase G: ZMQ / ZmqConsumerStateTable / ProducerStateTable

対象ページ: `docs/reference/config-db/dash-eni.md`
調査日: 2026-05-17
Evidence:
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/zmqorch.cpp` および `zmqorch.h`
- `sonic-swss-common/common/zmqserver.h` および `zmqserver.cpp`
- `sonic-swss-common/common/zmqconsumerstatetable.h` および `zmqconsumerstatetable.cpp`
- `sonic-swss-common/common/zmqproducerstatetable.h`
- `sonic-swss-common/common/zmqclient.h`
- `sonic-swss/orchagent/orchdaemon.cpp` (L1322–1420)
- `sonic-swss/tests/create_appliance.py` (ZmqClient 接続例)

---

## 概要

`DASH_ENI_TABLE` の変更通知は **Redis keyspace notification ではなく ZeroMQ (ZMQ) メッセージ** で実装されている。
DASH コントローラ (gNMI サービス等) が `ZmqProducerStateTable` (クライアント側) を通じて
`tcp://127.0.0.1:8100` に Protobuf エンコードの SET/DEL メッセージを送出し、
orchagent 側の `ZmqServer` + `ZmqConsumerStateTable` が受信して `ZmqConsumer::execute()` → `DashOrch::doTask()` に渡す。
Redis keyspace notification (PSUBSCRIBE) / `SubscriberStateTable` / `NotificationConsumer` は**一切使用しない**。

ZMQ チャンネルが無効化されている場合 (`ORCH_NORTHBOND_DASH_ZMQ_ENABLED=false`) は
通常の `ConsumerStateTable` (Redis SUBSCRIBE ベース) にフォールバックする
(`zmqorch.cpp:63-72`)。

---

## ZMQ ポートとエンドポイント

| 定数 | 値 | ファイル |
|------|-----|---------|
| `ORCH_ZMQ_PORT` | `8100` | `sonic-swss-common/common/zmqserver.h:16` |
| デフォルトエンドポイント | `tcp://127.0.0.1:8100` | `tests/create_appliance.py:27` |
| フィーチャーフラグ | `ORCH_NORTHBOND_DASH_ZMQ_ENABLED` (デフォルト: `true`) | `orchdaemon.cpp:1329` |

---

## 通信シーケンス

### 1. orchagent 起動時 — `DpuOrchDaemon::init()` (orchdaemon.cpp:1322-1419)

```
DpuOrchDaemon::init()
  └─ get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true)
       └─ true  → dash_zmq_server = m_zmqServer   ← ZmqServer("tcp://127.0.0.1:8100") を使用
       └─ false → dash_zmq_server = nullptr        ← ConsumerStateTable (Redis) にフォールバック

  └─ DashOrch(m_dpu_appDb, dash_tables, m_dpu_appstateDb, dash_zmq_server)
       └─ ZmqOrch::ZmqOrch(db, tableNames, zmqServer)
            └─ addConsumer(db, "DASH_ENI_TABLE", default_pri, zmqServer)
                 └─ ZmqConsumerStateTable(db, "DASH_ENI_TABLE", *zmqServer, gBatchSize, pri, dbPersistence=true)
                      └─ zmqServer.registerMessageHandler("DPU_APPL_DB", "DASH_ENI_TABLE", this)
                      └─ m_asyncDBUpdater = AsyncDBUpdater(db, "DASH_ENI_TABLE")  ← DB persistence 有効
```

`ZmqServer` はバックグラウンドスレッド (`mqPollThread`) で ZMQ PULL ソケットを `bind()` し、
受信メッセージを `handleReceivedData()` で対応 handler (`ZmqConsumerStateTable`) に転送する。

### 2. コントローラ (送信側) の接続

```
DASH コントローラ (gNMI / sonic-mgmt-common 等)
  └─ ZmqClient("tcp://127.0.0.1:8100")
  └─ ZmqProducerStateTable(dpu_app_db, "DASH_ENI_TABLE", zmq_client, dbPersistence=true)
       └─ set(eni_mac, [("pb", protobuf.SerializeToString())])  ← SET
       └─ del(eni_mac)                                          ← DEL
```

gNMI SetRequest → `sonic-mgmt-common` が Protobuf にエンコード → `ZmqProducerStateTable::set()` →
`ZmqClient::sendMsg()` → ZMQ PUSH ソケット経由で orchagent の ZmqServer へ送信。

`dbPersistence=true` の場合、`ZmqProducerStateTable` は送信と同時に `DPU_APPL_DB` の
`DASH_ENI_TABLE` にも Redis 書き込みを行う (`AsyncDBUpdater` 経由で非同期)。
これにより orchagent 再起動後も APP_DB にエントリが残留し、再受信が不要になる。

### 3. orchagent 受信 — `ZmqServer::mqPollThread()` → `ZmqConsumerStateTable::handleReceivedData()`

```
ZmqServer::mqPollThread()  [バックグラウンドスレッド]
  └─ zmq_poll(socket, MQ_POLL_TIMEOUT=1000ms)
  └─ zmq_recv(buffer)
  └─ BinarySerializer::deserialize(buffer) → vector<KeyOpFieldsValuesTuple>
  └─ findMessageHandler("DPU_APPL_DB", "DASH_ENI_TABLE") → ZmqConsumerStateTable*
  └─ handler->handleReceivedData(kcos)
       └─ m_receivedOperationQueue.push(kco)   [mutex lock]
       └─ m_asyncDBUpdater->update(clone)       ← DB persistence: DPU_APPL_DB への非同期書き込み
       └─ m_selectableEvent.notify()            ← epoll wakeup (Selectable)

Select ループ (orchagent メインスレッド)
  └─ selectableEvent が ready → ZmqConsumer::execute()
       └─ ZmqConsumerStateTable::pops(entries)   ← バッチ取得 (gBatchSize 件まで)
       └─ addToSync(entries)                      ← m_toSync キューへ積む
  └─ ZmqConsumer::drain()
       └─ DashOrch::doTask(*consumer)
            └─ doTaskEniTable(consumer)
                 └─ addEni() / removeEni() → SAI
```

### 4. DB persistence — 起動時の再生

`ZmqConsumerStateTable(dbPersistence=true)` は `AsyncDBUpdater` を持つ。
受信した SET/DEL は ZMQ 経由で処理されると同時に、非同期で `DPU_APPL_DB` の `DASH_ENI_TABLE` にも書かれる。
orchagent 再起動時は `warmRestoreAndSyncUp()` → `bake()` が APP_DB の既存エントリを
`m_toSync` に積み直し、3 イテレーション `doTask()` を実行する。
これにより、コントローラの再送なしで ENI 設定が再適用される。

---

## 送受信フロー概要

```
[DASH コントローラ]
  gNMI SetRequest
    └─ sonic-mgmt-common (Protobuf エンコード)
         └─ ZmqClient("tcp://127.0.0.1:8100")
              └─ ZmqProducerStateTable::set(eni_mac, [("pb", pb_bytes)])
                   ├─ ZmqClient::sendMsg() → ZMQ PUSH → orchagent ZmqServer
                   └─ AsyncDBUpdater → DPU_APPL_DB:DASH_ENI_TABLE (非同期・DB persistence)

[orchagent — バックグラウンドスレッド]
  ZmqServer::mqPollThread()
    └─ zmq_recv() → BinarySerializer::deserialize()
    └─ ZmqConsumerStateTable::handleReceivedData()
         ├─ m_receivedOperationQueue.push()
         ├─ AsyncDBUpdater::update() → DPU_APPL_DB (DB persistence)
         └─ SelectableEvent::notify()

[orchagent — メインスレッド]
  Select::select()
    └─ ZmqConsumer::execute()
         └─ ZmqConsumerStateTable::pops() → addToSync()
    └─ ZmqConsumer::drain()
         └─ DashOrch::doTaskEniTable()
              └─ addEni() / removeEni() → SAI DASH ENI API
              └─ writeResultToDB() → APPL_STATE_DB:DASH_ENI_TABLE:<eni_mac>
```

---

## Redis との関係

`DASH_ENI_TABLE` の変更は **ZMQ 経由のみ** で orchagent に到達する。Redis の ProducerStateTable チャンネル
(`DASH_ENI_TABLE_CHANNEL@<db_id>`) は使用されない。ただし DB persistence により `DPU_APPL_DB` の
`DASH_ENI_TABLE` には SET/DEL の内容が非同期書き込みされるため、`redis-cli` や `sonic-db-cli`
で参照することは可能 (orchagent の入力ではなくログ的役割)。

| DB / チャンネル | 使用 | 用途 |
|----------------|------|------|
| ZMQ `tcp://127.0.0.1:8100` | 使用 | コントローラ → orchagent の SET/DEL メッセージ |
| `DPU_APPL_DB:DASH_ENI_TABLE` | 使用 (非同期書き込み) | DB persistence (orchagent 再起動時の再生用) |
| `APPL_STATE_DB:DASH_ENI_TABLE` | 使用 | 処理結果 (DASH_RESULT_SUCCESS/FAILURE) の書き戻し |
| Redis keyspace notification | 不使用 | — |
| Redis SUBSCRIBE / PSUBSCRIBE | 不使用 | — |
| `ProducerStateTable` チャンネル | 不使用 | — |
| `NotificationConsumer` | 不使用 | — |
| `SubscriberStateTable` | 不使用 | — |

---

## ZMQ フォールバック (ZMQ 無効時)

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED=false` または orchagent 起動時 `-q` オプションなし時:

```
dash_zmq_server = nullptr
  └─ ZmqOrch::addConsumer()
       └─ ConsumerStateTable(db, "DASH_ENI_TABLE", gBatchSize, pri)
            └─ Redis SUBSCRIBE DASH_ENI_TABLE_CHANNEL@<db_id>
```

この場合、コントローラは通常の `ProducerStateTable` 経由で `DPU_APPL_DB` に書き込み、
Redis の PUBLISH/SUBSCRIBE 機構で orchagent に通知する。ただし DPU 環境では ZMQ が
デフォルト有効のため、通常このパスは使われない。

---

## 特性まとめ

| 特性 | 内容 |
|------|------|
| 通知種別 | ZeroMQ (PUSH/PULL パターン) |
| SWSS abstraction | `ZmqConsumerStateTable` + `ZmqOrch` |
| エンドポイント | `tcp://127.0.0.1:8100` (デフォルト) / `ORCH_ZMQ_PORT=8100` |
| メッセージ形式 | Protobuf binary (`"pb"` フィールドにシリアライズ済みバイト列) |
| バッチサイズ | `gBatchSize` (デフォルト 128) |
| poll タイムアウト | `MQ_POLL_TIMEOUT = 1000 ms` (ZmqServer バックグラウンドスレッド) |
| DB persistence | 有効 (`dbPersistence=true`) — 受信データを DPU_APPL_DB にも非同期書き込み |
| 起動時スナップショット | あり — `bake()` が DPU_APPL_DB の既存エントリを m_toSync に再積み込み |
| Redis keyspace notification | 不使用 |
| SubscriberStateTable | 不使用 |
| NotificationConsumer | 不使用 |
| APPL_STATE_DB 書き戻し | あり (`writeResultToDB` / `removeResultFromDB`) |
| ZMQ 無効フォールバック | `ConsumerStateTable` (Redis SUBSCRIBE) |
