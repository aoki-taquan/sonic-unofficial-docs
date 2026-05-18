# event-publisher failure-behavior 調査メモ (Phase D)

調査日: 2026-05-18
対象ファイル: docs/reference/config-db/event-publisher.md
ソース: sonic-buildimage/src/sonic-eventd/src/eventd.cpp, sonic-swss-common/common/events_common.h

## RET_ON_ERR マクロ

`events_common.h:47-54` で定義。条件が偽の場合 `SWSS_LOG_INFO` でログ出力後 `goto out` にジャンプ。
`out:` ラベル配下 (`eventd.cpp:651`) で `ret` を返す。呼び出し元 `run_eventd_service()` はそのまま return し、
`main()` からの再起動ループがあれば再実行、なければプロセス終了。

## 起動失敗シナリオ

| 失敗箇所 | 条件 | 挙動 |
|---------|------|------|
| `zmq_ctx_new()` | NULL 返却 | `RET_ON_ERR` → `goto out` → サービス関数 return → プロセス終了 |
| `cache_max <= 0` | `cache_max_cnt` が 0 以下の値 | `RET_ON_ERR` (L675) → `goto out` |
| `proxy->init()` | ZMQ bind 失敗 (ポート競合等) | `RET_ON_ERR` (L680) → `goto out` |
| `service.init_server()` | REQ/REP socket bind 失敗 | `RET_ON_ERR` (L682) → `goto out` |
| `stats_instance.start()` | COUNTERS_DB 接続失敗 | `RET_ON_ERR` (L684) → `goto out` |
| `capture->set_control(START_CAPTURE)` | 失敗 | `RET_ON_ERR` (L700) → `goto out` |
| `stats_instance.is_running()` | stats スレッド未起動 | `RET_ON_ERR` (L704) → `goto out` |

## capture service 初期化失敗 (soft failure)

`capture->set_control(INIT_CAPTURE) != 0` の場合は `RET_ON_ERR` ではなく `SWSS_LOG_WARN` + `skip_caching = true`。
サービス継続するが、キャッシュ機能が無効になる (L696)。
`EVENT_CACHE_READ` リクエストに `-1` で応答 (L763)。

## ループ内失敗

`service.channel_read()` 失敗: `RET_ON_ERR` (L710-711) → `goto out` → サービス終了
`service.channel_write()` 失敗: `RET_ON_ERR` (L819) → `goto out` → サービス終了
`EVENT_CACHE_START` / `EVENT_CACHE_STOP` で capture が NULL: `SWSS_LOG_WARN` + resp=-1 → サービス継続
`EVENT_CACHE_READ` で capture 未停止: `SWSS_LOG_ERROR` + resp=-1 → サービス継続

## 後片付け (out ラベル以降)

```
out:
    service.close_service();
    stats_instance.stop();
    if (zctx != NULL) { zmq_ctx_term(zctx); }
    if (proxy != NULL) { delete proxy; }
```
リソースはすべて解放される。再起動は systemd/supervisord が担う。
