# HEARTBEAT — Phase D 失敗挙動 調査証跡

## 調査対象

- `sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener`
- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-buildimage/src/sonic-eventd/src/eventd.h`

## 失敗パス一覧

### 1. `alert_interval` フィールド欠落時のフォールバック

`supervisor-proc-exit-listener:124-143` の `load_heartbeat_alert_interval()` は `alert_interval` が存在しない場合（`None`）をスキップし、`get_heartbeat_alert_interval()` がデフォルト定数 `ALERTING_INTERVAL_SECS = 60` 秒を返す。
フィールドが欠落していてもクラッシュせず、60 秒フォールバックで監視が継続される。

### 2. `heartbeat_interval` フィールド欠落時の挙動

`supervisor-proc-exit-listener` は `heartbeat_interval` を読み込まない（`alert_interval` のみ使用）。
eventd 側は CONFIG_DB の `HEARTBEAT` テーブルを直接購読しないため、影響なし。
`heartbeat_interval` フィールドが欠落しても supervisor-proc-exit-listener の動作に影響はない。

### 3. CONFIG_DB 接続失敗

`load_heartbeat_alert_interval()` 内の `ConfigDBConnector` 接続試行に例外が発生した場合は呼び出し元でキャッチされず、スクリプト全体が例外終了する可能性がある。
ただし `heartbeat_alert_interval_initialized` は `False` のままのため、次回の `get_heartbeat_alert_interval()` 呼び出しで再試行される。

### 4. eventd publish 失敗

`eventd.cpp:291-293`：`event_publish()` が非ゼロを返した場合、`SWSS_LOG_ERROR("Failed to publish heartbeat rc=%d")` を syslog に記録して継続する。heartbeat publish の失敗は eventd プロセスをクラッシュさせない。

### 5. heartbeat publisher 初期化失敗

`eventd.cpp:241-242`：`events_init_publisher()` が NULL を返した場合は `RET_ON_ERR` マクロにより eventd プロセスが終了する（fatal エラー）。

### 6. ZeroMQ サブスクライバ初期化失敗

`eventd.cpp:244-245`：`events_init_subscriber()` が NULL の場合も `RET_ON_ERR` で eventd が終了する。

### 7. プロセス heartbeat 無応答（stuck 検出）

`supervisor-proc-exit-listener:246-249`：監視対象プロセスが `threshold` 秒以上 heartbeat を送信しない場合、`generate_alerting_message(process, "stuck", elapsed_mins, syslog.LOG_WARNING)` で syslog に WARNING を記録する。プロセス強制終了や自動再起動は行わない（LOG_WARNING 通知のみ）。

### 8. `heartbeat_alert_interval_initialized` がセットされるが HEARTBEAT テーブルが空の場合

テーブルが空でも `heartbeat_table_initialized = True` にセットし、以後の全プロセスはデフォルト 60 秒フォールバックを使用する。

## 証跡

- `supervisor-proc-exit-listener:42` `ALERTING_INTERVAL_SECS = 60`
- `supervisor-proc-exit-listener:124-135` `load_heartbeat_alert_interval()`
- `supervisor-proc-exit-listener:137-143` `get_heartbeat_alert_interval()`
- `supervisor-proc-exit-listener:246-249` stuck 検出ループ
- `eventd.cpp:291-293` heartbeat publish 失敗ログ
- `eventd.cpp:241-245` 初期化失敗 RET_ON_ERR
