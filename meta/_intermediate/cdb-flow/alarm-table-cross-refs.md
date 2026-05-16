# ALARM テーブル — Phase C 暗黙参照 調査メモ

## 調査目的

ALARM テーブル (EVENT_DB / Redis index 6) に関連する **暗黙参照** を整理する。
- ALARM 自体は CONFIG_DB ではないため、CONFIG_DB の `leafref` のようなスキーマ参照は存在しない。
- 一方で「ALARM テーブルの内容が成立する前提として暗黙的に存在しなければならない CONFIG_DB / STATE_DB エントリ」「event publisher を駆動するためのソース文字列・タグ」がコード上に固定参照として現れる。
- Phase C: `<!-- cross-refs -->` セクション用。

ソース: `.cache/sonic-sources/sonic-buildimage/src/sonic-eventd/`, `.cache/sonic-sources/sonic-buildimage/src/system-health/`。

## 1. event publisher source / tag (RAISE_ALARM の発生源)

ALARM テーブルへ書き込まれる行は、SONiC 内のさまざまなコンポーネントが `events_init_publisher(source)` + `event_publish(handle, tag, params)` を呼び出すことで生まれる。`source` 文字列と `tag` 文字列は event profile (`*_events.rc.json` / `default.json`) の **キーとして暗黙参照** され、profile 内で対応する `severity` / `action` (`RAISE_ALARM` / `CLEAR_ALARM` …) / `text` が解決される。

### 検出された publisher (source 文字列でグルーピング)

| publisher source | 発火元 | tag | 発火条件 | evidence |
|---|---|---|---|---|
| `sonic-events-eventd` | eventd 自身 (heartbeat) | `heartbeat` | 2 秒周期 (HEARTBEAT_INTERVAL_SECS) | `sonic-eventd/src/eventd.cpp:46-47,291` |
| `sonic-events-host` | system-health `service_checker` | `process-not-running` | サービスのプロセス不在を検出 | `system-health/health_checker/service_checker.py:15-16,380-384` |
| `sonic-events-host` | system-health `hardware_checker` | `liquid-cooling-leak` | 液冷リーク検出 | `system-health/health_checker/hardware_checker.py:7-8,298-302` |
| `sonic-events-host` | supervisord proc-exit-listener | `process-exited-unexpectedly` | コンテナ内プロセス予期せぬ終了 | `sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener:44-45,145-149,176,202-203` |

これらの `source` + `tag` の組は **event profile JSON** に同名キーが存在することを暗黙前提とする。profile 未収載の tag は eventd の Alarm Consumer 側で severity / action が解決できず、ALARM テーブルにも `severity` / `action=RAISE` で書けない (=暗黙の参照整合性制約)。

### 結論

ALARM テーブルの `type-id` / `severity` / `action` フィールドは、`<source>.<tag>` をキーとして event profile を **暗黙 leafref** している。schema 上は型なしの string だが、profile 未掲載値は eventd 側で弾かれる。

## 2. CONFIG_DB 側の暗黙依存

### DEVICE_METADATA|localhost

`sonic-eventd/src/` 配下を `grep -rn "DEVICE_METADATA"` してもヒット 0 件。eventd プロセスは **DEVICE_METADATA を直接読まない**。

ただし、ALARM テーブルへの書き込みを駆動する `system-health` 側 (= `sysmonitor.py`) は CONFIG_DB の `DEVICE_METADATA` を読み出して device_config を構築している:

| 読み取りフィールド | 行 | 用途 |
|---|---|---|
| `DEVICE_METADATA` テーブル全体 | `sysmonitor.py:219` | `device_config['DEVICE_METADATA']` に格納し、healthd レンダリングに使用 |

evidence: `sonic-buildimage/src/system-health/health_checker/sysmonitor.py:152-219`

ALARM 自体は DEVICE_METADATA を参照しないが、ALARM の主要 publisher である healthd は DEVICE_METADATA を起動時依存に持つ。よって ALARM テーブルから見ると **2 段間接で DEVICE_METADATA に依存** している (= healthd が DEVICE_METADATA 取得に失敗すると hardware_checker / service_checker が動かず、`sonic-events-host` 系の RAISE_ALARM が一切発火しない)。

### FEATURE テーブル (CONFIG_DB / STATE_DB)

healthd は CONFIG_DB の `FEATURE` / STATE_DB の `FEATURE` を subscribe しサービス監視対象を決定している:

| 種別 | 行 | 用途 |
|---|---|---|
| `STATE_DB:FEATURE` SubscriberStateTable | `sysmonitor.py:39-41` | 機能の up/down 変化に追従 |
| `CONFIG_DB:FEATURE` get_table | `service_checker.py:321-323`, `sysmonitor.py:217,255` | 監視対象サービスの取捨選択 |

これも ALARM の **暗黙 1 段間接依存** (FEATURE が無ければ `process-not-running` の RAISE は出ない)。

## 3. STATE_DB 側の暗黙依存

healthd 経由で書かれる STATE_DB 系テーブル (ALARM テーブルとは別経路だが、運用上 ALARM と相関する):

| テーブル | 書き込み箇所 | 関係 |
|---|---|---|
| `SYSTEM_READY\|SYSTEM_STATE` | `sysmonitor.py:142,513` | システム全体の Ready/Not Ready 状態。ALARM RAISE と同時にここも更新されうる |
| `ALL_SERVICE_STATUS\|*` | `sysmonitor.py:511` 周辺 | サービス単位の Up/Down。`process-not-running` ALARM と相関 |

ALARM テーブルから直接 leafref する関係ではなく **「同じ healthd プロセスが両方を書く」並列書込関係**。Phase F (side-effects) で扱う範囲だが、Phase C 観点では healthd を介した **STATE_DB ⇔ ALARM(EVENT_DB) の論理同期** が暗黙的に存在する点を記録しておく。

## 4. COUNTERS_EVENTS の暗黙依存

eventd 自身が `COUNTERS_DB:COUNTERS_EVENTS` に publish/missed カウンタを書き出す (Phase F 該当)。
- ALARM テーブル更新ごとに `INDEX_COUNTERS_EVENTS_PUBLISHED` が進む。
- ALARM テーブルからの参照ではなく、ALARM 発生時に必ず連動するため **同期書込パートナー** として記録。

evidence: `sonic-eventd/src/eventd.h:18-20,87`, `sonic-eventd/src/eventd.cpp:50-53,131,187,205-210,287`

## 5. 注記: AlarmConsumer 本体は master HEAD に未存在

`sonic-buildimage/src/sonic-eventd/src/` (commit `9ea932ec...`) には XPUB/XSUB proxy + heartbeat + stats のみが含まれ、HLD §3.1.x で言及される **Alarm Consumer (RAISE/CLEAR/ACK/UNACK を ALARM テーブルに反映する側)** の実装ソースは見当たらない。
- ALARM テーブルの "暗黙参照" の **書き込み側ロジック** は現スナップショットでは grep できないため、本 Phase C では「publisher → event profile キー」「healthd → CONFIG_DB DEVICE_METADATA / FEATURE」「ALARM ⇄ COUNTERS_EVENTS」の 3 軸に絞る。
- 将来 Alarm Consumer がマージされ次第、`type-id` → event profile, `resource` → 該当リソーステーブル (例: `TRANSCEIVER_INFO`, `TEMPERATURE_INFO`) への暗黙参照を追記する。

## 6. cross-refs セクション最終構造案

```text
ALARM.type-id / severity / action   ──暗黙参照──▶  event profile (<source>.<tag>)
ALARM (entire table)               ──間接依存──▶  CONFIG_DB:DEVICE_METADATA|localhost (via healthd)
ALARM (entire table)               ──間接依存──▶  CONFIG_DB:FEATURE / STATE_DB:FEATURE (via healthd)
ALARM 書込み                       ──連動書込──▶  COUNTERS_DB:COUNTERS_EVENTS (eventd 内部)
```

## 7. 記述上の注意

- ALARM は EVENT_DB のため、ACL_TABLE のような CONFIG_DB 内 leafref とは性質が異なる。Phase C は「ALARM 行が正しく成立するために他テーブルに何が必要か」という観点で書く。
- `resource` フィールドへの参照解決は publisher 側のアプリケーションが決めるため、ALARM テーブルからの参照先 SCHEMA は固定されていない (動的多態)。HLD §3.1.2 の OpenConfig マッピングを根拠に「リソースパス文字列」として扱う旨を本文に明記。
- AlarmConsumer 実装は master HEAD に未収載である点を脚注で透明化する。
