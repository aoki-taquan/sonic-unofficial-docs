# extended-monitor — 失敗挙動調査 (Phase D)

## 調査対象

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-swss-common/common/events_common.h` (RET_ON_ERR マクロ)

## 失敗分類

### 致命的失敗 (プロセス終了)

1. `zmq_ctx_new()` 失敗 — L672
2. `get_config_data(CACHE_MAX_CNT) <= 0` — L675
3. `eventd_proxy::init()` 失敗 (ZMQ bind 失敗) — L680, proxy::run L78-93
4. `event_service::init_server()` 失敗 — L682
5. `stats_collector::start()` 失敗 (COUNTERS_DB 接続失敗) — L684
6. `START_CAPTURE` 失敗 — L700
7. `channel_read()` / `channel_write()` 失敗 — L710, L822

### 非致命的失敗 (警告ログ + 継続)

- `INIT_CAPTURE` 失敗: `skip_caching = true` — L695-701
- `event_receive()` 例外: ログ出力後ループ継続 — L266-271
- heartbeat publish 失敗: ログ出力後継続 — L293
- 不正フォーマットイベント: スキップ — L522

### 設定ファイル読み込み失敗

- `/etc/evprofile/default.json` 不在: 空の static_event_map で起動
- `/etc/eventd.json` 不在/不正: 実装の読み込みロジック未確認 (HLD 設計のみ)

## RET_ON_ERR マクロの動作

```c
#define RET_ON_ERR(res, msg, ...)\
    if (!(res)) {\
        int _e = errno; \
        SWSS_LOG_INFO(msg, ##__VA_ARGS__); \
        SWSS_LOG_INFO("last:errno=%d", _e); \
        goto out; }
```

条件が偽の場合、SWSS_LOG_INFO でログ出力後 `goto out` でクリーンアップへジャンプ。
呼び出し元がプロセス終了するかどうかは関数によって異なる。
