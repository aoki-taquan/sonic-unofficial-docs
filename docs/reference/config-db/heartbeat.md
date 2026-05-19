---
title: HEARTBEAT テーブル
description: "HEARTBEAT テーブル — システムプロセスの heartbeat 監視 (生存確認) のインターバルとアラート間隔をプロセスごとに設定するテーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-heartbeat.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - HEARTBEAT
  yang:
    - sonic-heartbeat
  _no_related_cli: true
---

# HEARTBEAT テーブル

## 概要

システムプロセスの heartbeat 監視 (生存確認) のインターバルとアラート間隔をプロセスごとに設定するテーブル[^1]。
process monitor は登録された `name` のプロセスから `heartbeat_interval` ms ごとに生存通知を期待し、`alert_interval` ms 内に通知がなければアラートを上げる。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>HEARTBEAT")]
  DM["process-monitor"]
  CDB --> DM
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
HEARTBEAT|<name>
```

`<name>`: 1–32 文字。監視対象プロセス名 (例: `pmon`, `swss`, `syncd` 等)。

## フィールド

| フィールド | 型 | 既定 | 説明 |
|-----------|----|------|------|
| `heartbeat_interval` | uint32 | `10000` | 期待される heartbeat 送信間隔 [ms] |
| `alert_interval`     | uint32 | `60000` | この時間内に heartbeat 不達ならアラート [ms] |

## 購読者

- process monitor デーモン (heartbeat 監視機能を持つ host service)。各プロセスは `STATE_DB` 等に生存通知を書き、監視側がタイムアウトを検査する

## 関連 YANG

- `sonic-heartbeat`

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

YANG (`sonic-heartbeat.yang`) には `default` 宣言が**存在し**、YANG validator 経由で書き込んだ場合は `heartbeat_interval=10000` ms / `alert_interval=60000` ms が暗黙適用される。`sonic-db-cli` 直接書き込みでは YANG default は注入されない。eventd 側は別経路 (GLOBAL_OPTION_HEARTBEAT JSON RPC) で interval を受け、初期値は `HEARTBEAT_INTERVAL_SECS=2` 秒 (`eventd.cpp:43`)。両者はスキーマ単位 (ms vs 秒) が異なるので混同しないこと。

| フィールド | YANG default | コード由来デフォルト | 発生源 |
|---|---|---|---|
| `heartbeat_interval` | **`10000`** ms | `10000` ms (YANG default 経由) | `sonic-heartbeat.yang` leaf `default "10000"` |
| `alert_interval` | **`60000`** ms | `60000` ms (YANG default 経由) | `sonic-heartbeat.yang` leaf `default "60000"` |
| (eventd 内部 `interval`) | n/a | **`2`** 秒、`300` ms ステップに量子化 | `eventd.cpp:43` `HEARTBEAT_INTERVAL_SECS=2` + `eventd.h:24` `STATS_HEARTBEAT_MIN=300` |
| (eventd `m_pause_heartbeat`) | n/a | **`false`** | `eventd.cpp:127` (atomic bool 初期化) |

### YANG default と sonic-db-cli の差異

YANG default は libyang/sonic-mgmt-common の validation pass を通したときのみ補完される。`config_db.json` を直接書く / `sonic-db-cli HSET` で書く経路では `heartbeat_interval` キーが欠落したまま DB に格納される。コンシューマ (process monitor) 側がキー欠落をどう扱うかが実 fallback を決める。

### eventd 側 `interval` の特殊値 (再掲・本ページ上部の値依存挙動マトリクスと整合)

`set_heartbeat_interval()` (`eventd.cpp:139-161`) は受け取った秒数を `STATS_HEARTBEAT_MIN` (300ms) 単位に切り上げ量子化する。`val=-1` は無効化 (`m_heartbeats_interval_cnt=0` で publish ループ skip)、`val<-1` は invalid。`m_pause_heartbeat` は起動時 `false`、`heartbeat_ctrl(true)` 呼び出しでのみ pause する。CONFIG_DB に "suppress" / "pause" 相当のフィールドは存在しない。

### hostcfgd 側

`sonic-host-services/scripts/hostcfgd` に `HEARTBEAT` テーブル handler は**不在**。CONFIG_DB → hostcfgd 経由のランタイム反映パスは無く、本テーブルの直接コンシューマは限定的。

### 参考: SYSTEM_HEALTH 側

`system-health/health_checker/config.py:12-13` の `DEFAULT_INTERVAL = 60` (秒) は **SYSTEM_HEALTH テーブル**の `polling_interval` 用 fallback であり、HEARTBEAT テーブルとは別系統。混同に注意。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`HEARTBEAT` テーブルは他の CONFIG_DB テーブルとの明示的な外部キー参照を持たない。エントリは `name` (プロセス名) 単位で独立しており、相互依存はない。ただし、eventd / process-monitor がこのテーブルを**起動時の初回読み込み**と**subscribe 通知**の 2 経路で参照する構造上、以下の順序制約が存在する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `HEARTBEAT` エントリ書込み → eventd / process-monitor 起動 | **推奨先行**（起動後の初回読み込みで反映される） | 起動後追加時は subscribe 通知で自動反映 |
| 2 | 各 `HEARTBEAT|<name>` エントリは相互独立 | 独立 | 書込み順序不問 |
| 3 | `heartbeat_interval` と `alert_interval` の同一エントリ内同時書込み | **アトミック推奨**（HSET で複数フィールドを一括書込み） | 片方だけ書くと中間状態で `alert_interval < heartbeat_interval` になりえる |

### 主要な制約詳細

**起動前書込み推奨 (依存 #1)**: eventd は `set_heartbeat_interval(HEARTBEAT_INTERVAL_SECS)` でデフォルト値 (2 秒) を内部に持ち起動する (`eventd.cpp:130`)。CONFIG_DB の `HEARTBEAT` エントリは `GLOBAL_OPTION_HEARTBEAT` option API 経由で eventd に通知されるが、eventd が既に起動済みの場合でも subscribe 通知によりランタイム更新が可能。ただし起動直後の短い窓ではデフォルト値で動作する点に注意。

**フィールド同時書込み (依存 #3)**: `sonic-db-cli CONFIG_DB HSET "HEARTBEAT|<name>" heartbeat_interval 5000 alert_interval 30000` のように 1 コマンドで複数フィールドを書くことで中間状態を回避できる。CLI 書き込みパスが存在しないため、通常は `config_db.json` の load (一括) または 1 エントリ単位の HSET で書き込む。

<!-- /ordering -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): `sonic-heartbeat`

<!-- ref-triangle:end -->

## 引用元

[^1]: [YANG](../../reference/glossary.md#term-yang) 定義: `sonic-heartbeat.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-heartbeat.yang>

## 関連ページ
- [CONFIG_DB index](index.md)

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `HEARTBEAT|<key>`。
- `interval`: 秒単位の hearbeat 間隔。デフォルトはイメージ依存。

### よくある誤設定

- interval を極端に短くすると CPU 負荷が上がり他デーモン処理が遅延する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'HEARTBEAT|*'
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

このテーブルに strict な enum フィールドはない。`interval` の特殊値で動作が分岐する。

### `interval` (eventd 側の内部スキーマ、events_wrap.h / eventd.cpp 準拠)

| 値 | 挙動 |
|----|------|
| `-1` | heartbeat を無効化（"A value of -1 implies no heartbeat"） |
| `< -1`（-2 以下） | invalid 扱い。syslog 記録後処理中断 |
| `0` | システムデフォルト 2 秒として動作（`HEARTBEAT_INTERVAL_SECS = 2`） |
| 正値 | 内部 300ms 単位（`STATS_HEARTBEAT_MIN`）に切り上げ量子化。指定値と実周期がずれる場合がある |

> **注意**: YANG では `heartbeat_interval` / `alert_interval` は uint32 [ms] 単位。
> eventd.cpp 側の `interval` とはスキーマが別（秒単位）なので混同に注意。

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-buildimage/src/sonic-eventd/src/eventd.cpp, sonic-swss-common/common/events_wrap.h -->

| 条件 | 挙動 |
|------|------|
| `interval = -1` | heartbeat を無効化（events_wrap.h L131「A value of -1 implies no heartbeat」） |
| `interval < -1`（-2 以下） | invalid 扱い。syslog に詳細記録後処理中断（events_wrap.h L136） |
| `interval = 0` | システムデフォルト 2 秒として動作（eventd.cpp L43 `HEARTBEAT_INTERVAL_SECS = 2`） |
| 任意の正値 | 内部は 300ms 単位に切り上げ量子化。指定値と実周期がずれる場合がある（eventd.cpp L145） |
| heartbeat publish 失敗 | `SWSS_LOG_ERROR("Failed to publish heartbeat rc=%d")` → ハートビート欠落するが eventd は継続 |

<!-- /cdb-exceptions -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`heartbeat` daemon / `system_health_monitor` が CONFIG_DB の `HEARTBEAT` テーブルを購読する。

`HEARTBEAT` はシステムヘルスモニタリング機能の設定。`system_health_monitor` と連携。

### 段階 2 — CFG→APPL 翻訳

なし (APPL_DB 中継なし)

### 段階 3 — APPL→SAI

なし (SAI 非経由 — システムヘルスチェック設定)

### 段階 4 — タイミングと副作用

**適用タイミング**: CONFIG_DB の `HEARTBEAT` エントリ変化を検知後、heartbeat チェック間隔/閾値を更新。次回チェックサイクルから有効。

**副作用**: heartbeat interval 変更は障害検知の速度に影響。閾値変更は誤検知/検知遅延に影響する可能性がある。
<!-- /runtime-trace -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`HEARTBEAT` テーブルは `supervisor-proc-exit-listener`（Python 版・Rust 版）が起動時に一括読み込みする。エントリ間の順序依存はないが、フィールド書込みタイミングと daemon 起動タイミングに関して以下の制約がある。

### 依存関係サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB への `HEARTBEAT\|<name>` 書込み → daemon 起動 | **推奨先行** | daemon は起動時に `load_heartbeat_alert_interval()` で一括読み込む。起動後は動的再読しない |
| 2 | `heartbeat_interval` + `alert_interval` の同一 SET | **推奨** | 片方のみ SET すると中間状態で `alert_interval < heartbeat_interval` になりえる |
| 3 | 複数 `HEARTBEAT\|<name>` エントリ間 | 独立 | 相互依存なし。任意の順序で書込み可 |

### 詳細

**起動前書込み推奨 (依存 #1)**

`supervisor-proc-exit-listener` は起動時に `load_heartbeat_alert_interval()` / `load_heartbeat_alert_interval(config_db)` を呼び、`HEARTBEAT` テーブル全体を一括でメモリに読み込む（Python: `supervisor-proc-exit-listener:124-135`、Rust: `proc_exit_listener.rs:212-234`）。起動後は CONFIG_DB の変更を subscribe しないため、**daemon 起動前に全エントリを書き込んでおくことが推奨される**。起動後に追加したエントリは、次回 daemon 再起動まで反映されない。

**フィールド同時書込み推奨 (依存 #2)**

`heartbeat_interval` と `alert_interval` は同一 `HEARTBEAT|<name>` エントリのフィールドである。Redis `HSET` で片方ずつ書き込むと中間状態が発生し、`alert_interval` がデフォルト (`60000` ms) のまま `heartbeat_interval` だけ短縮された状態になりえる。`HSET HEARTBEAT|<name> heartbeat_interval <v1> alert_interval <v2>` のように単一コマンドで両フィールドを同時に書くことで回避できる。

**エントリ間の独立性 (依存 #3)**

複数プロセス分の `HEARTBEAT|pmon`、`HEARTBEAT|swss` 等は互いに独立したエントリであり、書込み順序の制約はない。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`HEARTBEAT` テーブルは YANG `sonic-heartbeat.yang` に leafref を持たず、他の CONFIG_DB テーブルへの外部キー参照はゼロである。また、他テーブルから `HEARTBEAT|<name>` への被参照も存在しない。

<!-- evidence: meta/_intermediate/cdb-flow/heartbeat-cross-refs.md -->

| 参照方向 | 参照元フィールド / 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|------------------------|--------------|--------------|---------|------|
| なし（外部参照ゼロ） | — | — | — | `HEARTBEAT_LIST` は `leafref` を持たない。`name` / `heartbeat_interval` / `alert_interval` のみ | `sonic-heartbeat.yang` 全文 |
| 被参照なし | — | `HEARTBEAT` | — | 他の CONFIG_DB テーブルから `HEARTBEAT\|<name>` への leafref または外部キー参照は存在しない | 全 YANG 検索結果 |

### 補足: consumer 側の関連テーブル

`supervisor-proc-exit-listener` は同一スクリプト内で `FEATURE` テーブルも読むが (`get_autorestart_state()`)、これは auto-restart 判定用の別パスであり HEARTBEAT フィールドの値とは無関係である（`supervisor-proc-exit-listener:100-122`）。

`eventd` は `GLOBAL_OPTION_HEARTBEAT` という ZeroMQ RPC 経由でのみ heartbeat interval を受け取り、CONFIG_DB の `HEARTBEAT` テーブルを直接購読しない。両者はスキーマ単位（ms vs 秒）も異なる別系統（`eventd.cpp:638-646`）。

!!! note "HEARTBEAT は「孤立テーブル」"
    外部からの依存も、外部への依存もないため、HEARTBEAT エントリは他テーブルとの投入順序に縛られず任意の順序で書き込める。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

> 調査証跡: `meta/_intermediate/cdb-flow/heartbeat-failure.md`

### 失敗パス一覧

| # | 失敗条件 | 挙動 | 重大度 |
|---|----------|------|--------|
| 1 | `alert_interval` フィールド欠落 | `supervisor-proc-exit-listener` がデフォルト `ALERTING_INTERVAL_SECS = 60` 秒にフォールバック。クラッシュなし | 低（監視継続） |
| 2 | `heartbeat_interval` フィールド欠落 | `supervisor-proc-exit-listener` は `heartbeat_interval` を使用しないため影響なし。eventd は CONFIG_DB を直接購読しないため同様に影響なし | 低（影響なし） |
| 3 | CONFIG_DB 接続失敗 | `load_heartbeat_alert_interval()` が例外終了する可能性がある。`heartbeat_alert_interval_initialized` が `False` のままのため次回呼び出しで再試行 | 中（一時的） |
| 4 | `event_publish()` 失敗（eventd） | `SWSS_LOG_ERROR("Failed to publish heartbeat rc=%d")` を syslog に記録して継続。eventd クラッシュなし | 低（継続） |
| 5 | `events_init_publisher()` 初期化失敗（eventd） | `RET_ON_ERR` マクロにより eventd プロセスが終了（fatal） | 高（プロセス終了） |
| 6 | `events_init_subscriber()` 初期化失敗（eventd） | `RET_ON_ERR` マクロにより eventd プロセスが終了（fatal） | 高（プロセス終了） |
| 7 | 監視対象プロセスが `alert_interval` 秒以上 heartbeat 無送信（stuck） | `generate_alerting_message(process, "stuck", ..., LOG_WARNING)` で syslog に WARNING を記録。プロセス強制終了・自動再起動は行わない | 中（通知のみ） |
| 8 | HEARTBEAT テーブルが空（エントリなし） | `heartbeat_alert_interval_initialized = True` にセットされ、全プロセスがデフォルト 60 秒フォールバックを使用 | 低（デフォルト動作） |

### 主要な失敗パス詳細

**`alert_interval` 欠落時のフォールバック (失敗 #1)**

`load_heartbeat_alert_interval()` は `alert_interval` フィールドが存在しない場合（`.get('alert_interval')` が `None`）を条件判定でスキップし、`heartbeat_alert_interval_mapping` に登録しない。`get_heartbeat_alert_interval()` はプロセスが mapping に不在の場合 `ALERTING_INTERVAL_SECS = 60` を返す（`supervisor-proc-exit-listener:142-143`）。

**stuck 検出の通知のみ動作 (失敗 #7)**

監視ループ (`supervisor-proc-exit-listener:243-249`) は `threshold > 0 and elapsed_secs >= threshold` の条件で stuck を検出するが、アクションは syslog への `LOG_WARNING` 記録のみ。プロセスへの SIGTERM 送信や supervisord への終了通知は行わない。不応答プロセスの強制回復はオペレータ手動か `auto-restart` 設定に委ねられる。

**eventd publish 失敗の非致命的ハンドリング (失敗 #4)**

`event_publish(pub_handle, EVENTD_HEARTBEAT_TAG)` が非ゼロを返した場合は `SWSS_LOG_ERROR` のみ（`eventd.cpp:293`）。publish 失敗は heartbeat イベントの欠落を意味するが、eventd プロセス自体は継続して次のサイクルで再試行する。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

`HEARTBEAT` テーブルのコンシューマ `supervisor-proc-exit-listener`（Python 版・Rust 版）内に存在する、CONFIG_DB / YANG で管理されない固定値の一覧。

### supervisor-proc-exit-listener タイムアウト定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SELECT_TIMEOUT_SECS` | **1.0** 秒 (Python) / **1** 秒 (Rust) | `select()` 呼び出しのタイムアウト。このインターバルで heartbeat stuck 検出ループが動く | `supervisor-proc-exit-listener:39` / `proc_exit_listener.rs:30` |
| `ALERTING_INTERVAL_SECS` | **60** 秒 | `alert_interval` フィールドが CONFIG_DB に存在しないプロセスに対するデフォルト stuck 検出閾値。`HEARTBEAT` エントリが空またはプロセスが未登録の場合にこの値が使われる | `supervisor-proc-exit-listener:42` / `proc_exit_listener.rs:31` |

### イベントパブリッシャー識別子

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `EVENTS_PUBLISHER_SOURCE` | `"sonic-events-host"` | `events_init_publisher()` に渡すイベントソース名 | `supervisor-proc-exit-listener:44` |
| `EVENTS_PUBLISHER_TAG` | `"process-exited-unexpectedly"` | クリティカルプロセス unexpected exit 時に publish するイベントタグ | `supervisor-proc-exit-listener:45` |

### 設定ファイルパス

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `WATCH_PROCESSES_FILE` | `/etc/supervisor/watchdog_processes` | heartbeat 監視対象プロセスを列挙するファイル。`PROCESS_COMMUNICATION_STDOUT` イベントで heartbeat を更新する対象を絞り込む | `supervisor-proc-exit-listener:22` |
| `CRITICAL_PROCESSES_FILE` | `/etc/supervisor/critical_processes` | 予期しない終了時に supervisord を SIGTERM で停止する対象プロセス・グループを列挙 | `supervisor-proc-exit-listener:30` |

### 補足

- `ALERTING_INTERVAL_SECS = 60` はフォールバック定数であり、`HEARTBEAT|<name>.alert_interval` に値が設定されていれば ms 単位でその値が優先される (`supervisor-proc-exit-listener:131-133`: `int(alert_interval) / 1000` に変換)。
- `HEARTBEAT_TABLE_NAME = 'HEARTBEAT'` はシンボル定数として定義されているが (`supervisor-proc-exit-listener:36`)、CONFIG_DB テーブル名の変更が生じた際の単一変更点として機能する。
- Rust 版 (`proc_exit_listener.rs`) は Python 版の構造を踏襲し、同一定数を `const` として再定義している。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/heartbeat-side.md`

CONFIG_DB `HEARTBEAT` テーブルの変更に伴って副次的に書き込まれる DB エントリは **存在しない**。主消費者 `supervisor-proc-exit-listener`（Python 版・Rust 版）は CONFIG_DB を読み取るのみで他 DB への書込は行わない。eventd は CONFIG_DB の `HEARTBEAT` テーブルを直接購読せず、ZeroMQ RPC 経由でのみ heartbeat interval を受け取る構造であるため、`HEARTBEAT` エントリの変更が他 DB へ伝播する経路はない。

| 副次 DB | 書込有無 | 根拠 |
|---------|---------|------|
| APPL_DB | なし | `supervisor-proc-exit-listener` に `Producer`/`Table`/`hset` 書込呼出ゼロ件（スクリプト全文 grep） |
| STATE_DB | なし | 同スクリプトに STATE_DB への書込参照なし |
| COUNTERS_DB | なし | HEARTBEAT 監視は統計カウンタを持たない |
| ASIC_DB | なし | SAI 非経由（ホストサービス設定） |
| FLEX_COUNTER_DB | なし | 同上 |

### 実際の副作用（syslog のみ）

`HEARTBEAT` 設定の変更が間接的に引き起こす副作用は syslog 出力の変化に閉じる。

| トリガー | 副作用 | 重大度 | 証跡 |
|----------|--------|--------|------|
| `alert_interval` を短縮 → 対象プロセスが新閾値以上 heartbeat 無送信 | `generate_alerting_message(process, "stuck", ..., LOG_WARNING)` で syslog WARNING を記録 | LOG_WARNING | `supervisor-proc-exit-listener:249` |
| クリティカルプロセスが予期せず終了 | `events_init_publisher("sonic-events-host")` を通じて `process-exited-unexpectedly` イベントを publish。`HEARTBEAT` 設定とは独立したパス | LOG_INFO + event | `supervisor-proc-exit-listener:149,202` |

**注意**: `supervisor-proc-exit-listener` は起動時に `HEARTBEAT` テーブルを一括読み込みし (`load_heartbeat_alert_interval`)、以後は再読しない。そのため `alert_interval` を変更しても動作中の daemon には反映されず、次回 daemon 再起動後に有効化される。この「設定変更の副作用が遅延する」挙動はオペレーション上の注意点である。

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

> **調査根拠**: `sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener:124-135` (`load_heartbeat_alert_interval`)、`sonic-buildimage/src/sonic-supervisord-utilities-rs/src/proc_exit_listener.rs:212-233` (Rust 版)、`sonic-buildimage/dockers/docker-orchagent/orchagent.sh:127-130` 精読 (2026-05-19)
> 詳細証跡: `meta/_intermediate/cdb-flow/heartbeat-pubsub.md`

### 購読方式: なし (起動時の一括読み込みのみ — Redis pub/sub 不使用)

`HEARTBEAT` テーブルを読む全コンシューマは **Redis keyspace notification / ConsumerStateTable / SubscriberStateTable を使用しない**。CONFIG_DB への HSET 書き込みに対して Redis の publish 通知は発火するが、これを受け取る購読プロセスは存在しない。

| コンポーネント | 読み方式 | タイミング | 備考 |
|---|---|---|---|
| `supervisor-proc-exit-listener` (Python) | `ConfigDBConnector.get_table("HEARTBEAT")` | 起動時 1 回のみ (`load_heartbeat_alert_interval()` L124-135) | 起動後に CONFIG_DB を再読しない。変更は daemon 再起動後に有効 |
| `supervisor-proc-exit-listener` (Rust) | `config_db.get_table(HEARTBEAT_TABLE_NAME)` | 起動時 1 回のみ (`proc_exit_listener.rs:212-233`) | 同上 |
| `orchagent.sh` | `sonic-db-cli CONFIG_DB hget "HEARTBEAT\|orchagent" heartbeat_interval` | orchagent 起動スクリプト実行時 1 回 (`orchagent.sh:127-130`) | 取得値を `-I <interval>` フラグとして orchagent プロセスに引数渡しする |
| `eventd` | CONFIG_DB を**直接読まない** | — | ZeroMQ RPC (`GLOBAL_OPTION_HEARTBEAT`) 経由でのみ interval を受け取る |

### 変更の反映経路

Redis keyspace notification は発火するが受信側が存在しないため、実質的な反映経路は daemon 再起動のみ:

```
管理者: sonic-db-cli CONFIG_DB HSET "HEARTBEAT|<name>" alert_interval <v>
  ↓ Redis keyspace notification "__keyspace@4__:HEARTBEAT|<name>" が PUBLISH される
  ↓ (受信する SubscriberStateTable / ConsumerStateTable は存在しない — 通知は捨てられる)
次回 supervisor-proc-exit-listener 再起動時に load_heartbeat_alert_interval() が再読み込み
```

### APPL_DB / SAI 中継

なし。`HEARTBEAT` テーブルはホストサービス（supervisord 管理下デーモン）の監視設定であり、APPL_DB / STATE_DB / ASIC_DB への伝播も SAI 書き込みも発生しない。

<!-- /pubsub -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `HEARTBEAT`

### CLI
- なし (CLI 書き込みパスなし)

### minigraph / sonic-cfggen
- なし

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/SONiC YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- なし

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- `system-health` / `watchdog` 系デーモンが定期的に heartbeat タイムスタンプを書き込む。CLI 書き込みパスなし
<!-- /entry-points -->

<!-- glossary-links-injected: d5320e852f7a -->
