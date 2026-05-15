---
title: ALARM テーブル (EVENT_DB)
description: "ALARM テーブル — SONiC Event/Alarm Framework が STATE_DB (EVENT_DB) に保持するアクティブアラーム一覧テーブル。eventd が書き込み、gNMI/REST/CLI が参照する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/SONiC
    path: doc/event-alarm-framework/event-alarm-framework.md
    ref: 49bab5baddress-pr-review-comments
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-eventd/src/eventd.h
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  state_db:
    - ALARM
    - ALARM_STATS
    - EVENT
    - EVENT_STATS
  cli:
    - show alarm
---

# ALARM テーブル (EVENT_DB)

## 概要

**ALARM テーブル**は SONiC の Event/Alarm Framework において **アクティブなアラーム（未クリア・未クリア状態のもの）** を一時的に保持するテーブルである[^1]。

> **注意**: このテーブルは **CONFIG_DB ではなく EVENT_DB** (Redis DB index 6) に存在する。
> `schema.h` で `EVENT_CURRENT_ALARM_TABLE_NAME = "ALARM"` と定義されている[^2]。
> リブート時に内容はクリアされる（非永続）。

`eventd` コンテナ内の **Alarm Consumer** が以下の状態遷移でテーブルを管理する:

- `action=RAISE_ALARM` 受信 → エントリ追加、`acknowledged=false` で初期化
- `action=CLEAR_ALARM` 受信 → 対応エントリを削除
- `action=ACK_ALARM` 受信 → `acknowledged=true`、`acknowledge-time` 更新
- `action=UNACK_ALARM` 受信 → `acknowledged=false`、`acknowledge-time` 更新

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  APP["アプリケーション<br/>(pmon/swss/bgp等)"]
  ZMQ["zmqproxy"]
  ED["eventd<br/>Alarm Consumer"]
  EVDB[("EVENT_DB<br/>ALARM")]
  ASTATS[("EVENT_DB<br/>ALARM_STATS")]
  NBI["CLI/REST/gNMI"]
  LED["System LED<br/>(pmon)"]

  APP -- "event_publish(RAISE_ALARM)" --> ZMQ
  ZMQ --> ED
  ED -- "HSET ALARM|id ..." --> EVDB
  ED --> ASTATS
  NBI -- "hgetall" --> EVDB
  ASTATS --> LED
```

!!! note "凡例"
    EVENT_DB 内の ALARM テーブルへの書き込み経路を示す。CONFIG_DB 経由ではない。
<!-- /cdb-mermaid -->

## key 構造

```text
ALARM|<id>
```

`<id>` はシステムが自動採番する uint64 の sequential ID。フォーマット:
```
<32bit UNIX time_t><5桁連番 (00000–99999)>
```

例: `ALARM|1621460371062299951`

## フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|----|-----------|------|
| `id` | uint64 | システム自動採番 | シーケンス ID (key と同値) |
| `revision` | uint64 | `0` | event profile のリビジョン番号 |
| `type-id` | string | — | アラーム識別名 (例: `TEMPERATURE_EXCEEDED`) |
| `text` | string | 静的メッセージ | 動的メッセージを含むアラーム説明文 |
| `time-created` | uint64 | システム自動設定 | アラーム発生時刻 (nanosecond UNIX timestamp) |
| `severity` | string enum | event profile の値 | `CRITICAL` / `MAJOR` / `MINOR` / `WARNING` |
| `action` | string enum | `"RAISE"` (固定) | ALARM テーブルには RAISE エントリのみ存在 |
| `resource` | string | — (optional) | アラーム発生源リソース識別子 |
| `acknowledged` | boolean | `"false"` | ACK 済みフラグ; RAISE 時に `false` で初期化 |
| `acknowledge-time` | uint64 | — (ACK 時のみ設定) | ACK/UNACK 操作時のタイムスタンプ |

## 制約

- `severity` に `INFORMATIONAL` はアラームとして不可 (one-shot event 専用)
- ALARM テーブルは起動時クリア・非永続。再起動後に残存しない
- 同一条件のアラームが連続 RAISE された場合、eventd は直近キャッシュと比較してフラッドを防ぐ (重複エントリを黙棄)
- テーブルサイズ上限なし (EVENT テーブルが 40,000 件 / 30 日上限のある一方、ALARM はスナップショット)

## 購読者

- **CLI**: `show alarm [detail | summary | severity | recent | timestamp]`
- **gNMI/REST**: OpenConfig alarms コンテナ経由で取得 (`/openconfig-alarms:alarms`)
- **pmon**: `ALARM_STATS` テーブルのカウンタを参照して System LED を制御 (Critical/Major → 赤、Minor/Warning → 黄、なし → 緑)

## 関連テーブル

| テーブル | 説明 |
|---------|------|
| `EVENT` | 全イベント (ALARM 含む) の履歴 — 永続・上限付き |
| `ALARM_STATS` | 重要度別アクティブアラーム数のカウンタ |
| `EVENT_STATS` | イベント統計 (raised/cleared/acked 累計) |

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

| 条件 | 挙動 |
|------|------|
| 同一アラームが連続 RAISE | eventd の直近キャッシュと一致する場合、重複エントリを黙棄 (flooding 防止) |
| CLEAR_ALARM を対応する RAISE なしで受信 | lookup map にエントリなし → ALARM テーブルへの操作なし |
| リブート (cold/warm/fast) | ALARM テーブルの内容はクリア (非永続); ALARM_STATS も同様にリセット |
| ACK_ALARM を mgmt-framework 以外が発行 | API 上可能だが、設計上 mgmt-framework のみを想定 |

<!-- evidence: SONiC/doc/event-alarm-framework/event-alarm-framework.md:Section 3.1.3, 3.1.4.2 -->
<!-- /cdb-exceptions -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG optional / event profile 未指定時の実行時フォールバック。

| フィールド | コード由来デフォルト | fallback 源 |
|-----------|-------------------|------------|
| `revision` | `0` | event profile の `revision` 未指定時 — HLD Section 3.1.2.3 |
| `acknowledged` | `"false"` | RAISE_ALARM 処理時に Alarm Consumer が初期化 — HLD Section 3.1.2 |
| `action` | `"RAISE"` (ALARM テーブル内では固定) | ALARM テーブルに格納されるのは RAISE イベントのみ |
| `acknowledge-time` | フィールド不在 | ACK_ALARM / UNACK_ALARM 受信前は存在しない |
| `resource` | フィールド不在 (optional) | アプリケーションが渡さない場合はフィールドなし |

### 補足

- **`revision=0` デフォルト**: event profile の `default.json` に `revision` が未記載の場合 eventd が `0` を採用する。開発者が新しいアラームパラメータ (threshold 変更等) を適用した際にインクリメントすることで、クライアントが異なるリリースのイベントを区別できる。
- **`acknowledged=false` 強制初期化**: RAISE_ALARM 処理時に Alarm Consumer が必ず `false` で初期化する。これによりオペレータの ACK 操作より前に `acknowledged=true` でエントリが存在することはない。
- **`action` は常に `"RAISE"`**: CLEAR_ALARM 受信時は対応エントリを **削除** するため、テーブル内のエントリは全て `action=RAISE` の状態にある。CLEAR 後の証跡は EVENT テーブルのみに残る。
- **severity デフォルト不在**: `severity` は event profile の `default.json` で開発者が必ず指定しなければならない。フォールバックは定義されていない。`INFORMATIONAL` は alarm には不可。

<!-- /defaults -->

<!-- constants -->
## ハードコード定数 (Phase E — コード由来)

ALARM テーブルのスキーマ・運用に直接効く固定値。event profile や CONFIG_DB から上書き不能で、コード/HLD でリテラル固定されている。

### severity 列挙値 (5 値、ハードコード文字列)

| 値 | アラーム適用 | 出典 |
|----|-------------|------|
| `CRITICAL` | 可 | HLD §3.1.2 (event-alarm-framework.md:136) |
| `MAJOR` | 可 | HLD :138 |
| `MINOR` | 可 | HLD :140 |
| `WARNING` | 可 | HLD :142 |
| `INFORMATIONAL` | **不可** (one-shot event 専用) | HLD :144, :348 |

eventd は event profile (`default.json`) に書かれた severity 文字列をそのまま ALARM テーブルへ書き込む。enum は YANG (`openconfig-alarms`) 側に定義され、コード上は文字列比較で扱われる。

### テーブル名固定文字列

`sonic-swss-common/common/schema.h:551-554`:

```c
#define EVENT_HISTORY_TABLE_NAME          "EVENT"
#define EVENT_CURRENT_ALARM_TABLE_NAME    "ALARM"
#define EVENT_STATS_TABLE_NAME            "EVENT_STATS"
#define EVENT_ALARM_STATS_TABLE_NAME      "ALARM_STATS"
```

これらは `#define` で固定され、設定で変更不可。

### retention / サイズ上限

| 対象 | 上限 | 出典 |
|------|------|------|
| ALARM テーブル records 数 | **上限なし** (スナップショット) | HLD §3.1.7 |
| ALARM テーブル保持日数 | **非永続** (リブートでクリア) | HLD §3.1.7 |
| EVENT テーブル records 数 | `40000` (range 1-40000) | HLD :482, :491, :496 |
| EVENT テーブル保持日数 | `30` (range 1-30) | HLD :482, :492, :497 |

ALARM 側に records / days 上限は定義されておらず、`eventd.json` の `no-of-records` / `no-of-days` は EVENT テーブルにのみ適用される。

### action 列挙 (プロトコル定数)

ALARM テーブルへ作用する 4 操作 (HLD §3.1.4 / §3.1.5):

- `RAISE_ALARM` — 行追加 (`action=RAISE` で格納)
- `CLEAR_ALARM` — 対応行を削除
- `ACK_ALARM` — `acknowledged=true` に更新
- `UNACK_ALARM` — `acknowledged=false` に更新

ALARM テーブル内の `action` フィールドは常に `"RAISE"` (CLEAR は行削除なのでテーブル上に残らない)。

詳細解析: `meta/_intermediate/cdb-flow/alarm-table-constants.md`

<!-- evidence: sonic-swss-common/common/schema.h:551-554, SONiC/doc/event-alarm-framework/event-alarm-framework.md:136-144,346-348,480-499 -->
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

ALARM テーブル自身は **EVENT_DB** への主たる書込先である。ここでは ALARM 系処理に付随して、ALARM テーブル以外の DB / テーブルへ書き込まれる事象を扱う。

### COUNTERS_DB / `COUNTERS_EVENTS`

eventd プロセス内の `stats_collector` が `event_publish()` 経路全体の累計カウンタを周期書込する。`RAISE_ALARM` action もこの経路を通るため、ALARM 発生時にもカウンタが進む。

| トリガ | 操作 | キー | フィールド | 値 | evidence |
|--------|------|------|-----------|-----|----------|
| `event_publish()` 経由で event/alarm が流れ、`m_updated` フラグが立っていれば 10ms 周期で flush | `set` | `counter_keys[i]` (`published` / `missed_internal` / `missed_to_cache` / `missed_by_slow_receiver` / `latency_in_ms` 等) | `value` | uint64 累計値 | `sonic-eventd/src/eventd.cpp:178,186-187,205-210` |

定数:

- `COUNTERS_EVENTS_TABLE = "COUNTERS_EVENTS"` (`sonic-swss-common/common/schema.h:266`)
- `EVENTS_STATS_FIELD_NAME = "value"` (`sonic-eventd/src/eventd.h:23`)

!!! note "ALARM 固有カウンタではない"
    `COUNTERS_EVENTS` は eventd の publish パス全体のサマリであり、`RAISE_ALARM` 単独の統計ではない。重要度別アクティブアラーム数は EVENT_DB の `ALARM_STATS` テーブルで保持される (本ページ「関連テーブル」節を参照)。

### STATE_DB

ALARM テーブル処理に伴う **STATE_DB への副次書込はなし**。

根拠:

- `sonic-buildimage/src/sonic-eventd/src/` 配下を `grep -rn "STATE_DB"` してもヒット 0 件 (テスト用 `database_config.json` を除く)
- `sonic-buildimage/src/system-health/` の `SYSTEM_READY` / `ALL_SERVICE_STATUS` / `FAN_INFO` 等の STATE_DB 書込は System Health Monitoring サブシステム由来であり、Event/Alarm Framework の ALARM テーブル (EVENT_DB) の更新トリガとは独立している

### その他 (FLEX_COUNTER_DB / APPL_DB / ASIC_DB)

該当する副次書込は検出されず、なし。

詳細分析: `meta/_intermediate/cdb-flow/alarm-table-side.md`
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

ALARM テーブルは **CONFIG_DB ではなく EVENT_DB (Redis DB index 6)** に存在し、CONFIG_DB の派生テーブルとは異なる通信モデルで運用される。書き込みは ZMQ ベースのイベントフレームワーク経由、読み取りは HGETALL polling という非対称な構造を持つ。

### 書き込み経路 — ZMQ XPUB/XSUB (Redis keyspace 通知非使用)

```
App (pmon/swss/bgp 等) ─ events_publish(RAISE_ALARM) ─▶ ZMQ ─▶ zmqproxy (eventd)
                                                                  │
                                                                  ▼
                                                       eventd Alarm Consumer
                                                                  │
                                       ┌──────────────────────────┼──────────────────────────┐
                                       ▼                          ▼                          ▼
                              HSET EVENT_DB              HINCRBY EVENT_DB        DEL EVENT_DB (CLEAR時)
                                ALARM|<id>                ALARM_STATS|state           ALARM|<id>
```

- `events_publish()` API は ZMQ PUB socket 経由で `zmqproxy` (eventd コンテナ内) に転送され、XPUB/XSUB プロキシが eventd メインループへ配信する (`sonic-eventd/src/eventd.cpp:240,419` 周辺)。
- Alarm Consumer は受信した `action` フィールドで分岐し、Redis に **HSET / DEL を直接** 行う。Redis の `PUBLISH` チャネルは使わない。
- 同一 type-id + resource + text の連続 RAISE は eventd 内キャッシュで重複抑止される (flooding 防止)。

### 読み取り経路 — HGETALL polling (購読者なし)

| 読者 | 取得方法 |
|------|---------|
| `show alarm` CLI | `sonic-db-cli EVENT_DB keys 'ALARM\|*'` + `hgetall` (1 回のスナップショット) |
| OpenConfig gNMI/REST | translib が EVENT_DB を HGETALL してマッピング (HLD Section 3.1.6) |
| pmon System LED | `ALARM_STATS\|state` を HGETALL し severity 別カウンタで LED 色を決定 |

- ALARM テーブルに対する `SubscriberStateTable` / `ConsumerStateTable` / `NotificationProducer` の購読者は SONiC ソース内に **存在しない**。
- これは ALARM テーブルが「ある瞬間のアクティブアラーム集合」というスナップショット型設計であり、差分通知より全件取得が自然な利用パターンであるため。
- EVENT_DB は `notify-keyspace-events` がデフォルト無効で、Redis keyspace 通知に依存する購読者は想定されていない。

### healthd (system-health) との関係

`src/system-health/health_checker/sysmonitor.py:41,97` の healthd は ALARM テーブルを購読しない (購読対象は `STATE_DB:FEATURE` と systemd D-Bus のみ)。Event/Alarm Framework と healthd は独立したサブシステムである。

### dbId / TTL / 永続性

| 項目 | 値 |
|------|---|
| Redis DB index | 6 (EVENT_DB) |
| 永続性 | 無 (cold/warm/fast reboot で全件消失) |
| TTL | 無 (CLEAR_ALARM 受信時に eventd が明示 DEL) |
| Redis 通知 | keyspace 通知は非使用 (購読者が居ないため) |
| エントリ ID | `<32bit time_t><5桁連番>` を eventd Alarm Consumer が採番 |

詳細解析: `meta/_intermediate/cdb-flow/alarm-table-pubsub.md`

<!-- /pubsub -->

<!-- cross-refs -->
## 暗黙参照 (Phase C)

ALARM テーブルは EVENT_DB に存在し、CONFIG_DB 的な YANG `leafref` 制約は持たない。
しかし「ALARM 行が成立する前提として暗黙的に存在しなければならないキー / テーブル」がコード上に固定参照として現れる。

### event profile キー (`<source>.<tag>`) への暗黙参照

ALARM 行の `type-id` / `severity` / `action` フィールドは、publisher が指定する `(source, tag)` を **event profile JSON のキー** として暗黙参照する。profile に該当キーが無いと eventd 側で severity / action が解決されず RAISE が無効化される (型なし string だがコードレベルで参照整合性が強制)。

| publisher source | tag | 発火元 | evidence |
|---|---|---|---|
| `sonic-events-eventd` | `heartbeat` | eventd 自身 (2 秒周期) | `sonic-eventd/src/eventd.cpp:46-47,291` |
| `sonic-events-host` | `process-not-running` | system-health `service_checker` | `system-health/health_checker/service_checker.py:15-16,380-384` |
| `sonic-events-host` | `liquid-cooling-leak` | system-health `hardware_checker` | `system-health/health_checker/hardware_checker.py:7-8,298-302` |
| `sonic-events-host` | `process-exited-unexpectedly` | supervisord proc-exit-listener | `sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener:44-45,145-149` |

### CONFIG_DB / STATE_DB の暗黙間接依存 (healthd 経由)

`eventd` プロセスは DEVICE_METADATA を直接読まないが (`src/sonic-eventd/src/` 配下 `grep "DEVICE_METADATA"` ヒット 0)、主要な ALARM publisher である **healthd (system-health)** は CONFIG_DB / STATE_DB の以下エントリに起動時依存する。これらが欠落すると `sonic-events-host` 系の RAISE_ALARM が発火せず、ALARM テーブルが空のままになる。

| 参照元 | 参照先 | 種別 | 用途 | 参照箇所 |
|---|---|---|---|---|
| healthd `sysmonitor.py` | `CONFIG_DB:DEVICE_METADATA` (全フィールド) | get_table | device_config レンダリング | `sysmonitor.py:152,217-219` |
| healthd `sysmonitor.py` | `STATE_DB:FEATURE` | SubscriberStateTable | 監視対象 feature の up/down 追従 | `sysmonitor.py:39-41` |
| healthd `service_checker.py` | `CONFIG_DB:FEATURE` | get_table | プロセス監視対象の取捨選択 | `service_checker.py:321-323` |

### `resource` フィールドの動的参照

ALARM の `resource` フィールド (optional) は publisher アプリケーションが任意のリソース識別子 (例: `Ethernet0`, `PSU1`, `xcvrd:Ethernet24`) を入れる動的多態フィールド。参照先テーブル (`TRANSCEIVER_INFO` / `TEMPERATURE_INFO` / `PORT` 等) は固定されておらず、HLD §3.1.2 の OpenConfig `/components/component` 系パスへのマッピングのみが規約化されている。

### 連動書込先 (Phase F 重複)

| 連動書込先 | 関係 | 参照箇所 |
|---|---|---|
| `COUNTERS_DB:COUNTERS_EVENTS` | eventd が ALARM 含む event publish 経路全体のカウンタを 10ms 周期で flush | `eventd.h:18-20,87`, `eventd.cpp:50-53,187,205-210` |

!!! note "AlarmConsumer 本体は master HEAD に未収載"
    現スナップショット (`sonic-buildimage` SHA `9ea932ec...`) の `src/sonic-eventd/src/` は XPUB/XSUB proxy + heartbeat + stats のみで、HLD §3.1.x が言及する Alarm Consumer (RAISE/CLEAR/ACK/UNACK を ALARM テーブルへ反映する側) の実装ソースは未存在。`type-id` → event profile, `resource` → リソーステーブル の **書き込み側コード** からの参照確認は将来コミット待ち。本セクションは publisher 側 + healthd 側 + 連動書込先の 3 軸で構成している。

詳細解析: `meta/_intermediate/cdb-flow/alarm-table-cross-refs.md`

<!-- evidence: sonic-buildimage/src/sonic-eventd/src/eventd.cpp:46-47,50-53,187,205-210,291; src/system-health/health_checker/service_checker.py:15-16,321-323,380-384; src/system-health/health_checker/hardware_checker.py:7-8,298-302; src/system-health/health_checker/sysmonitor.py:39-41,152,217-219 -->
<!-- /cross-refs -->

<!-- ref-triangle:start -->

## 関連リファレンス

- HLD: [Event and Alarm Framework](https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/event-alarm-framework.md)
- YANG: `openconfig-alarms` (sonic-mgmt-common)
- CLI: `show alarm`

<!-- ref-triangle:end -->

## 引用元

[^1]: `SONiC/doc/event-alarm-framework/event-alarm-framework.md` Rev 0.3, Section 1 / 3.1.7 — ALARM テーブルの定義・スキーマ・redis 出力例。<https://github.com/sonic-net/SONiC/blob/master/doc/event-alarm-framework/event-alarm-framework.md>

[^2]: `sonic-swss-common/common/schema.h:552` — `#define EVENT_CURRENT_ALARM_TABLE_NAME "ALARM"`

## 関連ページ

- [CONFIG_DB / EVENT_DB: EVENT テーブル](event-table.md)

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# アクティブアラーム一覧
show alarm

# redis 直接確認 (EVENT_DB = index 6)
sonic-db-cli EVENT_DB keys 'ALARM|*'
sonic-db-cli EVENT_DB hgetall 'ALARM|<id>'

# ALARM_STATS 確認
sonic-db-cli EVENT_DB hgetall 'ALARM_STATS|state'
```

### よくある確認ポイント

- `acknowledged=true` のアラームは ALARM_STATS のカウンタから除外されるため、System LED の判定に影響しない
- リブート後に ALARM テーブルが空になるのは正常動作
- `show alarm summary` で severity 別カウントを確認できる
<!-- /ops-hint -->
