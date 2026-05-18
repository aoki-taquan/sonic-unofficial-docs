# ZMQ CONFIG_DB フィールド — 書込み順依存調査 (Phase B)

## 調査対象

- `DEVICE_METADATA|localhost` の `orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled`
- `DPU|<name>` の `orchagent_zmq_port`

## 主要な順序依存

### 1. CONFIG_DB 読み取りタイミング (一回限り・起動時)

`get_feature_status()` (`orch_zmq_config.cpp:81-104`) は orchagent 起動時に CONFIG_DB を直接読む。
この読み取りは `OrchDaemon` のコンストラクタ内で行われ (`orchdaemon.cpp:334`, `1329`)、
以降は runtime 変更を監視しない。

**含意**: `orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled` を CONFIG_DB に書く場合、
orchagent **再起動前**に設定しないと反映されない。orchagent が既に起動済みのタイミングで
フィールドを変更しても、実行中の orchagent インスタンスには影響しない。

evidence: `orchdaemon.cpp:333-337`, `orchdaemon.cpp:1327-1332`, `orch_zmq_config.cpp:81-104`

### 2. ZmqServer の lazy bind — ハンドラ登録 → bind の強制順序

`create_zmq_server()` (`orch_zmq_config.cpp:64-79`) は `ZmqServer` を
lazy bind モード (`true`) で生成する。実際の bind は `main.cpp:1036` で、
すべての orch ハンドラ (`ZmqConsumerStateTable`) が登録された後に明示的に呼ばれる。

```
[main.cpp]
1. zmq_server = create_zmq_server(zmq_server_address)   # lazy: bind しない
2. orchDaemon->init()                                    # 全ハンドラを ZmqServer に登録
3. zmq_server->bind()                                    # ここで初めて bind
4. orchDaemon->start(heartBeatInterval)
```

**含意**: bind 前 (init 完了前) に ZMQ クライアント (fpmsyncd / gnmi) がメッセージを
送信しようとしても接続できない。lazy bind はこのウィンドウを最小化し、
「ハンドラ未登録でメッセージを受信してドロップする」事故を防ぐ。

evidence: `main.cpp:646-654`, `main.cpp:1032-1038`, `orch_zmq_config.cpp:64-79`

### 3. RouteOrch への ZMQ 有効フラグ伝搬順序

`ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED` が `true` のとき、`route_zmq_sever` に
`m_zmqServer` を渡して `RouteOrch` を生成する (`orchdaemon.cpp:337`)。
`gRouteOrch` が生成された後は ZMQ/非 ZMQ の切替は不可能。
`fpmsyncd` 側も起動時に `create_local_zmq_client()` を呼び ZmqClient または
`nullptr` を固定する (`routesync.cpp:155`)。

**両側の起動タイミング依存**:
- orchagent が `bind()` を完了した後でなければ fpmsyncd の ZmqClient は接続できない
- fpmsyncd の ZmqClient が `nullptr` (feature=false) の場合は Redis ProducerStateTable にフォールバック

evidence: `orchdaemon.cpp:333-337`, `routesync.cpp:154-158`, `orch_zmq_config.cpp:106-115`

### 4. ZmqConsumer の ordered_queue モード

`ZmqOrch::addConsumer()` は `orderedQueue` フラグを受け取り、
`ZmqConsumer` を ordered キューモードで生成できる (`zmqorch.cpp:65-66`)。

ordered モードでは `execute()` 内でエントリを `m_queue` に蓄積し、
`drain()` で `doTask()` を呼ぶ。非 ordered モードでは `addToSync()` で
従来の `m_toSync` に入れる (`zmqorch.cpp:8-33`)。

この順序保証は送信側 (`ZmqProducerStateTable`) とのペアで機能し、
同一テーブル内での SET/DEL の順序が保たれる。

evidence: `zmqorch.cpp:8-33`, `zmqorch.cpp:59-78`

## 検出された順序依存テーブル

| # | 依存関係 | 方向 | 備考 |
|---|----------|------|------|
| 1 | CONFIG_DB フィールド書き込み → orchagent 再起動 | **起動前必須** | runtime 変更は無効 |
| 2 | 全ハンドラ登録 → ZmqServer.bind() | 強制先行 | lazy bind で自動保証 |
| 3 | orchagent bind() 完了 → fpmsyncd/gnmi の ZmqClient 接続 | orchagent 先行 | 接続失敗は ZMQ ECONNREFUSED |
| 4 | `orch_northbond_route_zmq_enabled` 読み取り → RouteOrch 生成 | 1 回限り | 変更には orchagent 再起動が必要 |
| 5 | DASH ZMQ 有効時: `DpuOrchDaemon` init → DashXxxOrch 生成 | 直列 (同一 init()) | DASH orch 群は全て同一 zmq_server を共有 |
