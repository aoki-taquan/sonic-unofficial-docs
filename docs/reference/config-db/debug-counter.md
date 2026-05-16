---
title: DEBUG_COUNTER テーブル
description: "DEBUG_COUNTER テーブル — SAI debug counter（パケットドロップ要因別の汎用カウンタ）を CONFIG_DB から定義するテーブル。debugcounterorch (orchagent) が消費し、SAI debug counter オブジェクトを作成する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-debug-counter.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DEBUG_COUNTER
    - DEBUG_COUNTER_DROP_REASON
    - DEBUG_DROP_MONITOR
  cli:
    - config debug counter
    - show debug counter
  yang:
    - sonic-debug-counter
hard: 0
---

# DEBUG_COUNTER テーブル

## 概要

[SAI](../../reference/glossary.md#term-sai) debug counter（パケットドロップ要因別の汎用カウンタ）を [CONFIG_DB](../../reference/glossary.md#term-config_db) から定義するテーブル[^1]。`debugcounterorch` ([orchagent](../../reference/glossary.md#term-orchagent)) が消費し、[SAI](../../reference/glossary.md#term-sai) debug counter オブジェクトを作成する。各カウンタには別テーブル `DEBUG_COUNTER_DROP_REASON` でドロップ理由 (`L3_ANY`、`SMAC_EQUALS_DMAC` 等) が紐付く。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>DEBUG_COUNTER")]
  DM["DebugCounterOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_debug_counter_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
DEBUG_COUNTER|<name>
DEBUG_COUNTER_DROP_REASON|<name>|<reason>
DEBUG_DROP_MONITOR|CONFIG          # global setting (container)
```

## フィールド (`DEBUG_COUNTER_LIST`)

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `name` | string | - | カウンタ識別名（key） |
| `alias` | string | - | カウンタ別名 |
| `desc` | string | - | カウンタ説明 |
| `group` | string | - | グルーピング名 |
| `drop_monitor_status` | `stypes:admin_mode` | `disabled` | ドロップモニタ機能の有効化 |
| `window` | uint64 (sec) | `900` | モニタ時間窓の長さ（秒） |
| `incident_count_threshold` | uint64 | `3` | syslog を発火させるインシデント数閾値 |
| `drop_count_threshold` | uint64 | `100` | インシデント判定するドロップ数閾値 |
| `type` | `stypes:debug_counter_type` | - (mandatory) | スコープ／方向: `PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` / `SWITCH_INGRESS_DROPS` / `SWITCH_EGRESS_DROPS` 等 |

## 派生テーブル

- `DEBUG_COUNTER_DROP_REASON_LIST` (key: `name reason`)
  - `name`: 親 `DEBUG_COUNTER_LIST.name` 存在チェック付き (`must` 制約)
  - `reason`: `stypes:counter_drop_reason` 列挙（[SAI](../../reference/glossary.md#term-sai) のドロップ理由一覧）
- `DEBUG_DROP_MONITOR/CONFIG/status`: 永続的ドロップ監視機能のグローバル ON/OFF（admin_mode、既定 `disabled`）

## 制約

- `type` は **mandatory**（[YANG](../../reference/glossary.md#term-yang) `mandatory true`）
- `DEBUG_COUNTER_DROP_REASON.name` は親 `DEBUG_COUNTER_LIST.name` に存在することが必須

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

- **allPortsReady 未到達 → 全更新ペンディング**: ポート初期化完了前は `DebugCounterOrch::doTask()` が即 return し全 DEBUG_COUNTER 更新を保留する。<!-- evidence: debugcounterorch.cpp L137-140 -->
- **未サポートカウンタ種別 → task_failed**: `counter_type` が `supported_counter_types` に含まれない場合 `SWSS_LOG_ERROR("Specified counter type '%s' is not supported.")` → `task_failed`。<!-- evidence: debugcounterorch.cpp L389 -->
- **無効 / 未サポートな drop_reason → task_failed**: `isDropReasonValid()` が false か `supported_*_drop_reasons` に含まれない場合 `SWSS_LOG_ERROR` → `task_failed`。<!-- evidence: debugcounterorch.cpp L445, L451-453 -->
- **counter 未存在への drop_reason 追加 → free_drop_counters で保留**: DEBUG_COUNTER エントリより先に DROP_REASON 更新が来た場合、`free_drop_reasons` に保存し counter 作成時に `reconcileFreeDropCounters()` で適用 (順序非依存)。<!-- evidence: debugcounterorch.cpp L460-465 -->
- **最後の drop_reason の削除 → task_ignore**: drop_reasons が 1 件のときに `removeDropReason()` を呼ぶと `SWSS_LOG_WARN("Attempted to remove all drop reasons from counter")` → `task_ignore`。drop counter は最低 1 つの理由が必要。<!-- evidence: debugcounterorch.cpp L476-479 -->
- **更新はべき等・失敗は状態を変更しない**: 失敗した更新はシステム状態を変更しない。同一リクエストの繰り返しは同一結果となる。<!-- evidence: debugcounterorch.cpp L128-130 -->

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

| フィールド | YANG default | 実行時 fallback | 種別 | evidence |
|---|---|---|---|---|
| `alias` | なし | **無視** (SAI・FlexCounter に不伝播) | dead field | `debugcounterorch.cpp:726-758` |
| `desc` | なし | **無視** (同上) | dead field | `debugcounterorch.cpp:726-758` |
| `group` | なし | **無視** (同上) | dead field | `debugcounterorch.cpp:726-758` |
| `drop_monitor_status` | `"disabled"` | `false` (C++ メンバ初期値) | YANG default = 実装整合 | `debugcounterorch.h:102` |
| `window` | `900` 秒 | **`0`** (Lua `tonumber(nil) or 0`) | YANG default 外 fallback — 欠損時は全インシデントを即クリア | `drop_monitor.lua:34` |
| `incident_count_threshold` | `3` | **`0`** (同 Lua fallback) | YANG default 外 fallback — 欠損時は 1 インシデントでアラート発火 | `drop_monitor.lua:33, 80` |
| `drop_count_threshold` | `100` | **`0`** (同 Lua fallback) | YANG default 外 fallback — 欠損時は 1 ドロップでインシデント登録 | `drop_monitor.lua:32, 59` |
| `type` | mandatory | 欠損時は空文字 → `task_failed` | mandatory 違反は silent empty fallback 後に task_failed | `debugcounterorch.cpp:385-391` |

### 補足: ハードコード固定値・プラットフォーム依存

- **FlexCounter polling interval**: `60000` ms ハードコード（`debugcounterorch.h:21` `DEBUG_DROP_MONITOR_FLEX_COUNTER_POLLING_INTERVAL_MS`）。`window` の精度はこの値に依存。
- **PHY ポートのみ対象**: `PORT_DEBUG` カウンタは `Port::Type::PHY` のみ追跡。LAG・VLAN・CPU ポートは silent skip（`debugcounterorch.cpp:639`）。
- **SAI 非サポート環境**: `sai_query_attribute_enum_values_capability` が失敗すると `supported_counter_types` が空になり、全カウンタ作成が `task_failed`（`drop_counter.cpp:380-384`）。
- **drop_reason 未設定の counter**: SAI オブジェクトを作成せず `free_drop_counters` に保留。`task_success` を返すが SAI 上にカウンタは存在しない（partial pending）（`debugcounterorch.cpp:393-394`）。
<!-- /defaults -->

<!-- value-behavior -->
## 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `type` | `PORT_INGRESS_DROPS` | `CounterType::PORT_DEBUG` として扱い、ポート単位に SAI debug counter を作成（`debugcounterorch.cpp:19`）。各ポートの ingress ドロップを個別に集計。ポート削除時にカウンタも削除される。 |
| `type` | `PORT_EGRESS_DROPS` | `CounterType::PORT_DEBUG` として扱い、ポート単位に SAI debug counter を作成（`debugcounterorch.cpp:20`）。各ポートの egress ドロップを個別に集計。 |
| `type` | `SWITCH_INGRESS_DROPS` | `CounterType::SWITCH_DEBUG` として扱い、スイッチ全体のグローバルカウンタを作成（`debugcounterorch.cpp:21`）。全ポート合算の ingress ドロップを集計。 |
| `type` | `SWITCH_EGRESS_DROPS` | `CounterType::SWITCH_DEBUG` として扱い、スイッチ全体のグローバルカウンタを作成（`debugcounterorch.cpp:22`）。全ポート合算の egress ドロップを集計。 |
| `drop_monitor_status` | `enabled` | `debug_monitor_enabled=true` をセット。ドロップ検知時に syslog アラートを発火する（`debugcounterorch.cpp:649, 708`）。 |
| `drop_monitor_status` | `disabled`（既定） | アラート発生なし。カウンタの蓄積は継続するが通知は行わない。 |
| `drop_monitor_status` | その他の値 | `SWSS_LOG_ERROR` を出力して拒否。`enabled`/`disabled` 以外は無効（`debugcounterorch.cpp:257`）。 |
<!-- /value-behavior -->

## 購読者

- `debugcounterorch` ([orchagent](../../reference/glossary.md#term-orchagent)): SAI debug counter (sai_debug_counter) を作成し、ドロップ理由のセットを反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `COUNTERS_DEBUG_NAME_MAP` ([COUNTERS_DB](../../reference/glossary.md#term-counters_db) 側)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-debug-counter`
- 関連 CLI: `config debug counter` / `show debug counter` 系

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-debug-counter`](../yang/sonic-debug-counter.md)
- CLI: `config debug counter` / `show debug counter`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-debug-counter.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-debug-counter.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `DEBUG_COUNTER|<name>`。
- `type`: `PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` / `SWITCH_INGRESS_DROPS` 等。`reasons`: drop reason の CSV。

### よくある誤設定

- プラットフォーム SAI が未対応の reason を指定すると CrmOrch がエラーを出してカウンタが作られない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'DEBUG_COUNTER|*'
show dropcounters configuration
```
<!-- /ops-hint -->


<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`DebugCounterOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `DEBUG_COUNTER` テーブルを購読する。

`DEBUG_COUNTER` と `DEBUG_COUNTER_DROP_REASON` は対で使用。drop reason リストで集計対象を指定。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_debug_counter_api` — デバッグカウンタ (drop reason 集計) を SAI に作成/削除

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後即座に SAI debug counter を作成/削除。カウンタは作成後即座に集計開始。

**副作用**: デバッグカウンタはハードウェアリソースを消費。作成後は `COUNTERS_DB` に counter OID がマッピングされ `show dropcounters` で確認可能。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `DEBUG_COUNTER`

### CLI
- `config debug-counter add/del <name>`
- `config debug-counter add-reasons/remove-reasons <name> <reason>`
  - ソース: `sonic-utilities/config/main.py (debug-counter グループ)`

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
- なし
<!-- /entry-points -->


<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 値による他フィールド自動派生

| 条件 | 派生先 | evidence |
|---|---|---|
| 派生なし（DEBUG_COUNTER は CLI / sonic-mgmt-common 経由でのみ書き込まれる） | — | — |

### Phase 7: 条件付き module/manager 登録

| 条件 | 登録 module | evidence |
|---|---|---|
| 常時（条件なし） | `DebugCounterOrch` が `DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON` を `doTask` で購読 | `sonic-swss/orchagent/debugcounterorch.cpp:129` |

### grep カバレッジ

- debugcounterorch.cpp L129-220: doTask 登録（条件なし）
<!-- /derivation -->
<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

| Manager / Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `DebugCounterOrch` | `doTask()` | `!gPortsOrch->allPortsReady()` | 早期 `return`（全ポート初期化待ちガード） | `sonic-swss/orchagent/debugcounterorch.cpp:137` |
| `DebugCounterOrch` | `doTask()` | `table_name == CFG_DEBUG_COUNTER_TABLE_NAME` | `installDebugCounter()` / `uninstallDebugCounter()` を呼び出し | `sonic-swss/orchagent/debugcounterorch.cpp:151` |
| `DebugCounterOrch` | `doTask()` | `table_name == CFG_DEBUG_COUNTER_DROP_REASON_TABLE_NAME` | `addDropReason()` / `removeDropReason()` を呼び出し（別パス） | `sonic-swss/orchagent/debugcounterorch.cpp:182` |
| `DebugCounterOrch` | `doTask()` | `op == SET_COMMAND`（DEBUG_COUNTER テーブル） | `installDebugCounter()` 実行 | `sonic-swss/orchagent/debugcounterorch.cpp:153` |
| `DebugCounterOrch` | `doTask()` | `op == DEL_COMMAND`（DEBUG_COUNTER テーブル） | `uninstallDebugCounter()` 実行 | `sonic-swss/orchagent/debugcounterorch.cpp:165` |

> **スキャン証跡**: `doTask` L129-220 全行読了。`allPortsReady()` ガードと 2 テーブルの dispatch 分岐が核心。5 件抽出。
<!-- /handler-branching -->
<!-- ordering -->
## 書込み順依存 (Phase B)

### 前提条件: allPortsReady() ガード

`doTask()` は `gPortsOrch->allPortsReady()` が false の間は即 return する。ポート初期化完了前は `DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON` / `DEBUG_DROP_MONITOR` のいずれの処理もブロックされる。CONFIG_DB への書き込み自体は受け付けるが、orchagent が処理するのはポート初期化完了後。<!-- evidence: debugcounterorch.cpp L136-139 -->

### DEBUG_COUNTER と DEBUG_COUNTER_DROP_REASON の到着順序

DROP_REASON が counter より先に届いても動作する。`addDropReason()` は counter が未存在の場合 `free_drop_reasons` に理由を蓄積し、`reconcileFreeDropCounters()` で counter と理由が揃った時点で SAI debug counter を作成する。ただし **両エントリが揃うまで SAI counter は存在せず集計は行われない**。<!-- evidence: debugcounterorch.cpp L456-466, L579-594 -->

### type 変更は DEL → SET が必須

`installDebugCounter()` は counter_name が既に `debug_counters` に存在する場合 `task_success` を即返して更新しない（冪等）。`type` を変更するには `DEL DEBUG_COUNTER|<name>` で削除後に `SET` で再作成する必要がある。SET のみでの上書きはサイレント無視。<!-- evidence: debugcounterorch.cpp L374-377 -->

### 最後の DROP_REASON は削除不可

`removeDropReason()` は `drop_reasons.size() <= 1` の場合 `task_ignore` を返して削除しない。drop counter は SAI 上で最低 1 つの理由が必要なため制約。counter を削除したい場合は DROP_REASON を全削除してから counter を DEL する手順は機能しない。`DEL DEBUG_COUNTER|<name>` を直接使うこと。<!-- evidence: debugcounterorch.cpp L476-501 -->

### counter DEL 前の free_drop_reasons 孤立

counter が SAI 未作成（`free_drop_counters` 状態）のまま DEL すると、`free_drop_reasons` に残った理由はクリアされない。その後同名で SET すると孤立していた理由が引き継がれる副作用がある。対策: counter 作成をキャンセルする場合は `DEL DEBUG_COUNTER_DROP_REASON|<name>|<reason>` で理由を先に削除する。<!-- evidence: debugcounterorch.cpp L400-417, L526-538 -->

### DEBUG_DROP_MONITOR の有効化タイミング

`DEBUG_DROP_MONITOR|CONFIG` の `status=enabled` 設定時はその時点で存在する全ポートに `startFlexCounterPolling()` を呼ぶ。有効化後に追加された `PORT_DEBUG` 型 counter も即時モニタ登録される。有効化タイミングの前後で挙動が変わるわけではないが、有効化前に追加されたカウンタは有効化時に一括登録、有効化後の追加は counter 作成時に個別登録という経路の違いがある。<!-- evidence: debugcounterorch.cpp L232-243, L649-656 -->

### restart / warm-reboot

`debug_counters` / `free_drop_counters` / `free_drop_reasons` はインメモリのみで永続化しない。orchagent 再起動後は Consumer が CONFIG_DB の全エントリを replay し `reconcileFreeDropCounters()` で自動復元する。warm-reboot も同様。再起動中の集計値は失われるが設定は自動復元される。<!-- evidence: debugcounterorch.cpp L579-594 -->

<!-- /ordering -->
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON` は **YANG leafref を PORT / FLEX_COUNTER_DB / STATE_DB / COUNTERS_DB に対して持たない**。以下はすべて実装レベルの暗黙参照。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `PORT` (CONFIG_DB / PortsOrch) | 読み取り（ポート一覧取得 + 変更イベント購読） | `PORT_INGRESS_DROPS` / `PORT_EGRESS_DROPS` 型カウンタ作成時。`gPortsOrch->getAllPorts()` で `Port::Type::PHY` のみ FlexCounter 登録対象に選択。ポート追加/削除で `installDebugFlexCounters()` / `uninstallDebugFlexCounters()` が自動呼び出し。 | `debugcounterorch.cpp:16,39,71,92,106,629,682` |
| `FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE` (`DEBUG_COUNTER` グループ) | 書き込み（orchagent → syncd 経路） | `DebugCounterOrch` コンストラクタで初期化。カウンタ作成/削除時に `flex_counter_manager.addFlexCounterStat()` / `removeFlexCounterStat()` で stat を登録・解除。 | `debugcounterorch.cpp:25-29,625,644; debugcounterorch.h:19` |
| `FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE` (`DEBUG_MONITOR_COUNTER` グループ) | 書き込み（drop monitor Lua 用） | コンストラクタで `setFlexCounterGroupParameter(DEBUG_DROP_MONITOR_FLEX_COUNTER_GROUP, ...)` を呼び、drop_monitor.lua を Lua プラグインとして登録。`drop_monitor_status=enabled` 時に `startFlexCounterPolling()` でポーリング開始。 | `debugcounterorch.cpp:55-59,241,651,710; debugcounterorch.h:20-21` |
| `STATE_DB DEBUG_COUNTER_CAPABILITIES` | 書き込み（自身が情報源） | 起動時 1 回 `publishDropCounterCapabilities()` が SAI に `sai_query_attribute_enum_values_capability` を投げ、サポートされているカウンタ種別・drop reason 一覧を書き込む。 | `debugcounterorch.cpp:31,314-361` |
| `COUNTERS_DB COUNTERS_DEBUG_NAME_PORT_STAT_MAP` | 書き込み（counter_name → port stat OID マップ） | PORT_DEBUG 型カウンタ作成時に `m_counterNameToPortStatMap->set()` で書き込む。`drop_monitor.lua` がポーリング時にこのマップを参照する。 | `debugcounterorch.cpp:33; drop_monitor.lua:18-19` |
| `COUNTERS_DB COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP` | 書き込み（counter_name → switch stat OID マップ） | SWITCH_DEBUG 型カウンタ作成時。`show dropcounters` が参照する逆引きマップ。 | `debugcounterorch.cpp:34` |

!!! note "PORT leafref が存在しない理由"
    `sonic-debug-counter.yang` は PORT テーブルへの leafref を定義しない。`PORT_INGRESS_DROPS` 型カウンタはポート単位に SAI オブジェクトを作るが、CONFIG_DB エントリには port 名を含まない。ポートとの紐付けは orchagent が `gPortsOrch->getAllPorts()` で動的に解決する。

!!! note "FLEX_COUNTER_DB への書き込みは間接的"
    `DebugCounterOrch` は直接 FLEX_COUNTER_DB に書かず、`FlexCounterManager` / `flex_counter_manager` 経由で書き込む。`FlexCounterManager` が `FLEX_COUNTER_GROUP_TABLE` / `FLEX_COUNTER_TABLE` を管理する。

詳細な参照経路・行番号は `meta/_intermediate/cdb-flow/debug-counter-cross-refs.md` を参照。

<!-- /cross-refs -->

<!-- glossary-links-injected: d2c490dcfe8c -->
