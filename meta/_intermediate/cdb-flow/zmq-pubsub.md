# Phase G 中間ファイル: ZMQ CONFIG_DB フィールド 通信メカニズム

ソース:
- `sonic-swss/lib/orch_zmq_config.cpp`
- `sonic-swss/lib/orch_zmq_config.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/zmqserver.h`

## 1. DEVICE_METADATA フィールドの消費メカニズム

`orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled` は通常の Orch 購読では**読まれない**。

`get_feature_status()` (orch_zmq_config.cpp:81-104) が起動時に一回だけ `DBConnector::hget` で取得する:

```cpp
swss::DBConnector config_db("CONFIG_DB", 0);
enabled = config_db.hget("DEVICE_METADATA|localhost", feature);
```

呼び出し元:
- `OrchDaemon::init()` (orchdaemon.cpp:334): `ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED`, default=false
- `DpuOrchDaemon::init()` (orchdaemon.cpp:1329): `ORCH_NORTHBOND_DASH_ZMQ_ENABLED`, default=true

runtime 変更は反映されない。orchagent 再起動が必要。

## 2. DPU|<name>.orchagent_zmq_port の消費メカニズム

orchagent が直接 CONFIG_DB を読まず、`gnmi-native.sh` や周辺スクリプトが起動パラメータとして渡す。
orch_zmq_config.cpp に当該フィールドの読み取りコードなし。

## 3. ZMQ チャネルの通信メカニズム

ZMQ 有効時、`ZmqConsumerStateTable` が Redis `ConsumerStateTable` の代わりにメッセージを受信する。

### orchagent 側（サーバ）

`ZmqServer` が `tcp://...:8100` でバインドし、ZmqConsumerStateTable がメッセージをポールする。

定数 (zmqserver.h):
- `MQ_RESPONSE_MAX_COUNT = 16 * 1024 * 1024` (16MiB) — メッセージ最大サイズ
- `MQ_SIZE = 100` — 内部キュー初期サイズ
- `MQ_MAX_RETRY = 10` — 送信失敗時の最大 retry 回数
- `MQ_POLL_TIMEOUT = 1000` (ms) — zmq_poll タイムアウト
- `MQ_WATERMARK = 10000` — HWM (超過で EAGAIN / DROP)
- `DEFAULT_POP_BATCH_SIZE = 128` — 1 回のポールで取り出す最大エントリ数

### クライアント側（fpmsyncd / gnmi）

`ZmqProducerStateTable` が `ZmqClient` 経由で送信。

`create_local_zmq_client()` (orch_zmq_config.cpp:106-115):
- feature が true → `ZmqClient(ZMQ_LOCAL_ADDRESS + ":" + port)` を作成
- feature が false → `nullptr` を返す

`createProducerStateTable()` (orch_zmq_config.cpp:117-145):
- `zmqClient != nullptr` → `ZmqProducerStateTable` (ZMQ 経由)
- `zmqClient == nullptr` → `ProducerStateTable` (Redis Pub/Sub 経由) にフォールバック

### ZMQ 有効時の APPL_DB 非書込み

`ZmqProducerStateTable` はメッセージを APPL_DB に書かず直接 ZMQ ソケットへ送信する。
そのため ZMQ 有効時は `sonic-db-cli APPL_DB keys 'DASH_*'` でエントリが存在しない可能性がある。

## 証拠コード

```
sonic-swss/lib/orch_zmq_config.cpp:81-104  — get_feature_status()
sonic-swss/lib/orch_zmq_config.cpp:106-115 — create_local_zmq_client()
sonic-swss/lib/orch_zmq_config.cpp:117-145 — createProducerStateTable()
sonic-swss/orchagent/orchdaemon.cpp:334    — ROUTE ZMQ 有効フラグ読み取り
sonic-swss/orchagent/orchdaemon.cpp:1329   — DASH ZMQ 有効フラグ読み取り
sonic-swss-common/common/zmqserver.h:9-31  — MQ 定数群
```
