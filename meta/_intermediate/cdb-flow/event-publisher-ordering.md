# event-publisher ordering 調査メモ

## 調査対象
- `/etc/sonic/init_cfg.json` の `"events"` キー
- `sonic-net/sonic-swss-common/common/events_common.cpp`
- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.cpp`

## 主要な発見

### 1. init_cfg.json は起動時一回読み込み（遅延初期化）

`get_config(key)` (`events_common.cpp:74-83`) は `cfg_data.empty()` を確認し、
空であれば `read_init_config(INIT_CFG_PATH)` を呼ぶ lazy pattern。
これは `eventd_proxy::init()` 内の `zmq_bind()` 呼び出し（L80-93）で最初に参照される。

**結論**: `eventd` コンテナ起動前に `init_cfg.json` を書き込む必要がある。
起動後の `init_cfg.json` 変更は `eventd` を再起動するまで無効。

### 2. `eventd` 内部の起動順序 (`run_eventd_service`, eventd.cpp:656-)

1. `zmq_ctx_new()` — ZMQ コンテキスト生成
2. `get_config_data(CACHE_MAX_CNT, MAX_CACHE_SIZE)` — **ここで init_cfg.json を初読み** (L674)
3. `proxy->init()` — XSUB(:5570)/XPUB(:5571)/CAPTURE(:5573) ソケット bind (L680)
4. `service.init_server(zctx)` — REQ_REP(:5572) ソケット bind (L682)
5. `stats_instance.start()` — stats collector スレッド起動 (L684)
6. `capture->set_control(INIT_CAPTURE/START_CAPTURE)` — イベントキャッシュ開始 (L695-701)
7. `sleep(200ms)` — stats スレッド初期化完了待ち (L703)
8. メインループ (`event_service` REQ/REP 処理)

### 3. パブリッシャー・サブスクライバーとの順序依存

publishers (`events_init_publisher()`) および subscribers (`events_init_subscriber()`) は
`get_config(XSUB_END_KEY/XPUB_END_KEY)` で取得したエンドポイントに `zmq_connect()` する。
`zmq_connect()` は lazy であり、eventd が bind 完了前でも失敗しない (ZMQ の設計)。
ただし eventd の bind 前にメッセージを publish しても proxy が未起動のため消失する。

### 4. telemetry コンテナとのキャッシュハンドシェイク

`capture_service` がイベントキャッシュを開始 (`START_CAPTURE`) してから
telemetry コンテナが `EVENT_CACHE_STOP_SUBCRIBER` を送って収集するまでの間、
イベントはキャッシュバッファに保持される。
telemetry コンテナは自身の起動後に `event_service` REQ/REP (:5572) へ接続して
`INIT_CAPTURE` → `START_CAPTURE` → `EVENT_CACHE_READ` → `STOP_CAPTURE` シーケンスを送る。

## 書き込み順序依存まとめ

| # | 依存関係 | 方向 | 備考 |
|---|---------|------|------|
| 1 | `init_cfg.json ["events"]` → `eventd` 起動 | **先行必須** | 起動後変更は restart まで無効 |
| 2 | `eventd` ZMQ bind 完了 → パブリッシャーのメッセージ送信 | **先行推奨** | ZMQ connect 自体は lazy; メッセージは proxy 起動前に消失 |
| 3 | `eventd` 全サービス起動 (sleep 200ms 後) → telemetry コンテナ起動 | **推奨** | 早期起動だとキャッシュ開始前イベントを取りこぼす |
