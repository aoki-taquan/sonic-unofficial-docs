# ALARM テーブル — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-alarm-table)

ソース:
- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-net/sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-net/sonic-buildimage/dockers/docker-eventd/supervisord.conf`
- `sonic-net/sonic-buildimage/dockers/docker-eventd/critical_processes`
- `sonic-net/sonic-swss-common/common/events.cpp`
- `sonic-net/sonic-buildimage/src/system-health/health_checker/`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ALARM テーブルは EVENT_DB (Redis DB index 6) 上のスナップショット型テーブルで、書込パスは
`App → events_publish() → ZMQ XSUB/XPUB → eventd Alarm Consumer → HSET/DEL` となる。
このパスのどこで障害が起きるかにより、観測される挙動が異なる。

### 書込失敗系（publisher 側 / events_publish 経路）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `events_publish()` の str_data が `EVENT_MAXSZ` 超過 | `EventPublisher::send_evt` | サイズ警告のみで **そのまま publish 継続** (drop しない) | `SWSS_LOG_ERROR` "event size (%d) > expected max(%d). Still published." | `sonic-swss-common/common/events.cpp:146-149` |
| eventd 未起動状態で publisher が初期化 | `EventPublisher::init` の `echo_send` | `init_client` が `EVENTS_SERVICE_TIMEOUT_MS_PUB` でタイムアウト → `rc != 0` → publisher 取得失敗 | `SWSS_LOG_ERROR` "Failed to init event service rc=%d" | `events.cpp:97-98` |
| publisher 接続確立前に最初の publish が走る | `EventPublisher::init` コメント | echo handshake で接続確立を待つが、**確立前のメッセージは drop** (ZMQ PUB 仕様) | コメント "Any message published before connection establishment is dropped." | `events.cpp:100-107` |
| `zmq_message_send` 失敗 | `send_evt:160-161` | `rc != 0` で戻る → 呼び出し元 `publish()` も失敗 rc を返す | `SWSS_LOG_ERROR` "failed to send for tag %s" | `events.cpp:160-163, 208-211` |

### eventd 落ち / ZMQ 切断系（broker 側）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `zmqproxy` (eventd_proxy) の `zmq_bind` 失敗 (`XSUB_END_KEY` / `XPUB_END_KEY` / `CAPTURE_END_KEY`) | `eventd_proxy::run` | init 失敗 → `m_init_result = 1` → `eventd_proxy::init()` が非 0 を返す → `eventd` プロセス起動失敗 | `RET_ON_ERR` ログ "Failing to bind XSUB to %s" / "Failing to bind XPUB to %s" / "Failing to bind capture PUB to %s" | `eventd.cpp:77-107` |
| `zmq_socket` (XSUB/XPUB/PUB) 取得失敗 | 同上 | プロキシ起動失敗 → eventd 全体が機能停止 | "failing to get ZMQ_XSUB/XPUB/PUB socket" | `eventd.cpp:78,84,90` |
| eventd プロセス異常終了 (crash / OOM など) | supervisord | **`autorestart=false`** だが、`critical_processes` に `eventd` が登録されているため `supervisor-proc-exit-listener` が PROCESS_STATE_EXITED を受け取り **コンテナごと再起動** | listener が container 再起動を発火 | `dockers/docker-eventd/supervisord.conf:47-57`, `critical_processes:1` |
| eventd 再起動中の publish | publisher 側 | `zmq_message_send` は ZMQ ソケットキューにバッファされるが、eventd 再起動完了前に publisher 側の HWM を超えると **drop** (subscriber 未接続のため) | (publisher 側でログなし、`COUNTERS_EVENTS:missed_*` カウンタには現れない) | `events.cpp:103` コメント "Any message published before connection establishment is dropped." |
| `event_receive` (stats_collector) で例外 | `stats_collector::run_collector:265-274` | `rc = -1` にセットし `SWSS_LOG_ERROR` 出力後 **ループ継続** (heartbeat 経路で復帰試行) | `SWSS_LOG_ERROR` "Receive event failed with %s" | `eventd.cpp:265-274` |
| `event_receive` が rc < 0 を返却 | 同上 | エラーログのみ・ループ継続。hb_cntr が進めばハートビート publish 試行 | `SWSS_LOG_ERROR` "event_receive failed with rc=%d; stats:published(%lu)" | `eventd.cpp:284-287` |
| heartbeat publish 失敗 | `run_collector:291-294` | エラーログのみ・カウンタは進めない・ループ継続 | `SWSS_LOG_ERROR` "Failed to publish heartbeat rc=%d" | `eventd.cpp:291-294` |
| eventd shutdown 中に in-flight event がある | `run_collector` 末尾コメント | キャッシュ内の数件は **欠落許容** (設計上の割り切り)。「critical shutdown」扱いで複雑な救済は実装しない | コメント "A shutdown could lose messages in cache." | `eventd.cpp:302-308` |

### ALARM 書込失敗系（Alarm Consumer / Redis 側）

ALARM Consumer の本体実装は `sonic-buildimage/src/sonic-eventd/src/` 配下には存在せず、
HLD (event-alarm-framework.md §3.1.4) で挙動が規定されている。Redis (`HSET ALARM|<id>`) 自体の
失敗は eventd プロセス内の `swss::Table::set()` が C++ 例外を投げるルートのみであるが、
キャッチは確認できず crash → コンテナ再起動経路に合流する。

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| Redis サーバ (redis-server) ダウン中の `HSET ALARM|<id>` | `swss::Table::set` (内部の `RedisCommand` 経由) | `redis_command()` が `RedisReply` ctor で例外を投げる。eventd でこの例外は明示捕捉されておらず、プロセスが abort → supervisord listener 経路でコンテナ再起動 | (例外メッセージ — sonic-swss-common 側で記録) | `eventd.cpp` 全体に Redis 例外 try/catch なし; `stats_collector::start:180-184` で `DBConnector` のみ catch |
| `stats_collector` 起動時に `COUNTERS_DB` connector 取得失敗 | `stats_collector::start:177-184` | 例外を catch して `LOG_ERROR` 出力後 `RET_ON_ERR` で start 中断 → 統計書込スレッド (`run_writer`) は起動しない。**ALARM テーブル本体への書込は影響を受けない** (主経路は別) | `SWSS_LOG_ERROR` "Unable to get DB Connector, e=(%s)" | `eventd.cpp:178-184` |
| 同一 `type-id` + `resource` + `text` の連続 RAISE_ALARM | Alarm Consumer 内キャッシュ (HLD §3.1.3) | 直近キャッシュと一致した場合 **黙棄** (重複エントリ抑止)。`ALARM_STATS` も増えない | (なし) | HLD `doc/event-alarm-framework/event-alarm-framework.md` §3.1.3 |
| CLEAR_ALARM を対応する RAISE なしで受信 | Alarm Consumer の lookup map | map にエントリなし → DEL を発行せずに **no-op** | (なし) | HLD §3.1.4.2 |
| キャッシュ書込時の `bad_alloc` (capture_service の cache_events) | `capture_service::run:518-526` | 例外捕捉して `LOG_ERROR` 出力後 `CAP_STATE_LAST` に fallback (最終 1 件のみ保持)。**ALARM 本体への影響なし** (capture は CLI からの `show event capture` 経由のみ) | `SWSS_LOG_ERROR` "Cache save event failed with %s events:size=%d" | `eventd.cpp:518-526` |

### 永続性 / 復旧

| 条件 | 挙動 | evidence |
|---|---|---|
| cold/warm/fast reboot | ALARM テーブルは EVENT_DB 上の **非永続データ** で全件消失。`ALARM_STATS` もリセット。RAISE 側アプリは再 RAISE が必要 | HLD §3.1.7 |
| eventd コンテナ再起動 | `events_init_publisher` を保持している publisher プロセスは再接続が必要 (echo handshake から再実行)。再起動完了前の publish は drop | `events.cpp:97-109`, `eventd.cpp` supervisord 経路 |
| Redis 再起動 (database コンテナ再起動) | eventd プロセスが Redis 切断で例外 → abort → supervisord listener がコンテナ再起動を発火 | `eventd.cpp` (Redis 例外捕捉なし), `critical_processes:1` |
| `acknowledged=true` のまま再起動 | リブートで ALARM 全消失するため ACK 状態も失われる | HLD §3.1.7 |

### healthd / system-health との独立性

`src/system-health/health_checker/sysmonitor.py:41,97` の healthd は **ALARM テーブルを購読しない** (購読対象は `STATE_DB:FEATURE` と systemd D-Bus のみ)。
従って ALARM の書込失敗・eventd 落ちは healthd の `SYSTEM_READY`/`ALL_SERVICE_STATUS` には**直接の影響を与えない**。逆に eventd コンテナが落ちると `SYSTEM_READY` の docker service チェックには影響しうるが、これは Event/Alarm Framework としての挙動ではなく container 単位の検出。

### 検出ロジック補足

- **publisher 側 fire-and-forget**: `EventPublisher::publish()` は `echo_receive` で接続確立だけ確認し、以降は `zmq_message_send` の戻り値しか確認しない。eventd 側で受信されたかどうかは publisher から検証できない (lossy by design)。
- **欠落カウントは broker 側でのみ可視**: `COUNTERS_EVENTS` の `missed_internal` / `missed_to_cache` / `missed_by_slow_receiver` は eventd プロセス内 `stats_collector` が周期書込するため、eventd 落ち中はカウンタも止まる。
- **エラー応答ループの設計**: `run_collector` は `event_receive` の例外をすべてループ内で握り潰す。eventd 単体プロセスの可用性優先。
- **critical_processes 経路**: `critical_processes` に `program:eventd` を登録することで、`autorestart=false` でも `supervisor-proc-exit-listener-rs --container-name eventd` がプロセス終了イベントを捕まえコンテナ再起動を発火する設計。

### grep カバレッジ

| 項目 | hit | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` (eventd.cpp) | 9 | `eventd.cpp:182,273,285,293,348,522,604,768,815` |
| `SWSS_LOG_WARN` (eventd.cpp) | 4 | `eventd.cpp:696,731,744,763` |
| `RET_ON_ERR` (proxy bind/socket) | 7 | `eventd.cpp:78,81,84,87,90,93,414` |
| `catch (exception` | 2 | `eventd.cpp:180-183, 268-274` |
| `autorestart=false` (eventd) | 1 | `dockers/docker-eventd/supervisord.conf:51` |
| `critical_processes:eventd` | 1 | `dockers/docker-eventd/critical_processes:1` |
| publisher dropped-before-connect コメント | 1 | `events.cpp:103` |
| Redis 例外捕捉 (eventd 側) | 0 | (主経路の `Table::set` 周辺に try/catch なし → 例外で abort → コンテナ再起動経路) |

<!-- /failure -->
