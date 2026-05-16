# ALARM テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `EVENT_DB` の `ALARM` テーブル（および付帯 `ALARM_STATS` / `EVENT` / `EVENT_STATS`）。

> 注意: ALARM は CONFIG_DB ではなく **EVENT_DB (Redis DB index 6)** に存在する非永続テーブルである (`sonic-swss-common/common/schema.h:552` — `EVENT_CURRENT_ALARM_TABLE_NAME "ALARM"`)。CONFIG_DB の派生テーブルと異なり、書き込み経路・購読経路ともに **ZMQ チャネル経由のイベントフレームワーク** が中核を担う。

## 1. パブリッシュ側 — ZMQ ベース (`events_publish`)

CONFIG_DB / STATE_DB のテーブルとは異なり、ALARM テーブルの書き込みは Redis の `HSET` を直接行うアプリケーションが居ない。代わりに以下の経路を辿る:

```
App (pmon / swss / bgp 等)
   │  events_publish(EVENT_CURRENT_ALARM_TABLE, payload)
   ▼
ZMQ PUB socket (proc-internal)
   │
   ▼
zmqproxy (eventd container)
   │  XPUB/XSUB バックエンド
   ▼
eventd メインループ (events_listen + ZMQ_SUBSCRIBE "")
   │
   ├─ Alarm Consumer ロジック (RAISE/CLEAR/ACK/UNACK)
   │     ├─ HSET ALARM|<id> ...                (Redis EVENT_DB)
   │     ├─ DEL  ALARM|<id>                    (CLEAR 時)
   │     └─ HINCRBY ALARM_STATS|state          (severity 集計)
   │
   └─ EVENT テーブル追記 (40k/30日 上限の循環バッファ)
```

ZMQ proxy・publisher API は `sonic-eventd/src/eventd.cpp` で実装されている (例: 240 行付近 `events_init_publisher(EVENTD_PUBLISHER_SOURCE)` がハートビート送出に使われる publisher 初期化、419 行付近 `zmq_setsockopt(cap_sub_sock, ZMQ_SUBSCRIBE, "", 0)` がキャプチャ用全件 subscribe)。

ALARM Consumer 本体（`RAISE_ALARM` / `CLEAR_ALARM` を受けて `HSET ALARM|<id>` する箇所）は HLD `event-alarm-framework.md` Section 3.1.4.2 に設計が記載されているが、**現時点の `sonic-eventd/src/` には `alarm` 文字列・`ALARM` 操作の実装は存在しない**（`grep -ln "alarm\|ALARM" sonic-eventd/src/*.cpp *.h` で hit なし）。HLD 上は eventd 内のサブモジュールとして動作する想定。

## 2. 購読側 — keyspace 通知ではなく直接 HGETALL / gNMI subscribe

ALARM テーブルの読者は CONFIG_DB のような `ConfigDBConnector.subscribe()` (keyspace 通知 PSUBSCRIBE) を **使わない**。

| 読者 | 取得方法 | コード根拠 |
|------|---------|------------|
| `show alarm` CLI | `sonic-db-cli EVENT_DB keys 'ALARM\|*'` + `hgetall` (snapshot ポーリング) | HLD Section 3.1.7 — Redis 出力例 |
| OpenConfig gNMI/REST (`/openconfig-alarms:alarms`) | translib が EVENT_DB を毎回 HGETALL してマッピング | sonic-mgmt-common 内に `alarm` translation 実装はまだ無く、HLD Section 3.1.6 が将来実装を規定 |
| pmon System LED ロジック | `ALARM_STATS|state` を **STATE_DB ではなく EVENT_DB から hgetall** で参照しカウンタ判定 | HLD Section 3.1.5 |

`SubscriberStateTable` / `ConsumerStateTable` / `NotificationProducer` を ALARM テーブルに張る購読者は SONiC ソース内に存在しない (`grep -rln "ALARM\|EVENT_CURRENT_ALARM_TABLE_NAME" .cache/sonic-sources/sonic-swss/ sonic-utilities/ sonic-gnmi/` で hit なし)。これは ALARM テーブルが「**スナップショット型テーブル** (ある瞬間のアクティブアラームの集合)」として設計されており、差分通知よりも全件取得が自然な利用パターンであるため。

## 3. system-health (healthd) との関係

ユーザの誤解を避けるため明示する: `src/system-health/health_checker/` (= healthd) は ALARM テーブルを **購読していない**。healthd の購読対象は以下のみ:

- `STATE_DB` の `FEATURE` テーブル (`SubscriberStateTable(state_db, "FEATURE")` — `sysmonitor.py:41`)
- systemd の D-Bus シグナル (`Manager.Subscribe()` — `sysmonitor.py:97`)

healthd は独自の `system_health_monitoring_config.json` ベースのチェックを実行し、結果を `STATE_DB:SYSTEM_HEALTH_INFO` に書き出す。Event/Alarm Framework (eventd) と healthd は **独立したサブシステム** であり、現状双方向の購読リンクは無い。

## 4. dbId と Redis 通知設定

| 項目 | 値 |
|------|---|
| DB index | 6 (`EVENT_DB`) — `database_config.json` 既定 |
| 永続性 | 無 (cold/warm/fast reboot で全件消失) |
| `notify-keyspace-events` | EVENT_DB ではデフォルト無効 (keyspace 通知に依存する購読者が居ないため) |
| エントリ TTL | 無 (eventd の CLEAR_ALARM 受信時に明示 `DEL`) |
| エントリ ID | `<32bit time_t><5桁連番>` の uint64 — eventd Alarm Consumer が採番 |

## 5. キー単位ディスパッチ

ALARM テーブルへの書き込みは **eventd 内部の Alarm Consumer 1 個所のみ** が行う。CONFIG_DB のような複数ハンドラ分岐は無く、入力イベント `action` フィールドのみで分岐する:

| ZMQ 受信 `action` | Alarm Consumer の Redis 操作 |
|------------------|-------------------------------|
| `RAISE_ALARM`    | `HSET ALARM\|<new id> ...`、`acknowledged=false` 初期化、`HINCRBY ALARM_STATS\|state <severity> 1` |
| `CLEAR_ALARM`    | lookup map から `<id>` 解決 → `DEL ALARM\|<id>`、`HINCRBY ... -1` |
| `ACK_ALARM`      | `HSET ALARM\|<id> acknowledged true acknowledge-time <now>` + STATS 補正 |
| `UNACK_ALARM`    | `HSET ALARM\|<id> acknowledged false acknowledge-time <now>` + STATS 補正 |

`lookup map` (id ↔ type-id+resource) は eventd プロセスのメモリ上に保持され、リブートで失われる。これが「リブート後 ALARM テーブルが空」になる根本理由。

## 6. flooding 防止 (重複 RAISE の黙棄)

Alarm Consumer は直近に処理した RAISE のキャッシュ (type-id + resource + text のハッシュ) を保持し、同一値の連続 RAISE は **テーブル書き込みを行わずに黙棄**する (HLD Section 3.1.4.2 の "Duplicate suppression")。これにより、フラッピング中のリソースが ALARM テーブルを汚さない。CLEAR_ALARM は黙棄対象外で、対応 RAISE が消えた状態で来た場合は lookup map ミスで no-op になる。

## 7. NotificationProducer / 派生テーブル非使用の確認

- `NotificationProducer` で ALARM 関連の channel publish を行う箇所は SONiC ソース内に無し。
- ALARM の派生テーブル (ALARM_STATS / EVENT / EVENT_STATS) はすべて eventd 内部の同じトランザクションで更新され、外部の orchagent / syncd 等を経由しない。
- 結論: ALARM は **App → ZMQ → eventd Alarm Consumer → EVENT_DB (ALARM / ALARM_STATS)** の一方向。読者は **EVENT_DB を polling / HGETALL** する形式で、keyspace 通知や channel publish には乗らない。

## 8. CONFIG_DB との設計差分まとめ

| 観点 | CONFIG_DB テーブル (例: AAA) | EVENT_DB ALARM テーブル |
|------|------------------------------|--------------------------|
| 書き込み元 | `sonic-cfggen` / `config` CLI / gNMI Set (HSET 直接) | App が ZMQ `events_publish()` → eventd が HSET |
| 通知方式 | Redis keyspace 通知 (`__keyspace@4__:...`) | ZMQ XPUB/XSUB (eventd zmqproxy) — Redis 通知は非使用 |
| 購読者 API | `ConfigDBConnector.subscribe(table, cb)` + `listen()` | `events_init_subscriber()` (ZMQ) — Redis 側は **HGETALL polling のみ** |
| 永続性 | 永続 (config_db.json から復元) | 非永続 (リブートでクリア) |
| TTL | 無 | 無 (CLEAR で明示 DEL) |

## 9. 参考行番号・パス

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
  - 240 付近: `events_init_publisher(EVENTD_PUBLISHER_SOURCE)` (heartbeat publisher)
  - 244-310: heartbeat スレッド (subscribe→publish ループ — alarm 専用ではない)
  - 419-456: capture socket (`ZMQ_SUBSCRIBE ""` で全 publish を傍受、ALARM 含む)
- `sonic-buildimage/src/sonic-eventd/src/eventd.h` — ZMQ proxy 構造体定義
- `sonic-swss-common/common/schema.h:552` — `EVENT_CURRENT_ALARM_TABLE_NAME "ALARM"`
- `SONiC/doc/event-alarm-framework/event-alarm-framework.md` Section 3.1.4.2 (Alarm Consumer), 3.1.5 (System LED), 3.1.7 (Redis schema)
- `sonic-buildimage/src/system-health/health_checker/sysmonitor.py:41,97` — **ALARM とは無関係** の healthd 購読対象 (FEATURE / D-Bus) — 読者の混同を避けるため参考掲載
