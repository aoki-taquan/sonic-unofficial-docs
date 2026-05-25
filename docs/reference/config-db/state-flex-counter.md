---
title: FLEX_COUNTER_DB — ランタイム状態フィールド
description: "FLEX_COUNTER_DB（DB 5）のランタイム状態フィールド — syncd の FlexCounter モジュールが管理する per-group ポーリング状態とコード由来デフォルト。"
area: reference
verification: code-verified
last_verified: 2026-05-18
hard: 0
sources:
  - repo: sonic-net/sonic-sairedis
    path: syncd/FlexCounter.cpp
    ref: master
  - repo: sonic-net/sonic-sairedis
    path: syncd/FlexCounterManager.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/flexcounterorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
related:
  config_db:
    - FLEX_COUNTER_TABLE
  yang:
    - sonic-flex_counter
  cli:
    - counterpoll
---

# FLEX_COUNTER_DB ランタイム状態フィールド

## 概要

[SONiC](../../reference/glossary.md#term-sonic) のハードウェアカウンタポーリングは **3 つの DB** にまたがって動作する[^1]:

| DB | 番号 | 役割 |
|----|------|------|
| `CONFIG_DB` | 4 | ユーザ設定（`FLEX_COUNTER_TABLE`）|
| `FLEX_COUNTER_DB` | 5 | [orchagent](../../reference/glossary.md#term-orchagent) → [syncd](../../reference/glossary.md#term-syncd) 制御信号（group 設定 + per-OID ID リスト）|
| `COUNTERS_DB` | 2 | [syncd](../../reference/glossary.md#term-syncd) → 外部 読み取り専用の実カウンタ値 |

本ページは **[FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db)**（DB 5）のランタイム状態フィールドと、[syncd](../../reference/glossary.md#term-syncd) 内 `FlexCounter` モジュールが持つコード由来デフォルト値を記述する。


## FLEX_COUNTER_DB のテーブル構造

### FLEX_COUNTER_GROUP_TABLE — グループ制御

```text
FLEX_COUNTER_GROUP_TABLE|<group>
```

[orchagent](../../reference/glossary.md#term-orchagent) が書き込む group-level 制御フィールド:

| フィールド | 型 | 説明 |
|----------|----|------|
| `POLL_INTERVAL` | uint32 (ms) | ポーリング間隔 |
| `FLEX_COUNTER_STATUS` | `enable` / `disable` | ポーリング有効化 |
| `STATS_MODE` | `STATS_MODE_READ` / `STATS_MODE_READ_AND_CLEAR` | カウンタ読み取りモード |
| `BULK_CHUNK_SIZE` | uint32 | 1 回の [SAI](../../reference/glossary.md#term-sai) bulk API で処理するエントリ数 |
| `BULK_CHUNK_SIZE_PER_PREFIX` | string | プレフィクス別チャンクサイズ |

### FLEX_COUNTER_TABLE — per-OID カウンタ ID リスト

```text
FLEX_COUNTER_TABLE|<group>|<oid>
  <COUNTER_ID_LIST_FIELD> = <comma-separated SAI stat enum>
```

[orchagent](../../reference/glossary.md#term-orchagent) の各 Orch（PortsOrch / IntfsOrch / BufferOrch 等）が、`FLEX_COUNTER_STATUS = enable` を受信すると、ハードウェアオブジェクトごとにエントリを書き込む。詳細は [`counters-flex`](counters-flex.md) を参照。

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

<!-- evidence: sonic-sairedis/syncd/FlexCounter.cpp,
     sonic-sairedis/syncd/FlexCounterManager.cpp,
     sonic-swss/orchagent/flexcounterorch.cpp,
     sonic-swss/orchagent/portsorch.cpp,
     sonic-buildimage/files/build_templates/init_cfg.json.j2,
     sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang,
     sonic-utilities/counterpoll/main.py,
     sonic-utilities/scripts/db_migrator.py -->

### FlexCounter インスタンス初期状態

`FlexCounter::FlexCounter(...)` コンストラクタ（[FlexCounter](../../reference/glossary.md#term-flexcounter).cpp:3031-3051）の初期値:

| フィールド | 初期値 | 意味 |
|-----------|--------|------|
| `m_enable` | `false` | `FLEX_COUNTER_STATUS = enable` 受信前はポーリング無効 |
| `m_pollInterval` | `0` | 0ms ではポーリングループが実行されない |
| `m_readyToPoll` | `false` | ID リスト未登録状態 |
| `m_isDiscarded` | `false` | インスタンス有効状態 |

**ポーリング実行条件**（[FlexCounter](../../reference/glossary.md#term-flexcounter).cpp:3538）:

```cpp
if (m_enable && !allIdsEmpty() && (m_pollInterval > 0))
```

3 条件すべてが `true` でないとポーリングしない。config が正しく投入されていても ID リストが空の場合は動作しない。

### `FLEX_COUNTER_STATUS` の暗黙デフォルト

`setStatus()` は `enable` / `disable` のみ受け付ける。その他の値は `SWSS_LOG_WARN` でスキップされ `m_enable` は変更されない（[FlexCounter](../../reference/glossary.md#term-flexcounter).cpp:3079-3083）:

```cpp
if (cit == statusMap.cend())
{
    SWSS_LOG_WARN("Input value %s is not supported ...", status.c_str());
    return;
}
```

未設定時は `m_enable = false`（ポーリング無効）。

### `STATS_MODE` の暗黙デフォルト

`setStatsMode()` が処理するフィールド:

| 値 | 意味 | 用途 |
|----|------|------|
| `STATS_MODE_READ` | 読み取りのみ（デフォルト） | PORT, QUEUE, PG_DROP 等 |
| `STATS_MODE_READ_AND_CLEAR` | 読み取り後クリア | QUEUE_WATERMARK, PG_WATERMARK |

`portsorch.cpp:866-886` が `QUEUE_WATERMARK` と `PG_WATERMARK` グループに対して `STATS_MODE_READ_AND_CLEAR` を明示投入する。設定なし時は `STATS_MODE_READ` 扱い。

### portsorch.cpp ハードコード初期ポーリング間隔

FlexCounter グループ作成時、[portsorch](../../reference/glossary.md#term-portsorch).cpp:87-93 で定義された定数が初期 `POLL_INTERVAL` として [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に書き込まれる。[CONFIG_DB](../../reference/glossary.md#term-config_db) の `POLL_INTERVAL` 値で後から上書き可能。

| グループ | ハードコード初期値 | 定数名 |
|---------|-------------------|--------|
| `PORT` | 1000 ms | `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `PORT_BUFFER_DROP` | 60000 ms | `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS` |
| `PORT_PHY_ATTR` | 10000 ms | `PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `QUEUE` | 10000 ms | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `QUEUE_WATERMARK` | 60000 ms | `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `PG_WATERMARK` | 60000 ms | `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `PG_DROP` | 10000 ms | `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` |
| `WRED_ECN_PORT` | 1000 ms | `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` と共用 |
| `WRED_ECN_QUEUE` | 10000 ms | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` と共用 |

**[YANG](../../reference/glossary.md#term-yang) との乖離**: [YANG](../../reference/glossary.md#term-yang)（sonic-flex_counter.yang）の `poll_interval` typedef は `range 100..4294967295` で統一。[portsorch](../../reference/glossary.md#term-portsorch) のハードコード値は YANG バリデーション対象外。[CONFIG_DB](../../reference/glossary.md#term-config_db) `POLL_INTERVAL` が未設定でも [portsorch](../../reference/glossary.md#term-portsorch) 初期化時に [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) へ書き込まれるため、`counterpoll show` 表示とは異なる実値になる場合がある。

### FlexCounterOrch m_* フラグ初期値

`flexcounterorch.cpp:433-478` の各 `get*State()` メソッドが返すフラグ:

| フラグ | 対応グループ | 初期値 |
|--------|-------------|--------|
| `m_port_counter_enabled` | `PORT` | `false` |
| `m_port_buffer_drop_counter_enabled` | `PORT_BUFFER_DROP` | `false` |
| `m_queue_enabled` | `QUEUE` | `false` |
| `m_queue_watermark_enabled` | `QUEUE_WATERMARK` | `false` |
| `m_pg_enabled` | `PG_DROP` | `false` |
| `m_pg_watermark_enabled` | `PG_WATERMARK` | `false` |
| `m_wred_port_counter_enabled` | `WRED_ECN_PORT` | `false` |
| `m_wred_queue_counter_enabled` | `WRED_ECN_QUEUE` | `false` |
| `m_route_flow_counter_enabled` | `FLOW_CNT_ROUTE` | `false` |

これらのフラグは portsorch / intfsOrch 等が新しいポート・[RIF](../../reference/glossary.md#term-rif) を追加したときに、カウンタ ID リストを FLEX_COUNTER_DB に書き込むかどうかを制御する。フラグが `false` のままでは `FLEX_COUNTER_STATUS = enable` が書き込まれていても ID リスト登録が行われずポーリングは起動しない（3 条件のうち `allIdsEmpty()` が `true` のため）。

### `BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX` の挙動

FLEX_COUNTER_DB レベルの bulk 設定:

| 種類 | 内容 |
|------|------|
| 未設定時 fallback | orchagent は `"NULL"` 文字列を FLEX_COUNTER_DB に送信。syncd 側で chunk size 無限（上限なし）として扱われる |
| 片方のみ設定 | 未設定側は `"NULL"` で自動補完（flexcounterorch.cpp:405）。ユーザへの通知なし |
| 両方省略 UPDATE | `m_groupsWithBulkChunkSize` から erase → `"NULL","NULL"` を送信してリセット |

### warm-reboot / fast-reboot との関係

FLEX_COUNTER_DB は warm-reboot 後に全クリアされ、orchagent 起動時に再構築される。

`db_migrator.py` の migration:

| migration | 条件 | 動作 |
|-----------|------|------|
| `migrate_config_db_flex_counter_delay_status` | fast-reboot 前 | [CONFIG_DB](../../reference/glossary.md#term-config_db) `FLEX_COUNTER_TABLE` 全エントリの `FLEX_COUNTER_DELAY_STATUS` を `true` に強制上書き |
| `migrate_flex_counter_delay_status_removal` | cross-branch upgrade 時 | `FLEX_COUNTER_DELAY_STATUS` フィールドを全エントリから削除 |

**FLEX_COUNTER_DELAY_STATUS の通常起動時挙動**: orchagent コンストラクタで `m_delayTimerExpired = true` が即セットされるため、通常起動では遅延なし。フィールドは fast-reboot 専用。

### STATE_DB との関係

[STATE_DB](../../reference/glossary.md#term-state_db)（DB 6）に FLEX_COUNTER 専用の独立テーブルはない。FLEX_COUNTER システムが [STATE_DB](../../reference/glossary.md#term-state_db) を参照するのは syncd の warm-reboot 状態（`STATE_DB:WARM_RESTART_TABLE`）のみ（Syncd.cpp:5824）。ポーリング状態・カウンタ値は FLEX_COUNTER_DB と [COUNTERS_DB](../../reference/glossary.md#term-counters_db) で完結する。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`FlexCounterOrch` → `FLEX_COUNTER_DB` → `syncd FlexCounter` の 3 段パイプラインでは、`FLEX_COUNTER_GROUP_TABLE`（グループ制御）と `FLEX_COUNTER_TABLE`（per-OID カウンタ ID リスト）が **別の [Redis](../../reference/glossary.md#term-redis) キー空間**に書き込まれるため、syncd が受信するイベントの順序は保証されない。ポーリング起動条件（`m_enable && !allIdsEmpty() && m_pollInterval > 0`）が揃うまでの間は中間状態が観測しうる。

### 検出された順序依存

| # | 依存関係 | 方向 | 中間状態 | 緩和策 |
|---|----------|------|---------|--------|
| 1 | `FLEX_COUNTER_GROUP_TABLE` STATUS=enable と `FLEX_COUNTER_TABLE` OID リストの syncd 到着順不定 | [Redis](../../reference/glossary.md#term-redis) イベントキュー | `m_enable=true` + OID 空、または OID あり + `m_enable=false` — どちらも 3 条件が揃った時点でポーリング自動起動 | `FlexCounter::addCounter()` / `setStatus()` は独立更新、3 条件チェックは毎ポーリングループで再評価 |
| 2 | portsorch ハードコード `POLL_INTERVAL` 書込み → CONFIG_DB 値による上書き | 起動順序（init → doTask） | orchagent 起動直後〜`FlexCounterOrch::doTask()` が CONFIG_DB 値を処理するまで FLEX_COUNTER_DB には portsorch 初期値が入っている | `counterpoll interval <group> <ms>` で再設定すると即上書き可能 |
| 3 | `FLEX_COUNTER_STATUS=enable` 受信 → `generatePortCounterMap()` → `setFlexCounterGroupOperation()` の 2 ステップ | 単一 doTask イテレーション内 | COUNTER_TABLE SET と GROUP_TABLE SET は別 [Redis](../../reference/glossary.md#term-redis) write — syncd では依存 #1 と同様に別イベントとして到達 | 最終的に収束（依存 #1 の自動解消と同様） |
| 4 | PortsOrch ポート初期化完了 → OID 逐次追加 | 起動シーケンス（initPort() ループ） | orchagent 起動直後は `FLEX_COUNTER_TABLE` が空 → `allIdsEmpty()=true` でポーリング無効 | `initPort()` が各 Ethernet<N> を追加するたびに OID リストが追記され、最終的にすべてのポートがカバーされる |

### 主要な制約詳細

**GROUP_TABLE / COUNTER_TABLE 到着順不定 (依存 #1)**: Syncd のメインループ（`Syncd.cpp:5982,5986`）は `m_flexCounter`（`FLEX_COUNTER_TABLE`）と `m_flexCounterGroup`（`FLEX_COUNTER_GROUP_TABLE`）を別の `swss::Selectable` として `swss::Select::addSelectable()` で登録する。Redis 通知はキューの到着順に配信されるため、orchagent 側での書込み順とは独立して syncd に届く。`processFlexCounterGroupEvent()` が `STATUS=enable` を処理して `FlexCounter::setStatus(true)`（`m_enable=true`）にした後でも `allIdsEmpty()` が真であればポーリングは開始されない。逆に `processFlexCounterEvent()` が OID リストを先に登録しても `m_enable=false` のままではポーリングしない。いずれの順序でも 3 条件が揃い次第（次回ポーリングスレッドの判定で）ポーリングが起動する（`FlexCounter.cpp:3538`）。

**起動直後のポート OID 逐次追加 (依存 #4)**: `FlexCounterOrch::doTask()` が `FLEX_COUNTER_STATUS=enable` を受信した時点で `gPortsOrch->generatePortCounterMap()` を呼ぶが（`flexcounterorch.cpp:237-244`）、この時点で portsorch が `initPort()` を完了していないポートは OID リストに含まれない。その後 portsorch が `initPort()` で各ポートを追加するたびに `m_port_counter_enabled` フラグ（`flexcounterorch.cpp:240`）を参照して FLEX_COUNTER_TABLE への OID 追記が行われる。結果として起動後のポーリング対象は徐々に拡大し、全ポート初期化完了後に安定する。

**ハードコード POLL_INTERVAL の先行書込み (依存 #2)**: `portsorch.cpp:87-93` で定義された定数（`PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 1000` 等）は portsorch コンストラクタ内で `FlexCounterOrch::createCounterTable()` を通じて FLEX_COUNTER_GROUP_TABLE に書き込まれる。その後 orchagent の通常 doTask ループで CONFIG_DB の `POLL_INTERVAL` フィールドが処理されると `setFlexCounterGroupPollInterval()` で上書きされる。CONFIG_DB に `POLL_INTERVAL` が設定されていない場合、portsorch のハードコード値がそのまま有効になるが、YANG `poll_interval` typedef（`range 100..4294967295`）のバリデーション対象外であることに注意。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照マップ (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/state-flex-counter-cross-refs.md -->

`FlexCounterOrch` が `FLEX_COUNTER_DB` へ書き込む際に暗黙的に参照・依存する CONFIG_DB / APP_DB テーブルおよびOrch 内状態。

| 参照方向 | このテーブル | 相手テーブル / Orch | 条件 |
|---------|------------|-------------------|------|
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `CONFIG_DB:DEVICE_METADATA` `.create_only_config_db_buffers` | コンストラクタで hget; `"true"` のとき Queue/PG 設定で非ゼロプロファイルのポートのみ対象に絞る (`flexcounterorch.cpp:106-120`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gPortsOrch->allPortsReady()` | doTask 先頭ガード; PortsOrch が未初期化なら全イベントを silent defer (`flexcounterorch.cpp:164-167`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gFabricPortsOrch->allPortsReady()` | 同上; Fabric 版PortsOrch ガード (`flexcounterorch.cpp:169-172`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gPortsOrch->generate*Map()` 各メソッド | `FLEX_COUNTER_STATUS=enable` 時に PORT/QUEUE/PG/[WRED](../../reference/glossary.md#term-wred) 系グループのOIDリストを FLEX_COUNTER_DB へ書き込む起点 (`flexcounterorch.cpp:235-295`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gIntfsOrch->generateInterfaceMap()` | `RIF` グループ enable 時。[RIF](../../reference/glossary.md#term-rif) OIDリストを FLEX_COUNTER_DB へ登録 (`flexcounterorch.cpp:283-286`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gBufferOrch->generateBufferPoolWatermarkCounterIdList()` | `BUFFER_POOL_WATERMARK` グループ enable 時 (`flexcounterorch.cpp:287-290`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `APP_DB:BUFFER_QUEUE` / `APP_DB:BUFFER_PG` | `create_only_config_db_buffers=true` 時に `gBufferOrch->getBufferObjectsWithNonZeroProfile()` 経由で参照; 非ゼロプロファイルキュー/PGのみ対象 (`flexcounterorch.cpp:554,623`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `VxlanTunnelOrch->generateTunnelCounterMap()` | `TUNNEL` グループ enable 時。VxlanTunnelOrch を `gDirectory.get<>()` で動的取得 (`flexcounterorch.cpp:295-299`) |
| FlexCounterOrch → | `FLEX_COUNTER_TABLE` | `gFlowCounterRouteOrch->generateRouteFlowStats()` | `FLOW_CNT_ROUTE` グループ enable 時 (`flexcounterorch.cpp:325-332`) |
| warm-reboot 遅延 | — | `WarmStart::isWarmStart()` | warm-reboot 時は `m_delayTimerExpired=false` で起動し 60 秒間 doTask を全スキップ。CONFIG_DB 更新が届いても FLEX_COUNTER_DB は更新されない (`flexcounterorch.cpp:44,127-136,155-158`) |

### 参照関係サマリ

```
CONFIG_DB:FLEX_COUNTER_TABLE
  → FlexCounterOrch::doTask()
      ├─ [guard]  gPortsOrch->allPortsReady()              (未完了なら silent defer)
      ├─ [guard]  gFabricPortsOrch->allPortsReady()        (未完了なら silent defer)
      ├─ [guard]  m_delayTimerExpired                      (warm-reboot 時 60s 遅延)
      ├─ [config] DEVICE_METADATA.create_only_config_db_buffers
      ├─ FLEX_COUNTER_DB:FLEX_COUNTER_GROUP_TABLE|<group>  (POLL_INTERVAL/STATUS/STATS_MODE/BULK)
      └─ FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|<group>|<oid>
            ├─ gPortsOrch->generate*Map()  ... PORT / QUEUE / PG / WRED
            ├─ gFabricPortsOrch->generateQueueStats()  ... FABRIC_QUEUE
            ├─ gIntfsOrch->generateInterfaceMap()      ... RIF
            ├─ gBufferOrch->generateBufferPoolWatermarkCounterIdList()  ... BUFFER_POOL
            ├─ VxlanTunnelOrch->generateTunnelCounterMap()  ... TUNNEL
            └─ gFlowCounterRouteOrch->generateRouteFlowStats()  ... FLOW_CNT_ROUTE
```

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/state-flex-counter-failure.md -->

FLEX_COUNTER_DB への書き込みと syncd 内 `FlexCounter` ポーリングの各障害経路を示す。**[COUNTERS_DB](../../reference/glossary.md#term-counters_db) への影響**に着目することが重要で、失敗時には「書き込まれない」か「stale 値が残留する」かのどちらかになる。

### FlexCounterOrch 側の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | FLEX_COUNTER_DB への影響 |
|---|---|---|---|
| `gPortsOrch->allPortsReady()` が `false` | `flexcounterorch.cpp:164-167` | `doTask()` が即 `return`。CONFIG_DB イベントは `m_toSync` に残留 | FLEX_COUNTER_DB への書き込みなし。準備完了後に一括処理 |
| `gFabricPortsOrch->allPortsReady()` が `false` | `flexcounterorch.cpp:169-172` | 同上 | 同上 |
| warm-reboot 遅延中 (`m_delayTimerExpired == false`) の CONFIG_DB 更新 | `flexcounterorch.cpp:155-158` | 60 秒間 `doTask()` を全スキップ | FLEX_COUNTER_DB 未更新。タイマー満了後に `m_toSync` を一括処理 |
| `generate*Map()` が空のポートリストを返す | `flexcounterorch.cpp:237-295` (各 generate* 関数) | OID リストが空のまま `FLEX_COUNTER_TABLE` に書き込まれる | `allIdsEmpty()=true` のためポーリング起動しない（3 条件未充足） |
| CONFIG_DB `BUFFER_QUEUE` / `BUFFER_PG` キー形式不正 | `flexcounterorch.cpp:561, 630` | `SWSS_LOG_ERROR`、該当エントリをスキップ | 不正キーに対応する OID は FLEX_COUNTER_TABLE に登録されない |

### FlexCounter（syncd 側）の失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | [COUNTERS_DB](../../reference/glossary.md#term-counters_db) への影響 |
|---|---|---|---|
| `FLEX_COUNTER_STATUS` に `"enable"` / `"disable"` 以外の値 | `FlexCounter.cpp:3074-3084` | `SWSS_LOG_WARN`、`m_enable` 変更なし | ポーリング状態は変化しない。不正値は FLEX_COUNTER_DB に残留 |
| `BULK_CHUNK_SIZE` に数値変換不能な値 | `FlexCounter.cpp:3176-3183` | `catch(...)` で捕捉、`SWSS_LOG_ERROR`、`bulkChunkSize` は変更しない | 既存の chunk size 設定が継続、ポーリングは継続 |
| 未知フィールドが FLEX_COUNTER_GROUP_TABLE に到着 | `FlexCounter.cpp:3230-3236` | `SWSS_LOG_ERROR("Field is not supported %s")`、無視 | FLEX_COUNTER_DB・COUNTERS_DB への影響なし |
| [SAI](../../reference/glossary.md#term-sai) 単体 `getStats()` 失敗（非 `SAI_STATUS_SUCCESS`） | `FlexCounter.cpp:1249-1258` | `return false`、当該 OID をスキップ | COUNTERS_DB の当該 OID エントリは更新されず **stale 値が残留** |
| [SAI](../../reference/glossary.md#term-sai) `clearStats()` 失敗（`STATS_MODE_READ_AND_CLEAR` 時） | `FlexCounter.cpp:1261-1282` | `return false`、`SWSS_LOG_ERROR` | COUNTERS_DB は getStats 成功分を書いた後でクリアされない（値は更新済みだがカウンタは非リセット） |
| SAI `bulkGetStats()` 呼び出し失敗（ステータス非 SUCCESS） | `FlexCounter.cpp:1339-1344` | `SWSS_LOG_WARN`、`current += bulk_chunk_size` で処理継続 | 失敗チャンク内の OID は `object_statuses[i]` が非 SUCCESS → COUNTERS_DB 書き込みをスキップ（`continue`、`FlexCounter.cpp:1363`）。stale 値残留 |
| `removeCounterContext()` で存在しないコンテキスト名 | `FlexCounter.cpp:3484` | `SWSS_LOG_ERROR`、処理継続 | COUNTERS_DB・FLEX_COUNTER_DB は変化しない |

### 失敗時の COUNTERS_DB エントリ挙動

```
SAI getStats 単体失敗
  → COUNTERS_DB|<oid>.<stat_id>  … 前回値が stale として残存

SAI bulkGetStats チャンク失敗
  → 失敗 OID は COUNTERS_DB 書き込みをスキップ（stale 残留）
  → 成功 OID は正常に書き込まれる（同一チャンク内で混在）

allPortsReady 未達 / m_delayTimerExpired=false
  → FLEX_COUNTER_TABLE に OID が登録されない
  → allIdsEmpty()=true のままポーリング自体が起動しない
  → COUNTERS_DB には何も書かれない（エントリなし）
```

### エラーの観測方法

```bash
# STATUS 設定の確認（不正値の検出）
sonic-db-cli FLEX_COUNTER_DB hget 'FLEX_COUNTER_GROUP_TABLE|PORT' FLEX_COUNTER_STATUS

# OID リストが空かを確認（allIdsEmpty 状態）
sonic-db-cli FLEX_COUNTER_DB keys 'FLEX_COUNTER_TABLE|PORT|*' | wc -l
# 0 の場合はポーリング無効（PORT グループの例）

# COUNTERS_DB エントリの stale 確認（タイムスタンプ比較）
sonic-db-cli COUNTERS_DB hget 'COUNTERS:0x<oid>' SAI_PORT_STAT_IF_IN_OCTETS

# syslog でエラー確認
journalctl -u syncd | grep "Failed to get stats"
journalctl -u swss | grep "flexcounterorch\|FlexCounter"
```

SAI 失敗は `SWSS_LOG_ERROR` または `SWSS_LOG_WARN` で syslog に出力される。`ERROR_TABLE` への書き込みはいずれの失敗経路でも行われない。

> **証跡**: `flexcounterorch.cpp:155-172`（doTask ガード）、`flexcounterorch.cpp:44,127-136`（warm-reboot 遅延）、`flexcounterorch.cpp:561, 630`（バッファキー不正）、`FlexCounter.cpp:3074-3084`（STATUS 不正値）、`FlexCounter.cpp:3176-3183`（BULK_CHUNK_SIZE 不正）、`FlexCounter.cpp:3230-3236`（未知フィールド）、`FlexCounter.cpp:1249-1282`（getStats / clearStats 失敗）、`FlexCounter.cpp:1339-1363`（bulkGetStats 失敗）、`FlexCounter.cpp:3484`（removeCounterContext 不在）。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp,
     sonic-swss/orchagent/portsorch.h,
     sonic-swss-common/common/schema.h -->

FLEX_COUNTER_DB の GROUP_TABLE / COUNTER_TABLE で使われるフィールド名・グループ名・タイムアウト値はすべてコード内定数で決まる。YANG スキーマや CONFIG_DB のキー名とは独立しており、ユーザが直接変更することはできない。

### FLEX_COUNTER_GROUP_TABLE フィールド名定数 (`sonic-swss-common/common/schema.h`)

| 定数名 | 文字列値 | 行 |
|---|---|---|
| `POLL_INTERVAL_FIELD` | `"POLL_INTERVAL"` | `schema.h:320` |
| `STATS_MODE_FIELD` | `"STATS_MODE"` | `schema.h:322` |
| `STATS_MODE_READ` | `"STATS_MODE_READ"` | `schema.h:323` |
| `STATS_MODE_READ_AND_CLEAR` | `"STATS_MODE_READ_AND_CLEAR"` | `schema.h:324` |
| `FLEX_COUNTER_STATUS_FIELD` | `"FLEX_COUNTER_STATUS"` | `schema.h:335` |
| `FLEX_COUNTER_GROUP_TABLE` | `"FLEX_COUNTER_GROUP_TABLE"` | `schema.h:336` |
| `BULK_CHUNK_SIZE_FIELD` | `"BULK_CHUNK_SIZE"` | `schema.h:318` |
| `BULK_CHUNK_SIZE_PER_PREFIX_FIELD` | `"BULK_CHUNK_SIZE_PER_PREFIX"` | `schema.h:319` |

### CONFIG_DB キー → FLEX_COUNTER グループ名マッピング (`flexcounterorch.cpp:68-83`)

`flexCounterGroupMap` は CONFIG_DB の `FLEX_COUNTER_TABLE` キー文字列から FLEX_COUNTER_DB グループ名への変換テーブル。

| CONFIG_DB キー (`#define`) | 値 | FLEX_COUNTER_GROUP 名 |
|---|---|---|
| `PORT_KEY` | `"PORT"` | `"PORT_STAT_COUNTER"` |
| `PORT_BUFFER_DROP_KEY` | `"PORT_BUFFER_DROP"` | `"PORT_BUFFER_DROP_STAT"` |
| `PORT_PHY_ATTR_KEY` | `"PORT_PHY_ATTR"` | `"PORT_PHY_ATTR"` |
| `PORT_PHY_SERDES_ATTR_KEY` | `"PORT_PHY_SERDES_ATTR"` | `"PORT_PHY_SERDES_ATTR"` |
| `QUEUE_KEY` | `"QUEUE"` | `"QUEUE_STAT_COUNTER"` |
| `QUEUE_WATERMARK` | `"QUEUE_WATERMARK"` | `"QUEUE_WATERMARK_STAT_COUNTER"` |
| `PG_WATERMARK_KEY` | `"PG_WATERMARK"` | `"PG_WATERMARK_STAT_COUNTER"` |
| `PG_DROP_KEY` | `"PG_DROP"` | `"PG_DROP_STAT_COUNTER"` |
| `WRED_QUEUE_KEY` | `"WRED_ECN_QUEUE"` | `"WRED_ECN_QUEUE_STAT_COUNTER"` |
| `WRED_PORT_KEY` | `"WRED_ECN_PORT"` | `"WRED_ECN_PORT_STAT_COUNTER"` |
| `RIF_KEY` | `"RIF"` | `"RIF_STAT_COUNTER"` |
| `TUNNEL_KEY` | `"TUNNEL"` | `"TUNNEL_STAT_COUNTER"` |
| `FLOW_CNT_TRAP_KEY` | `"FLOW_CNT_TRAP"` | `"HOSTIF_TRAP_COUNTER"` |
| `FLOW_CNT_ROUTE_KEY` | `"FLOW_CNT_ROUTE"` | `"FLOW_CNT_ROUTE"` |
| `SWITCH_KEY` | `"SWITCH"` | `"SWITCH_STAT_COUNTER"` |
| `SRV6_KEY` | `"SRV6"` | `"SRV6_STAT_COUNTER"` |

### warm-reboot 遅延タイムアウト定数 (`flexcounterorch.cpp:44`)

```cpp
#define FLEX_COUNTER_DELAY_SEC 60
```

warm-reboot 時に FlexCounterOrch が FLEX_COUNTER_DB への書き込みを遅延させる秒数。変更には orchagent のリビルドが必要。この値は YANG モデルも CONFIG_DB も参照しない純粋なコード定数。

### portsorch.cpp ハードコード初期ポーリング間隔定数 (`portsorch.cpp:87-93`, `portsorch.h:29-43`)

PortsOrch コンストラクタが `FlexCounterManager` 初期化時に直接渡すポーリング間隔。CONFIG_DB の `FLEX_COUNTER_TABLE.<group>.POLL_INTERVAL` 値で後から上書き可能だが、orchagent 起動直後はこれらの定数値が FLEX_COUNTER_DB に書き込まれる。

| 定数名 | 値 | 対応グループ |
|---|---|---|
| `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 1000 ms | `PORT_STAT_COUNTER`, `WRED_ECN_PORT_STAT_COUNTER` |
| `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS` | 60000 ms | `PORT_BUFFER_DROP_STAT` |
| `PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | `PORT_PHY_ATTR`, `PORT_PHY_SERDES_ATTR` |
| `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | `QUEUE_STAT_COUNTER`, `WRED_ECN_QUEUE_STAT_COUNTER` |
| `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 60000 ms | `QUEUE_WATERMARK_STAT_COUNTER` |
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 60000 ms | `PG_WATERMARK_STAT_COUNTER` |
| `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | `PG_DROP_STAT_COUNTER` |

**YANG との乖離**: YANG の `poll_interval` typedef は `range 100..4294967295`。orsorch のコード定数は YANG バリデーション対象外で、60000 ms 等は YANG の最大値制約に収まるが YANG モデルから検証する手段はない。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

> 調査証跡: `sonic-sairedis/syncd/FlexCounter.cpp`、`sonic-swss-common/common/schema.h`

`FLEX_COUNTER_DB` のエントリが設定・削除されると、syncd 内 `FlexCounter` スレッドを通じて以下の DB への副次書き込みが発生する。

### SET 時（ポーリング起動後） → COUNTERS_DB 書込み

| 対象 DB / テーブル | キー / フィールド | 書込内容 | トリガー |
|------------------|-----------------|---------|---------|
| `COUNTERS_DB` / `COUNTERS:<oid>` | `SAI_*_STAT_*` | SAI から取得した統計カウンタ値（uint64 文字列） | ポーリング条件 3 つが揃って `collectCounters()` が実行されたとき（`FlexCounter.cpp:3543`） |
| `COUNTERS_DB` / `PORT_PHY_ATTR:<oid>` | 各 PHY 属性フィールド | ポート PHY 属性（[SerDes](../../reference/glossary.md#term-serdes) パラメータ等） | `PORT_PHY_ATTR` グループのポーリング（`FlexCounter.cpp:1984-2005`） |
| `COUNTERS_DB` / `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP` | `<serdes_oid>` → `<port_oid>` | Serdes OID → Port OID マッピング | `PORT_PHY_SERDES_ATTR` グループの初期登録（`FlexCounter.cpp:2251-2260`） |

**ポーリング書込みタイミング**: `FlexCounter::flexCounterThreadRunFunction()`（`FlexCounter.cpp:3526`）が `m_pollInterval` ms ごとに `collectCounters()` を呼び出し、`COUNTERS_TABLE`（= `COUNTERS:`）への書込みを Redis パイプライン経由でフラッシュする。書込みは各ポーリング周期の終わりにまとめて行われ（`pipeline.flush()`）、周期中の中間状態は COUNTERS_DB に現れない。

**Lua プラグインの追加書込み**: `runPlugins()` が各カウンタコンテキストの登録プラグインを実行する。プラグインは COUNTERS_DB に対して任意の追加書き込みを行う可能性がある（例: `RATES:<oid>` への書き込みは Lua レートプラグインが担当する）。

### DEL 時（OID 削除） → COUNTERS_DB 削除

| 操作 | 対象テーブル | 削除キー |
|------|------------|---------|
| ポート / [RIF](../../reference/glossary.md#term-rif) / Queue 等の OID 削除 | `COUNTERS_DB:COUNTERS` | `<vid>` のエントリ全体 |
| RIF OID 削除 | `COUNTERS_DB:RATES` | `<vid>` / `<vid>:RIF` |
| Trap OID 削除 | `COUNTERS_DB:RATES` | `<vid>` / `<vid>:TRAP` |

`FlexCounter::removeDataFromCountersDB()` (`FlexCounter.cpp:3116-3133`) が `COUNTERS:<vid>` を del し、`ratePrefix` が指定された場合は `RATES:<vid>` / `RATES:<vid>:<prefix>` も del する。

### FLEX_COUNTER_DB 書込みが COUNTERS_DB に影響しない条件

| 条件 | 理由 |
|------|------|
| `m_enable == false` かつ OID リスト空 | ポーリングスレッドが `waitPoll()` でブロックされる（ポーリング 3 条件未充足） |
| SAI `getStats()` / `bulkGetStats()` 失敗 | 当該 OID の書込みをスキップ（stale 残留）。`COUNTERS_DB` の旧値は上書きされない |
| グループ `FLEX_COUNTER_STATUS = disable` | `m_enable = false` となりポーリングが停止。`COUNTERS_DB` は最後に書かれた値が残留（削除されない） |

> **参照ソース**: `FlexCounter.cpp:3526-3569`（`flexCounterThreadRunFunction`）、`FlexCounter.cpp:3495-3507`（`collectCounters`）、`FlexCounter.cpp:3116-3133`（`removeDataFromCountersDB`）、`schema.h:223`（`COUNTERS_TABLE`）、`schema.h:272`（`RATES_TABLE`）

<!-- /side-effects -->

<!-- pubsub -->
## Redis 通知メカニズム (Phase G)

### 書き込み側 orchagent の通信構造

orchagent 内の各 Orch（`FlexCounterOrch` / `PortsOrch` / `IntfsOrch` / `BufferOrch` 等）は `FLEX_COUNTER_DB`（DB 5）に対して **`ProducerTable`** 経由で書き込む。`ProducerTable` は Lua スクリプトで `LPUSH` + `PUBLISH` をアトミックに実行するため、書き込みと同時にチャネルへの通知が発行される（`producertable.cpp:38`）。

| 書き込みコンポーネント | 書き込み先テーブル | 使用クラス |
|----------------------|-----------------|-----------|
| `FlexCounterOrch::doTask()` | `FLEX_COUNTER_GROUP_TABLE` | `ProducerTable` |
| `PortsOrch::initPort()` など各 Orch | `FLEX_COUNTER_TABLE` | `ProducerTable` (FlexCounterManager 経由) |

### 購読方式: ConsumerTable + SUBSCRIBE

syncd は `Syncd::Syncd()` コンストラクタ（`Syncd.cpp:209-210`）で **`ConsumerTable`** を生成し、FLEX_COUNTER_DB の 2 テーブルを購読する:

| ConsumerTable インスタンス | 購読チャネル | 生成箇所 |
|--------------------------|------------|---------|
| `m_flexCounter` | `FLEX_COUNTER_TABLE_CHANNEL@5` | `Syncd.cpp:209` |
| `m_flexCounterGroup` | `FLEX_COUNTER_GROUP_TABLE_CHANNEL@5` | `Syncd.cpp:210` |

`ConsumerTable` は構築時に `SUBSCRIBE <TABLE>_CHANNEL@<dbId>` を発行し、`ProducerTable` からの PUBLISH を受け取る（`consumertable.cpp:31`）。

### syncd 主ループ — 永続 blocking select

`Syncd::run()` のメインループ（`Syncd.cpp:5832-5856`）は `swss::Select` に上記 2 ConsumerTable を登録し、イベント到着まで永続ブロックする:

```cpp
s->addSelectable(m_selectableChannel.get());   // orchagent → syncd 主チャネル
s->addSelectable(m_restartQuery.get());         // warm-reboot/fast-reboot 制御
s->addSelectable(m_flexCounter.get());          // FLEX_COUNTER_TABLE イベント
s->addSelectable(m_flexCounterGroup.get());     // FLEX_COUNTER_GROUP_TABLE イベント
```

`swss::Select` は Linux epoll を使用し、タイムアウト指定なし（`UINT_MAX`）で永続ブロックする。受信したセレクタに応じて `processFlexCounterEvent()` または `processFlexCounterGroupEvent()` を呼び出す（`Syncd.cpp:477-486`）:

```cpp
if (temps == m_flexCounter.get())
    processFlexCounterEvent(key, SET_COMMAND, kfvFieldsValues(kco));
else if (temps == m_flexCounterGroup.get())
    processFlexCounterGroupEvent(key, SET_COMMAND, kfvFieldsValues(kco));
```

### FlexCounter ポーリングスレッドの内部 Wakeup

`FlexCounter` ポーリングスレッドは条件変数 `m_cvSleep`（`std::condition_variable`）で待機する。設定変更時には `m_cvSleep.notify_all()` でスレッドを即時 wakeup する:

| 変更操作 | wakeup 発生箇所 |
|---------|---------------|
| `FLEX_COUNTER_STATUS` 変更（enable/disable） | `FlexCounter.cpp:3089` |
| `POLL_INTERVAL` 変更 | `FlexCounter.cpp:3068` |
| `STATS_MODE` 変更 | `FlexCounter.cpp:3110` |
| スレッド終了 (`endFlexCounterThread`) | `FlexCounter.cpp:3597` |

3 条件（`m_enable && !allIdsEmpty() && m_pollInterval > 0`）が揃わない場合はスレッドが `waitPoll()`（`FlexCounter.cpp:3902`）に戻り、次の wakeup まで待機する。ポーリング自体に外部 Redis SUBSCRIBE は使われず、内部スレッド間の条件変数のみで制御される。

### イベント到達タイムライン（通常起動時）

```
orchagent FlexCounterOrch::doTask()
  LPUSH FLEX_COUNTER_GROUP_TABLE_KEY_VALUE_OP_QUEUE|5    (STATUS=enable)
  PUBLISH FLEX_COUNTER_GROUP_TABLE_CHANNEL@5  1
      ↓
syncd Syncd::run() select() wakeup
  processFlexCounterGroupEvent("PORT", SET, {STATUS=enable})
    → FlexCounter::setStatus("enable") → m_enable=true → m_cvSleep.notify_all()
      ↓
FlexCounter ポーリングスレッド wakeup
  if (m_enable && !allIdsEmpty() && m_pollInterval > 0)  ← allIdsEmpty チェック
    collectCounters() → COUNTERS_DB 書込み
```

orchagent 側の `FLEX_COUNTER_TABLE`（OID リスト）と `FLEX_COUNTER_GROUP_TABLE`（グループ制御）は別チャネルで独立して届くため、syncd が STATUS=enable を先に受信するケースと OID リストを先に受信するケースの両方が発生しうる。いずれの順序でも 3 条件が揃った次回ポーリングスレッド判定時にポーリングが起動する（Phase B「書込み順依存 #1」参照）。

> **参照ソース**: `Syncd.cpp:208-212, 5832-5856, 477-486`（主ループ）、`consumertable.cpp:31`（SUBSCRIBE）、`producertable.cpp:38`（PUBLISH）、`table.h:85-96`（チャネル名生成）、`FlexCounter.cpp:3068, 3089, 3110, 3597, 3902`（条件変数 wakeup）

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

> 詳細証跡: `meta/_intermediate/cdb-flow/state-flex-counter-platform.md`

FLEX_COUNTER_DB のテーブル名・チャネル名・`FlexCounter` 制御ロジック自体はプラットフォーム非依存だが、**どのカウンタグループが FLEX_COUNTER_DB に生成されるか**はプラットフォーム構成に依存する。

### Gearbox (外付け PHY) 有効時 — PORT / MACSEC グループへの追加書き込み

`gPortsOrch->isGearboxEnabled()` が `true` の場合のみ、`PORT` グループおよび `MACSEC_*` グループのポーリング間隔・enable 状態が **Gearbox 専用の `FlexCounterManager` インスタンスにも同時に書き込まれる**（`flexcounterorch.cpp:204-212, 382-390`）。

```cpp
if (gPortsOrch && gPortsOrch->isGearboxEnabled())
{
    if (key == PORT_KEY || key.rfind("MACSEC", 0) == 0)
    {
        setFlexCounterGroupPollInterval(flexCounterGroupMap[key], value, true);  // true = gearbox instance
        setFlexCounterGroupOperation(flexCounterGroupMap[key], value, true);
    }
}
```

Gearbox なし構成ではこのコードパスは実行されず、Gearbox 用 FLEX_COUNTER_DB エントリは生成されない。

### MACsec ハードウェアオフロード — MACSEC_SA / MACSEC_FLOW グループ

`MACSEC_SA`・`MACSEC_SA_ATTR`・`MACSEC_FLOW` の 3 グループは `flexCounterGroupMap` に定義されており（`flexcounterorch.cpp:89-91`）、[MACsec](../../reference/glossary.md#term-macsec) オフロード有効プラットフォーム (`macsecorch` が初期化される構成) でのみ `FLEX_COUNTER_GROUP_TABLE|MACSEC_*` エントリが FLEX_COUNTER_DB に書き込まれる。[MACsec](../../reference/glossary.md#term-macsec) 非搭載構成では `macsecorch` が存在せず、これらのグループは生成されない。

### VOQ chassis — QUEUE グループの一括展開

[VOQ](../../reference/glossary.md#term-voq) シャーシ（`gMySwitchType == "voq"`）では、BUFFER_QUEUE CONFIG_DB 設定の有無に関わらず**全フロントパネルポートおよびシステムポートの全 egress queue と VoQ** に対して `FLEX_COUNTER_TABLE|QUEUE|<oid>` が FLEX_COUNTER_DB に一括書き込まれる（`flexcounterorch.cpp:544-558`）。非 [VOQ](../../reference/glossary.md#term-voq) 環境では `BUFFER_QUEUE` にプロファイル設定を持つキューのみが対象になる。

### FabricPortsOrch — ファブリックポート Queue カウンタ

`gFabricPortsOrch` が初期化されている構成（ファブリックスイッチまたはファブリックポートを持つ構成）では、`FLEX_COUNTER_STATUS = enable` 受信時に `gFabricPortsOrch->generateQueueStats()` が追加呼び出しされる（`flexcounterorch.cpp:291-294`）。ファブリックポートなし構成では `gFabricPortsOrch == nullptr` でスキップされる。また、ファブリックポートが全部 ready になるまで CONFIG_DB 変更処理自体がブロックされる（`flexcounterorch.cpp:169`）。

### DASH / ENI / SmartSwitch — ENI / DASH_METER / HA_SET グループ

`DashOrch` / `DashHaOrch` が初期化される [SmartSwitch](../../reference/glossary.md#term-smartswitch) 構成では `ENI`・`DASH_METER`・`HA_SET` グループへのポーリング制御が連動する（`flexcounterorch.cpp:299-314`）。標準 BOX スイッチでは `dash_orch == nullptr` であり、これらのコードパスは到達されない。

### FLEX_COUNTER_DB 制御フィールド自体はプラットフォーム共通

`FLEX_COUNTER_GROUP_TABLE` のフィールド（`POLL_INTERVAL`・`FLEX_COUNTER_STATUS`・`STATS_MODE`・`BULK_CHUNK_SIZE`）、`FlexCounter::setStatus` / `setStatsMode` / `setPollInterval` の処理ロジック、DB 番号（5）・テーブル名・チャネル名（`schema.h` 定義）はすべてプラットフォーム非依存。各カウンタの SAI 統計値取得（`sai_*_stats` API）は [ASIC SDK](../../reference/glossary.md#term-asic-sdk) に依存するが、FLEX_COUNTER_DB のフィールド設計には影響しない。

<!-- /platform -->

## 確認コマンド

```bash
# FLEX_COUNTER_DB の group 設定確認
sonic-db-cli FLEX_COUNTER_DB keys 'FLEX_COUNTER_GROUP_TABLE|*'
sonic-db-cli FLEX_COUNTER_DB hgetall 'FLEX_COUNTER_GROUP_TABLE|PORT'

# per-OID カウンタ ID リスト確認
sonic-db-cli FLEX_COUNTER_DB keys 'FLEX_COUNTER_TABLE|PORT|*' | head -5

# CONFIG_DB の設定確認
counterpoll show

# 実カウンタ値確認（COUNTERS_DB）
sonic-db-cli COUNTERS_DB keys 'COUNTERS:*' | head -5
```

<!-- ref-triangle:start -->

## 関連リファレンス

- [FLEX_COUNTER_TABLE テーブル](flex-counter-table.md) — CONFIG_DB グループ設定
- [FLEX_COUNTER 個別カウンタフィールド](counters-flex.md) — FLEX_COUNTER_DB per-OID ID リスト
- [YANG](../../reference/glossary.md#term-yang): [`sonic-flex_counter`](../yang/sonic-flex_counter.md)
- CLI: `counterpoll`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-swss-common/common/schema.h`: `COUNTERS_DB = 2`, `FLEX_COUNTER_DB = 5`, `STATE_DB = 6`. <https://github.com/sonic-net/sonic-swss-common/blob/master/common/schema.h>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 1c64d648249a -->
