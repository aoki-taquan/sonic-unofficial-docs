# HEARTBEAT — 副次 DB 書込 (Phase F) 調査メモ

## 調査対象

- `sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener`
- `sonic-buildimage/src/sonic-supervisord-utilities-rs/src/proc_exit_listener.rs`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`

## 結論

`HEARTBEAT` テーブルの変更に伴う副次 DB 書込は **存在しない**。

- 主消費者 `supervisor-proc-exit-listener` は CONFIG_DB を読み取るのみで、他 DB への書込は行わない
- eventd は CONFIG_DB の `HEARTBEAT` テーブルを直接購読せず、ZeroMQ RPC 経由でのみ heartbeat interval を受け取る
- 副作用はすべて syslog アラート出力（プロセス "stuck" 警告）に閉じる

## 副次 DB 書込の有無

| 対象 DB | 書込 | 根拠 |
|---------|------|------|
| APPL_DB | なし | `supervisor-proc-exit-listener` に Producer/Table 書込呼出なし |
| STATE_DB | なし | 同スクリプトに STATE_DB 参照なし |
| COUNTERS_DB | なし | HEARTBEAT 監視は統計カウンタを持たない |
| ASIC_DB | なし | SAI 非経由（ホストサービス設定） |
| FLEX_COUNTER_DB | なし | 同上 |

## syslog 副作用

- プロセスが `alert_interval` 秒以上 heartbeat を送信しなかった場合: `generate_alerting_message(process, "stuck", ..., LOG_WARNING)` で syslog に WARNING を記録
  - source: `supervisor-proc-exit-listener:249`
- クリティカルプロセスが予期せず終了した場合: `EVENTS_PUBLISHER_TAG = "process-exited-unexpectedly"` を `sonic-events-host` として event publish
  - source: `supervisor-proc-exit-listener:149`, `supervisor-proc-exit-listener:202`

## eventd 側の副作用

- eventd は `event_publish(pub_handle, EVENTD_HEARTBEAT_TAG)` で heartbeat イベントを ZeroMQ 経由で publish
  - source: `eventd.cpp:291`
- これは CONFIG_DB `HEARTBEAT` テーブルの変更とは無関係に行われる定期動作

## 検索証跡

- `supervisor-proc-exit-listener` を `hset`/`set(`/`Producer`/`Notification`/`APPL_DB`/`STATE_DB` で grep → 0 ヒット
- `proc_exit_listener.rs` を `state_db`/`appl_db`/`counters` で grep → 0 ヒット
