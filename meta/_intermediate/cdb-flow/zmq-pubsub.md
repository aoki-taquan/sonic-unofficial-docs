# ZMQ CONFIG_DB フィールド — 通信メカニズム (Phase G) 解析メモ

対象: `DEVICE_METADATA|localhost` の `orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled`、`DPU|<name>` の `orchagent_zmq_port`

## 1. CONFIG_DB フィールドの読み取り方式 — 購読なし

ZMQ 関連 CONFIG_DB フィールドは `orchagent` 起動時に `hget` で一度だけ読まれる。`SubscriberStateTable` / `ConsumerStateTable` のいずれも使用しない。

```cpp
// sonic-swss/lib/orch_zmq_config.cpp:88
enabled = config_db.hget("DEVICE_METADATA|localhost", feature);
```

`orchdaemon.cpp:334` (route zmq) と `orchdaemon.cpp:1329` (dash zmq) の両方が `get_feature_status()` を通じてこのパスを通る。orchagent は DEVICE_METADATA テーブルを ZMQ フラグのために購読しない。

## 2. ZMQ が置き換える通信経路

`orch_northbond_*_zmq_enabled` を `true` に設定すると、当該 APPL_DB テーブルへの書き込み経路が Redis Pub/Sub から ZeroMQ TCP ソケットに切り替わる。

| フラグ | 従来の経路 (Redis) | ZMQ 有効時の経路 |
|--------|------------------|----------------|
| `orch_northbond_dash_zmq_enabled=true` | gNMI → ProducerStateTable → APPL_DB → orchagent | gNMI → ZmqProducerStateTable → orchagent (TCP:8100) |
| `orch_northbond_route_zmq_enabled=true` | fpmsyncd → ProducerStateTable → APPL_DB → orchagent | fpmsyncd → ZmqProducerStateTable → orchagent (TCP:8100) |

ZMQ 経路では Redis チャンネルへの `PUBLISH` は発生せず、APPL_DB に対応するレコードが書き込まれない場合がある。

## 3. orchagent 側の ZmqConsumerStateTable

orchagent は `ZmqConsumerStateTable` で ZMQ メッセージを受信する。`load_zmq_tables()` (`orch_zmq_config.cpp:18-33`) が起動時に `/etc/swss/orch_zmq_tables.conf` を読み込んでテーブル名一覧を取得し、各テーブルに対し `ZmqConsumerStateTable` を登録する。

ZMQ サーバ自体は lazy bind モードで生成され (`orch_zmq_config.cpp:64-79`)、全ハンドラ登録後に `main.cpp:1036` で `zmqServer->bind()` を呼ぶ。これ以降は ZmqClient 側からの接続を受け付ける。

## 4. ZmqConsumerStateTable と Redis Consumer の比較

| 項目 | ConsumerStateTable (Redis) | ZmqConsumerStateTable |
|------|--------------------------|----------------------|
| トランスポート | Redis keyspace 通知 / PUBLISH | ZeroMQ TCP ソケット |
| エントリ取得 | `pops()` Lua SCRIPT | 受信スレッドが `m_queue` に push |
| バッチサイズ | `gBatchSize` (既定 128) | `DEFAULT_POP_BATCH_SIZE = 128` (`zmqserver.h:31`) |
| 順序保証 | table 内 FIFO | `orderedQueue=true` のとき `m_queue` で FIFO 保証 |
| HWM | なし (Redis) | `MQ_WATERMARK = 10000` (`zmqserver.h:13`) |

## 5. DPU|orchagent_zmq_port の読み取り

SmartSwitch 環境では `orchagent.sh` / `gnmi-native.sh` が `DPU|<name>.orchagent_zmq_port` を bash スクリプト内で `sonic-db-cli CONFIG_DB hget` して接続ポートを決定する。これも一回読みでありサブスクリプションではない。

## 証跡

- `sonic-swss/lib/orch_zmq_config.cpp:88` — `config_db.hget("DEVICE_METADATA|localhost", feature)`
- `sonic-swss/orchagent/orchdaemon.cpp:334` — `get_feature_status(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)`
- `sonic-swss/orchagent/orchdaemon.cpp:1329` — `get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true)`
- `sonic-swss/lib/orch_zmq_config.cpp:64-79` — `create_zmq_server()` lazy bind
- `sonic-swss-common/common/zmqserver.h:31` — `DEFAULT_POP_BATCH_SIZE = 128`
- `sonic-swss-common/common/zmqserver.h:13` — `MQ_WATERMARK = 10000`
