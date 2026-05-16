# ALARM テーブル — Phase B 書込み順依存スキャンノート

対象テーブル: `ALARM` (EVENT_DB index 6 — CONFIG_DB ではない点に注意)
主要 Consumer: `eventd` (`sonic-buildimage/src/sonic-eventd/src/eventd.{h,cpp}`) + `zmqproxy` (eventd コンテナ内)
主要 Publisher: アプリ各種 (`events_publish()` 経由) + healthd (`sonic-buildimage/src/system-health/health_checker/*.py`) + supervisord proc-exit-listener
スキャン範囲: `eventd_proxy::init()`, eventd main run loop, `stats_collector::start/run_writer`, `events.cpp` (`events_init_publisher` / `echo handshake`), system-health の event publisher 経路、`schema.h` の EVENT_DB 定数

---

## ALARM テーブル書込パスの全体構造

```
[t=0] eventd プロセス起動
       │
       ▼
  ┌────────────────────────────────────────────────────────────┐
  │ eventd_proxy::init()                                       │
  │   1. ZMQ context 生成                                       │
  │   2. zmq_socket(ZMQ_XSUB) ← capture socket bind            │
  │   3. zmq_socket(ZMQ_XPUB) ← bind                           │
  │   4. zmq_socket(ZMQ_PUB)  ← capture                        │
  │   5. zmq_proxy(XSUB, XPUB, CAPTURE) を別 thread で起動     │
  └────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌────────────────────────────────────────────────────────────┐
  │ stats_collector::start()                                   │
  │   - COUNTERS_DB connector 取得                              │
  │   - run_writer thread 起動 (10ms 周期で COUNTERS_EVENTS flush) │
  │   - 例外発生時は catch して run_writer 未起動 (本体は継続) │
  └────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌────────────────────────────────────────────────────────────┐
  │ eventd main loop                                           │
  │   - events_init_publisher() (eventd 自身が heartbeat 用)    │
  │   - event_receive() ループ ← XPUB から受信                  │
  │   - heartbeat publish (2 秒周期)                            │
  └────────────────────────────────────────────────────────────┘
       │
       ▼ (publisher 側は別プロセス・別タイミングで接続)
  ┌────────────────────────────────────────────────────────────┐
  │ app (healthd / pmon / supervisord-listener 等)              │
  │   1. events_init_publisher()                                │
  │   2. echo handshake (EVENTS_SERVICE_TIMEOUT_MS_PUB 内に成立)│
  │   3. event_publish(RAISE_ALARM, ...)                        │
  └────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌────────────────────────────────────────────────────────────┐
  │ eventd Alarm Consumer 分岐                                  │
  │   - RAISE_ALARM → HSET EVENT_DB ALARM|<id> + HINCRBY ALARM_STATS │
  │   - CLEAR_ALARM → DEL  EVENT_DB ALARM|<id> + HINCRBY ALARM_STATS │
  │   - ACK_ALARM   → HSET acknowledged=true                    │
  │   - UNACK_ALARM → HSET acknowledged=false                   │
  └────────────────────────────────────────────────────────────┘
```

ALARM テーブルは CONFIG_DB 経由の SubscriberStateTable ではなく ZMQ XPUB/XSUB 経由の push 配信であり、Redis 側に keyspace 通知購読者は存在しない。順序依存は **(a) socket bind / handshake 時系列**、**(b) publisher 側 DB 依存の起動順**、**(c) 同一 action 内での複数テーブル連続書込** の 3 層に分かれる。

---

## 検出した順序依存・タイミング依存

### 1. zmqproxy bind が publisher の echo handshake より先行必須 (XSUB/XPUB/CAPTURE)

- `eventd_proxy::init()` (`sonic-eventd/src/eventd.cpp:77-107`) は ZMQ_XSUB → ZMQ_XPUB → ZMQ_PUB (capture) の順に `zmq_bind` を行い、いずれかが失敗すると eventd プロセス起動が失敗する。
- publisher 側 `events_init_publisher()` (`sonic-swss-common/common/events.cpp:97-109`) は echo socket で handshake を行い、`EVENTS_SERVICE_TIMEOUT_MS_PUB` 内に成立しなければ publisher 取得失敗 (`SWSS_LOG_ERROR "Failed to init event service rc=%d"`)。
- **順序依存**: publisher (app / healthd / supervisord-listener) は eventd の XSUB が bind 完了した後に `events_init_publisher()` を呼ばないと echo handshake が timeout し、以後 ALARM publish が一切できない。
- **緩和策**: SONiC では `eventd.service` を systemd 経路で先に起動し、`docker-eventd` がレディになってから他コンテナの publisher が接続するシーケンス。それでも echo handshake 前に `event_publish()` を呼ぶと ZMQ PUB 仕様により **silent drop** される (`events.cpp:103` コメント "Any message published before connection establishment is dropped.")。RAISE_ALARM がカウントもログも残さず消える可能性がある。
- evidence: `sonic-eventd/src/eventd.cpp:77-107`; `sonic-swss-common/common/events.cpp:97-109`

### 2. event profile (`default.json`) ロードが publisher の RAISE_ALARM 発火より先行必須

- ALARM 行の `type-id` / `severity` / `action` フィールドは publisher が指定する `(source, tag)` をキーに event profile JSON で解決される (HLD §3.1.2 / §3.1.3)。
- `sonic-events-eventd.heartbeat` / `sonic-events-host.process-not-running` / `sonic-events-host.liquid-cooling-leak` / `sonic-events-host.process-exited-unexpectedly` 等のキーが profile に存在しないと severity / action が解決されず RAISE が無効化される (本ページ Phase C「event profile キーへの暗黙参照」参照)。
- **順序依存**: ベンダ・モジュール側のイメージビルド時に profile JSON が `default.json` へ merge されていなければ、対応するタグの RAISE_ALARM が静かに無視される。実行時の CONFIG_DB 書き込みでは復旧不可。
- **緩和策**: profile は image build 時に静的に確定する設計。runtime での順序問題ではなく、image-construction 時の構成順序問題として現れる。
- evidence: `sonic-eventd/src/eventd.cpp:46-47,291`; HLD `event-alarm-framework.md:Section 3.1.2 / 3.1.3`; `system-health/health_checker/service_checker.py:15-16,380-384`

### 3. healthd publisher は CONFIG_DB:DEVICE_METADATA / FEATURE / STATE_DB:FEATURE を先読みする (起動時依存)

- healthd (`sysmonitor.py:39-41,152,217-219` / `service_checker.py:321-323`) は ALARM publish 前に以下を起動時に読む:
  - `CONFIG_DB:DEVICE_METADATA` 全フィールド (device_config レンダリング)
  - `CONFIG_DB:FEATURE` (`get_table`) — 監視対象 feature の取捨選択
  - `STATE_DB:FEATURE` (`SubscriberStateTable`) — feature の up/down 追従
- **順序依存**: これらが CONFIG_DB / STATE_DB に存在しない状態で healthd が起動すると、`sonic-events-host` 系の RAISE_ALARM が発火せず ALARM テーブルが空のまま。
- **緩和策**: 起動順は systemd unit の `After=` 依存と `database` コンテナ起動が CONFIG_DB を populate する init 経路で保証される。runtime 中の `FEATURE` 追加は SubscriberStateTable 経路で追従される。
- 影響範囲: ALARM テーブル**自体**ではなく ALARM publisher の有効化条件。eventd 側はこの順序を強制しない (eventd は publisher の存在を前提にしない)。
- evidence: `system-health/health_checker/sysmonitor.py:39-41,152,217-219`; `system-health/health_checker/service_checker.py:321-323`

### 4. stats_collector start の COUNTERS_DB 接続失敗は ALARM 本体に影響しない (隔離設計)

- `stats_collector::start()` (`sonic-eventd/src/eventd.cpp:177-184`) は COUNTERS_DB connector 取得失敗を catch し、`run_writer` thread を起動しないまま例外吸収する。
- **順序依存**: COUNTERS_DB (redis index 2) の起動が eventd より遅れても、ALARM テーブル (EVENT_DB) への HSET/DEL は別経路で動作する。停止するのは `COUNTERS_EVENTS` カウンタの周期 flush のみ。
- 副作用: eventd 落ち / COUNTERS_DB 落ちの期間中、`missed_internal` / `missed_to_cache` / `missed_by_slow_receiver` 等のカウンタは進まないため、後追いで欠損を可視化できない (本ページ Phase D「eventd プロセス落ち時の挙動」参照)。
- evidence: `sonic-eventd/src/eventd.cpp:177-184,205-210`

### 5. RAISE_ALARM 1 アクション内の連続書込順 — ALARM 行 HSET → ALARM_STATS HINCRBY → (CLEAR時のみ) DEL

- Alarm Consumer は受信 action ごとに以下を**順次同期** Redis コマンドで発行する (HLD §3.1.4 / §3.1.5):
  - RAISE_ALARM: `HSET EVENT_DB ALARM|<id> ...` → `HINCRBY EVENT_DB ALARM_STATS|state <severity> 1`
  - CLEAR_ALARM: `DEL EVENT_DB ALARM|<id>` → `HINCRBY ALARM_STATS|state <severity> -1`
- **順序依存**: 同一 action 内で ALARM 本体行と ALARM_STATS カウンタを連続書込するが、Redis MULTI/EXEC でラップされていない。ALARM HSET 成功 + ALARM_STATS HINCRBY 失敗 (Redis 切断瞬間など) という不整合が原理的に発生し得る (Phase D 失敗節で言及した「eventd 側で Redis 例外の明示捕捉なし」が該当)。
- **緩和策**: 不整合が観測されるのは Redis 切断瞬間のごく短期間のみで、Redis 例外発生時は eventd プロセス自体が abort → コンテナ再起動 (`supervisor-proc-exit-listener-rs`) で healthy 状態に回帰。ただし**再起動後も ALARM テーブルは空からの再開**であり、再 RAISE は publisher 側に依存する。
- pmon System LED は `ALARM_STATS` を読むため、瞬間不整合中は LED 色判定がずれる可能性 (実害は秒未満)。
- evidence: `sonic-eventd/src/eventd.cpp` (Redis 例外明示 catch なし); `dockers/docker-eventd/supervisord.conf:47-57`; `dockers/docker-eventd/critical_processes:1`

### 6. heartbeat publisher 初期化は eventd 自身の zmqproxy bind 後 — `sonic-events-eventd.heartbeat` 自参照ループ

- eventd 自身が 2 秒周期で `sonic-events-eventd.heartbeat` を publish する (`eventd.cpp:46-47,291`)。
- この publish は eventd プロセス内の `events_init_publisher()` 経由で行われ、当然ながら eventd 自身の zmqproxy XSUB が bind 完了している必要がある (`eventd_proxy::init()` → 後段で `events_init_publisher()`)。
- **順序依存**: `eventd_proxy::init()` 失敗時はそもそもプロセス起動が失敗するため矛盾は起きないが、`init()` 成功直後・heartbeat publisher 取得前に外部 publisher が接続して RAISE_ALARM を発火するシーケンスでは、heartbeat と外部 ALARM が同じ XSUB に多重化される。順序的な競合は ZMQ socket が単純な FIFO なので問題ない (ZMQ_XSUB の subscribe-pattern 仕様)。
- 関連: heartbeat publish 失敗時もループ継続 (`SWSS_LOG_ERROR "Failed to publish heartbeat rc=%d"` のみ) なので、heartbeat が出ない期間 = eventd が ZMQ recv も止まっている期間に近い。heartbeat 不在は外部からの ALARM 飢餓の早期検知に使える。
- evidence: `sonic-eventd/src/eventd.cpp:46-47,265-294`

### 7. CLEAR_ALARM の対応 RAISE 先行依存 — lookup map に無いと no-op

- Alarm Consumer は内部 lookup map (`<type-id, resource> → <id>`) を保持し、CLEAR_ALARM 受信時にここから `<id>` を解決して `DEL ALARM|<id>`。
- 対応する RAISE_ALARM がない (= lookup map にエントリ無し) 状態で CLEAR_ALARM を受けると **no-op** (本ページ Phase D「ALARM 書込 / Redis 側」参照)。
- **順序依存**: publisher 側のリブートで内部状態を失った場合、再起動後に CLEAR_ALARM を送っても eventd 側 (lookup map) と一致しないため、ALARM テーブル上の古い RAISE エントリが消えずに残る可能性。eventd 自身が落ちると lookup map も消えるため逆方向 (RAISE 再送 → 重複行) も問題になる。
- **緩和策**: 同一 `(type-id, resource, text)` の連続 RAISE は eventd 内キャッシュで flooding 防止される (HLD §3.1.3)。CLEAR の取り残しは `show alarm` で可視化されるため、運用上は人手で ACK/clear する。eventd 内 lookup map の永続化は未実装。
- evidence: HLD `event-alarm-framework.md:Section 3.1.3, 3.1.4.2`

### 8. capture cache 書込で bad_alloc 発生時は CAP_STATE_LAST fallback — ALARM 本体は影響なし

- capture cache (内部リングバッファ) の `push_back` で `std::bad_alloc` が発生すると、catch して `CAP_STATE_LAST` に遷移し、以降は**最終 1 件のみ保持**するモードに fallback する (`eventd.cpp:518-526`)。
- **順序依存**: cache の状態遷移は ALARM テーブルへの書込経路と独立。`CAP_STATE_LAST` モードに入っても ALARM HSET/DEL は通常通り動作する。
- 影響: 復旧後に過去履歴 (cache) を吸い上げる subscriber が居る場合、cache 縮退モード中の event は欠落する。
- evidence: `sonic-eventd/src/eventd.cpp:518-526`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | eventd の zmqproxy XSUB/XPUB/CAPTURE bind → publisher の echo handshake | **強制先行** (handshake timeout 時 publisher 取得失敗 / handshake 前の publish は silent drop) | systemd 起動順 + `docker-eventd` ready 待ちで保証 |
| 2 | event profile (`default.json`) に `(source, tag)` キーが存在 → publisher の RAISE_ALARM 発火 | **強制先行** (image build 時に静的解決) | runtime での復旧不可・image 構成順序問題 |
| 3 | CONFIG_DB:DEVICE_METADATA / FEATURE + STATE_DB:FEATURE → healthd publisher 起動 | 推奨先行 (欠如時 `sonic-events-host` 系 RAISE 発火せず) | systemd `After=` + SubscriberStateTable 後追い |
| 4 | COUNTERS_DB 起動 → eventd の stats_collector run_writer | 緩い依存 (失敗時はカウンタのみ停止・ALARM 本体無影響) | 例外 catch で eventd 本体は継続 |
| 5 | 同一 RAISE_ALARM 内 — `HSET ALARM` → `HINCRBY ALARM_STATS` | 同期順 (MULTI/EXEC 無し → Redis 切断瞬間に不整合可能) | eventd abort + コンテナ再起動で healthy 回帰 (テーブルは空から再開) |
| 6 | eventd 自身の zmqproxy bind → heartbeat publisher 初期化 | プロセス内自己順序 (init 失敗時はプロセス起動失敗で矛盾せず) | heartbeat 不在は ALARM 飢餓の早期検知信号 |
| 7 | publisher の RAISE_ALARM → 対応 CLEAR_ALARM (lookup map 先行必須) | **対応先行必須** (RAISE 不在の CLEAR は no-op) | flooding 防止キャッシュで重複 RAISE は黙棄・lookup map 永続化なし |
| 8 | capture cache 状態遷移 (`CAP_STATE_*`) | ALARM 書込と独立 | bad_alloc 時 `CAP_STATE_LAST` fallback・本体無影響 |

---

## キーパースペクティブ

- ALARM テーブルは **CONFIG_DB 派生テーブルではなく EVENT_DB の push 配信テーブル** であるため、CONFIG_DB 系の「daemon が SubscriberStateTable で待つ → 順序が緩い」モデルが当てはまらない。
- 順序依存の本質は **(a) ZMQ XPUB/XSUB の bind / handshake 時系列**、**(b) publisher 側 (healthd 等) が CONFIG_DB / STATE_DB を起動時に読む依存**、**(c) 同一 action 内での非トランザクショナルな複数 Redis 書込** の 3 層構造。
- healthd と eventd は**互いに購読しない独立サブシステム**であり、ALARM フロー上は「healthd が publisher として一方向に流す」関係のみ。failure 伝播は systemd / supervisord 側の再起動経路で吸収される。
- capability 公開順序という概念は ALARM 領域には存在しない (eventd 側で動的 capability ネゴシエーションをしないため)。代わりに event profile JSON の **image build 時静的解決** が同等の役割を果たす。

<!-- evidence: sonic-buildimage/src/sonic-eventd/src/eventd.cpp:46-47,77-107,177-184,205-210,265-294,291,518-526; sonic-swss-common/common/events.cpp:97-109,103; sonic-buildimage/src/system-health/health_checker/sysmonitor.py:39-41,152,217-219; sonic-buildimage/src/system-health/health_checker/service_checker.py:15-16,321-323,380-384; sonic-buildimage/dockers/docker-eventd/supervisord.conf:47-57; sonic-buildimage/dockers/docker-eventd/critical_processes:1; SONiC/doc/event-alarm-framework/event-alarm-framework.md:Section 3.1.2,3.1.3,3.1.4,3.1.4.2,3.1.5 -->
