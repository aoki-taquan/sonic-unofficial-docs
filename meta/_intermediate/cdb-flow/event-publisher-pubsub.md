# event-publisher — 通信メカニズム (Phase G) 解析メモ

対象: `init_cfg.json` の `"events"` キー（`eventd` / ZMQ イベントフレームワーク）。

## 1. CONFIG_DB 購読なし — ファイルベース起動時読み込みのみ

`eventd` は `init_cfg.json` を **ファイル直接読み** (`read_init_config(INIT_CFG_PATH)`) する。
Redis keyspace 通知 (`PSUBSCRIBE`) / `SubscriberStateTable` / `ConsumerStateTable` / `ConfigDBConnector` は一切使用しない。

証跡:
- `sonic-swss-common/common/events_common.cpp:38-83` — `read_init_config()` が `ifstream` でファイルを直接開く
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:674` — `get_config_data(CACHE_MAX_CNT, ...)` が lazy 初期化で一度だけ呼ばれる
- CONFIG_DB / APPL_DB / STATE_DB への読み書きパスは存在しない

## 2. ZMQ がフレームワーク内部の pub/sub メカニズム

`eventd` 自体が ZMQ ブローカーとして動作し、Redis pub/sub の代わりに ZeroMQ を使う:

| 区間 | 方式 | エンドポイント |
|------|------|--------------|
| パブリッシャー (全コンテナ) → eventd | ZMQ XSUB (`zmq_connect`) | `:5570` (`xsub_path`) |
| eventd (XSUB/XPUB プロキシ) → サブスクライバー | ZMQ XPUB (`zmq_connect`) | `:5571` (`xpub_path`) |
| telemetry → eventd (キャッシュ制御) | ZMQ REQ/REP | `:5572` (`req_rep_path`) |
| eventd → capture service | ZMQ PUB (内部) | `:5573` (`capture_path`) |

## 3. stats_collector の内部 subscribe

`stats_collector::start()` (`eventd.cpp:172-225`) は `events_init_subscriber(false, STATS_HEARTBEAT_MIN)` で
ZMQ XPUB (:5571) に接続する内部サブスクライバーを作成する (eventd.cpp:244)。
これは CONFIG_DB ではなく ZMQ 上の購読であり、COUNTERS_DB への統計書き込みに使う。

## 4. 変更の反映経路

```
管理者: init_cfg.json を手動編集
  ↓ (Redis への書き込みなし — ファイル直接編集)
systemctl restart eventd
  ↓ run_eventd_service() → get_config_data() で init_cfg.json を再読み込み
  ↓ ZMQ ソケット再バインド (xsub/xpub/req_rep/capture)
全 ZMQ クライアント (パブリッシャー・サブスクライバー) が自動再接続 (lazy connect)
```

`config reload` は `init_cfg.json` を書き直さないため、`eventd` の動的再設定には
`systemctl restart eventd` が必要 (redis keyspace notification が発火しないため)。

## 5. hostcfgd / orchagent 関与なし

- `hostcfgd` は `eventd` 設定を購読しない
- `orchagent` は event フレームワーク設定を処理しない
- `sonic-gnmi` は `xpub_path` (:5571) に直接 ZMQ 接続してイベントストリームを受信する
  (`sonic-gnmi/gnmi_server/events_client.go`)

## 参照コード

- `sonic-swss-common/common/events_common.cpp:38-83` — `read_init_config()`
- `sonic-swss-common/common/events_common.h:129-130` — `INIT_CFG_PATH`, `CFG_EVENTS_KEY`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:656-704` — `run_eventd_service()`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:172-225` — `stats_collector::start()`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp:240-296` — `stats_collector::run_collector()`
