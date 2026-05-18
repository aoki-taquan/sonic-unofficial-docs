# extended-monitor — Phase B: 書込み順依存 中間ファイル

生成日: 2026-05-18 (q67-f-batch454)

## 調査対象ソース

- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-net/sonic-swss-common/common/events_common.cpp`
- `sonic-net/sonic-swss-common/common/events_common.h`
- `sonic-net/SONiC/doc/event-alarm-framework/event-alarm-framework.md` (section 3.1.2)

## 検出した順序依存

### 1. /etc/sonic/init_cfg.json 読込み → ZMQ エンドポイント bind

`get_config()` は `cfg_data.empty()` のとき `read_init_config(INIT_CFG_PATH)` を呼ぶ
(`events_common.cpp:77-78`)。
`INIT_CFG_PATH = "/etc/sonic/init_cfg.json"` (`events_common.h:129`)。
ファイル不在時は `cfg_default` の値 (`tcp://127.0.0.1:5570~5573`) をそのまま使用。
起動時 1 回のみ読込み。

### 2. ZMQ XPUB/XSUB proxy bind 完了 → event_service.init_server()

`eventd_proxy::run()` が XSUB bind → XPUB bind → capture PUB bind の順に実行し、
全成功後に `m_init_result = 0; m_init_done = true` を設定 (`eventd.cpp:96-97`)。
`eventd_proxy::init()` は `m_init_done` が true になるまで 10ms ポーリングで待機 (`eventd.cpp:64-68`)。
bind 失敗時は `run_eventd_service()` が `goto out` で終了。

### 3. /etc/evprofile/default.json 読込み → EVENT_DB への書込み開始

HLD section 3.1.2: "On initialization, event consumer reads /etc/evprofile/default.json and
builds an internal map of events, called static_event_map. It then subscribes to zmqproxy for events."
プロファイル未読込み状態でイベント受信 → severity/enable 判定不可。

### 4. キャプチャサービス 1 ステップ遷移制約

`set_control()` は `RET_ON_ERR((ctrl - m_ctrl) == 1, ...)` (`eventd.cpp:557`)。
NEED_INIT(0) → INIT_CAPTURE(1) → START_CAPTURE(2) → STOP_CAPTURE(3) の順を厳守。
INIT_CAPTURE 失敗時は `skip_caching = true` となり EVENT_CACHE_READ が全て `resp=-1`
(`eventd.cpp:695-701, 762-765`)。

### 5. EVENT_CACHE_STOP → EVENT_CACHE_READ の強制順序

`capture != NULL` の間は `EVENT_CACHE_READ` が `resp=-1` を返す (`eventd.cpp:767-770`)。
telemetry が `EVENT_CACHE_STOP` を送り、`read_cache()` で内部バッファを swap してから
初めてキャッシュデータが取得可能になる。
`STOP_CAPTURE` 時は `CACHE_DRAIN_IN_MILLISECS` 待機後にスレッド join (`eventd.cpp:598`)。

### 6. stats_collector::start() → COUNTERS_DB 書込み

`run_writer()` スレッドが `COUNTERS_DB` に接続できなかった場合、
`RET_ON_ERR(m_counters_db != NULL, ...)` で `start()` がエラーを返し
`run_eventd_service()` が終了 (`eventd.cpp:684`)。
接続成功後のみ `COUNTERS_EVENTS_TABLE` (`COUNTERS_EVENTS_PUBLISHED` /
`COUNTERS_EVENTS_MISSED_CACHE`) への書込みが開始する。

### 7. heartbeat と通常イベントの非決定的順序

`stats_collector::run_collector()` はイベント受信のたびに `hb_cntr = 0` にリセット
(`eventd.cpp:280`)。通常イベントと heartbeat の到着順は ZMQ ソケットに依存し非決定的。
heartbeat 発行条件: `!m_pause_heartbeat && (m_heartbeats_interval_cnt > 0) && ++hb_cntr >= m_heartbeats_interval_cnt`
(`eventd.cpp:289-295`)。キャッシュ中は `heartbeat_ctrl(true)` で一時停止される。
