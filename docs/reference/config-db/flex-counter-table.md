---
title: FLEX_COUNTER_TABLE テーブル
description: "FLEX_COUNTER_TABLE テーブル — orchagent / syncd に対し、各種ハードウェアカウンタのポーリング有効化と周期、bulk API のチャンクサイズを指定するテーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-14
hard: 0
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-flex_counter.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/flexcounterorch.cpp
    ref: master
  - repo: sonic-net/sonic-utilities
    path: counterpoll/main.py
    ref: master
related:
  config_db:
    - FLEX_COUNTER_TABLE
    - FLOW_COUNTER_ROUTE_PATTERN
  cli:
    - counterpoll
  yang:
    - sonic-flex_counter
---

# FLEX_COUNTER_TABLE テーブル

## 概要

[orchagent](../../reference/glossary.md#term-orchagent) / [syncd](../../reference/glossary.md#term-syncd) に対し、各種ハードウェアカウンタのポーリング有効化と周期、bulk API のチャンクサイズを指定するテーブル[^1]。`syncd` の `FlexCounter` モジュールがこのテーブルを購読し、[SAI](../../reference/glossary.md#term-sai) bulk counter API の周期呼び出しスケジュールを切り替える。fast-reboot 時の `FLEX_COUNTER_DELAY_STATUS = true` で system-ready まで停止可能。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>FLEX_COUNTER_TABLE")]
  DM["syncd"]
  CDB --> DM
  SAI["SAI<br/>sai_*_stats"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
FLEX_COUNTER_TABLE|<group>
```

`<group>` は固定の counter グループ名。23 グループ前後が [YANG](../../reference/glossary.md#term-yang) で定義される（下表）。

## 共通フィールド

各グループ共通でとりうる leaf:

| フィールド | 型 | 説明 |
|-----------|----|------|
| `FLEX_COUNTER_STATUS` | enum `enable`/`disable` | ポーリング有効化 |
| `FLEX_COUNTER_DELAY_STATUS` | `boolean_type` | system-ready まで起動遅延 |
| `POLL_INTERVAL` | uint32 (100..2^32-1) [ms] | ポーリング間隔 |
| `BULK_CHUNK_SIZE` | uint32 (1..2^32-1) | 1 回の bulk API で扱うエントリ数 |
| `BULK_CHUNK_SIZE_PER_PREFIX` | string | プレフィクス別 bulk チャンクサイズ |

各グループは上記のうち一部のみ持つ（例: `PFCWD` は `FLEX_COUNTER_STATUS` と `FLEX_COUNTER_DELAY_STATUS` のみ）。

## 主なグループ

| グループ | 対象 |
|----------|------|
| `BUFFER_POOL_WATERMARK` | バッファプール watermark |
| `DEBUG_COUNTER` | drop reason 等のデバッグカウンタ |
| `ENI` | [DASH](../../reference/glossary.md#term-dash) [ENI](../../reference/glossary.md#term-eni) カウンタ |
| `DASH_METER` / `HA_SET` | [DASH](../../reference/glossary.md#term-dash) 関連 |
| `PFCWD` | [PFC](../../reference/glossary.md#term-pfc) watchdog |
| `PG_DROP` / `PG_WATERMARK` | priority group ドロップ / watermark |
| `PORT` / `PORT_RATES` / `PORT_BUFFER_DROP` / `PORT_PHY_ATTR` | ポート系 |
| `QUEUE` / `QUEUE_WATERMARK` | キュー系 |
| `RIF` / `RIF_RATES` | router-interface 系 |
| `ACL` | [ACL](../../reference/glossary.md#term-acl) ヒットカウンタ |
| `FLOW_CNT_TRAP` | host-IF trap flow |
| `FLOW_CNT_ROUTE` | route flow（`FLOW_COUNTER_ROUTE_PATTERN` と連携） |
| `TUNNEL` | tunnel 系 |
| `WRED_ECN_QUEUE` / `WRED_ECN_PORT` | [WRED](../../reference/glossary.md#term-wred)/ECN マーキング |
| `SRV6` | [SRv6](../../reference/glossary.md#term-srv6) |
| `SWITCH` | スイッチレベルグローバル |

## 関連サブテーブル

- `FLOW_COUNTER_ROUTE_PATTERN` (key: `ip_prefix`): default [VRF](../../reference/glossary.md#term-vrf) のルートフロー対象パターン
    - `max_match_count` (uint32, 1..50): バインドする最大ルート数
- `FLOW_COUNTER_ROUTE_PATTERN` の [VRF](../../reference/glossary.md#term-vrf) 版 list (key: `vrf_name`, `ip_prefix`): [VRF](../../reference/glossary.md#term-vrf) / [VNET](../../reference/glossary.md#term-vnet) 名スコープ

## 購読者

- `syncd` の `FlexCounter`: [SAI](../../reference/glossary.md#term-sai) bulk counter API スケジュール
- `FlexCounterOrch` ([orchagent](../../reference/glossary.md#term-orchagent) 内)
- `pfcwd`、`watermarkmgr` 等のカウンタ依存モジュール

<!-- pubsub -->
## 通信メカニズム (Phase G)

`FlexCounterOrch` は `Orch` 基底クラス経由で `FLEX_COUNTER_TABLE` を購読する。[CONFIG_DB](../../reference/glossary.md#term-config_db) 起源のため `Orch::addConsumer()` の DB 種別分岐で **`SubscriberStateTable`** が選ばれ、[Redis](../../reference/glossary.md#term-redis) の **keyspace 通知** (`__keyspace@4__:FLEX_COUNTER_TABLE:*` の PSUBSCRIBE) を購読する。channel ベースの `PUBLISH` は使用しない。

| 項目 | 値 |
|------|-----|
| 購読クラス | `SubscriberStateTable` ([CONFIG_DB](../../reference/glossary.md#term-config_db) / [STATE_DB](../../reference/glossary.md#term-state_db) / CHASSIS_APP_DB 分岐) |
| keyspace パターン | `__keyspace@4__:FLEX_COUNTER_TABLE:*` (CONFIG_DB dbId=4) |
| key 区切り | `FLEX_COUNTER_TABLE\|<group>` (TableNameSeparator 既定 `\|`) |
| POP_BATCH_SIZE | `TableConsumable::DEFAULT_POP_BATCH_SIZE` = **128** (`sonic-swss-common/common/table.h:164`) |
| 優先度 (`pri`) | 0 (`TableConnector` 既定) |
| 起動時スナップショット | `SubscriberStateTable` が既存エントリを SET イベントとして再配信 |
| TTL | 未設定 (CONFIG_DB は永続前提) |
| ディスパッチ | `Consumer::execute()` → `FlexCounterOrch::doTask(Consumer&)` → `key` でグループ判定 → SAI flex counter group 更新 |

`FlexCounterOrch` が変更を受信後、SAI 呼び出しパスは **2 系統**ある:

1. **新方式 (gTraditionalFlexCounter=false)**: `setFlexCounterGroupOperation()` / `setFlexCounterGroupPollInterval()` が `sai_redis_flex_counter_group_parameter_t` を構築し、`SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` 属性で `notifySyncdCounterOperation()` を呼ぶ。SAI/[syncd](../../reference/glossary.md#term-syncd) 側で flex counter polling が制御される。
2. **旧方式 (gTraditionalFlexCounter=true)**: `operateFlexCounterGroupDatabase()` が `FLEX_COUNTER_DB` の `FLEX_COUNTER_GROUP_TABLE` (`ProducerTable: gFlexCounterGroupTable`) に直接書き込み、[syncd](../../reference/glossary.md#term-syncd) が `ConsumerStateTable` 経由で読む。

[FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) は `saihelper.cpp:323` で `DBConnector("FLEX_COUNTER_DB", 0)` として初期化。CONFIG_DB Consumer → [orchagent](../../reference/glossary.md#term-orchagent) 内処理 → [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) writer / SAI counter API の一方向フローとなる。

<!-- evidence: sonic-net/sonic-swss/orchagent/flexcounterorch.cpp:102L (FlexCounterOrch::FlexCounterOrch via Orch(db, tableNames)) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orch.cpp:1188L (Orch::addConsumer DB 種別分岐 CONFIG_DB→SubscriberStateTable) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orchdaemon.cpp:620L (flex_counter_tables 定義, FlexCounterOrch 生成) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/saihelper.cpp:323L (gFlexCounterDb = DBConnector("FLEX_COUNTER_DB")) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/saihelper.cpp:918L (setFlexCounterGroupOperation SAI 呼び出し) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/saihelper.cpp:941L (setFlexCounterGroupPollInterval SAI 呼び出し) -->
<!-- /pubsub -->

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `FLOW_COUNTER_ROUTE_PATTERN`、`COUNTERS_DB`（実カウンタ値の読み出し先）
- 関連 CLI: `counterpoll <group> enable/disable`、`counterpoll <group> interval <ms>`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-flex_counter`

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-flex_counter`](../yang/sonic-flex_counter.md)
- CLI: `counterpoll`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-flex_counter.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-flex_counter.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Telemetry / SNMP / Observability](../../topics/09-telemetry-snmp/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `FLEX_COUNTER_TABLE|<group>` (PORT / QUEUE / PG_WATERMARK / [RIF](../../reference/glossary.md#term-rif) 等)`。
- `FLEX_COUNTER_STATUS`: `enable`、`POLL_INTERVAL`: 1000〜10000ms。

### よくある誤設定

- POLL_INTERVAL を極端に短く（100ms 等）するとカウンタ集計で CPU が貼り付く。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'FLEX_COUNTER_TABLE|*'
counterpoll show
```
<!-- /ops-hint -->

<!-- value-behavior -->
## 値依存挙動マトリクス

### `FLEX_COUNTER_STATUS`

| 値 | グループ | 挙動 |
|----|---------|------|
| `enable` | `PORT` | `m_port_counter_enabled = true` → ポート統計 COUNTER_ID_LIST を投入 |
| `enable` | `PORT_BUFFER_DROP` | `m_port_buffer_drop_counter_enabled = true` |
| `enable` | `QUEUE` | `m_queue_enabled = true` → キュー COUNTER_ID_LIST を投入 |
| `enable` | `QUEUE_WATERMARK` | `m_queue_watermark_enabled = true` |
| `enable` | `PG_DROP` | `m_pg_enabled = true` |
| `enable` | `PG_WATERMARK` | `m_pg_watermark_enabled = true` |
| `enable` | `WRED_ECN_PORT` | `m_wred_port_counter_enabled = true` |
| `enable` | `WRED_ECN_QUEUE` | `m_wred_queue_counter_enabled = true` |
| `enable` | `RIF` | `gIntfsOrch` に COUNTER_ID_LIST を渡す |
| `enable` | `BUFFER_POOL_WATERMARK` | `gBufferOrch` に通知 |
| `enable` | `TUNNEL` | `vxlan_tunnel_orch` に通知 |
| `enable` | `FLOW_CNT_ROUTE` | `m_route_flow_counter_enabled = true` |
| `disable` | 全グループ | 対応カウンタを停止。`FLOW_CNT_ROUTE` は `m_route_flow_counter_enabled = false` |
| 未設定 | 全グループ | デフォルト `disable`（"counters are disabled for polling by default"） |

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp -->

| 条件 | 挙動 |
|------|------|
| `BUFFER_QUEUE` / `BUFFER_PG` key 形式不正 | `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]")` → エントリスキップ |
| queue / PG インデックスが非整数 | `std::invalid_argument` をキャッチし `SWSS_LOG_ERROR` → そのポートのカウンタ設定は適用されない |
| `FLEX_COUNTER_STATUS` 未設定 | デフォルト `disable`。エントリがなければカウンタ収集は行われない |
| `create_only_config_db_buffers` フラグ読み取りエラー | `SWSS_LOG_ERROR` → バッファカウンタ関連設定がデフォルト動作になる可能性 |
| `POLL_INTERVAL` の極端な短縮 | コード上バリデーションなし。100ms 等ではカウンタ集計で orchagent / syncd CPU が貼り付くリスク |

<!-- /cdb-exceptions -->

<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

`FlexCounterOrch` (orchagent 直接 CFG 購読) が CONFIG_DB の `FLEX_COUNTER_TABLE` テーブルを購読する。

`FLEX_COUNTER_TABLE` の key はグループ名 (例: `PORT`, `QUEUE`, `TUNNEL`)。各グループの polling interval と状態を管理。

### 段階 2 — CFG→APPL 翻訳

なし (orchagent が直接 CONFIG_DB を購読)

### 段階 3 — APPL→SAI

`sai_counter_api` — SAI flexible counter グループの polling interval / enable を設定

### 段階 4 — タイミングと副作用

**適用タイミング**: orchagent が CONFIG_DB 変化を検知後即座に SAI counter group を更新。`POLL_INTERVAL` 変更は次回 polling から有効。

**副作用**: counter polling の有効/無効化は `COUNTERS_DB` の更新頻度に影響。`FLEX_COUNTER_STATUS` を `enable` にすると対応する SAI カウンタが増分し始める。
<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

対象テーブル: `FLEX_COUNTER_TABLE`

### CLI
- `config flex-counter enable/disable <group>`
- `config flex-counter interval <group> <msec>`
  - ソース: `sonic-utilities/config/main.py (flex-counter グループ)`

### minigraph / sonic-cfggen
- あり: `sonic-cfggen -m <minigraph.xml>` 実行時に本テーブルが生成・上書きされる

### REST / gNMI (sonic-mgmt-common)
- なし (対応 OpenConfig/[SONiC](../../reference/glossary.md#term-sonic) YANG transformer なし)

### db_migrator
- なし

### ビルド時デフォルト (init_cfg / j2 テンプレート)
- `init_cfg.json.j2` に `FLEX_COUNTER_TABLE` デフォルト (各グループの `FLEX_COUNTER_STATUS: enable`) が定義。minigraph 生成時は mgmt 系グループが `disable` に変更

### ハードコードデフォルト
- なし

### ランタイム注入 (デーモン自動書き込み)
- なし
<!-- /entry-points -->

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp, sonic-swss/orchagent/flexcounterorch.h,
     sonic-buildimage/files/build_templates/init_cfg.json.j2,
     sonic-buildimage/src/sonic-config-engine/minigraph.py,
     sonic-buildimage/dockers/docker-orchagent/enable_counters.py,
     sonic-utilities/counterpoll/main.py,
     sonic-utilities/scripts/db_migrator.py,
     sonic-buildimage/src/sonic-yang-models/yang-models/sonic-flex_counter.yang -->

### `FLEX_COUNTER_STATUS` の暗黙デフォルト

YANG に `default` 宣言なし。orchagent コメント「counters are disabled for polling by default」(flexcounterorch.cpp:227)。未設定時のデフォルトは **`disable`**（カウンタ収集ゼロ）。

**init_cfg.json.j2 で `enable` が書き込まれるグループ**（ビルド時デフォルト）:

| グループ | init_cfg STATUS | init_cfg POLL_INTERVAL |
|---------|----------------|----------------------|
| `ACL` | `enable` | `10000` ms（唯一明示） |
| `PORT` | `enable` | なし（syncd 側 fallback） |
| `PORT_PHY_ATTR` | `enable` | なし |
| `RIF` | `enable` | なし |
| `QUEUE` | `enable` | なし |
| `PFCWD` | `enable` | なし |
| `PG_WATERMARK` | `enable` | なし |
| `PG_DROP` | `enable` | なし |
| `QUEUE_WATERMARK` | `enable` | なし |
| `BUFFER_POOL_WATERMARK` | `enable` | なし |
| `PORT_BUFFER_DROP` | `enable` | なし |

**minigraph 経由 (`BmcMgmtToRRouter` / `MgmtToRRouter` / `MgmtTsToR`) で `disable` に上書き**:
`BUFFER_POOL_WATERMARK`, `PFCWD`, `PG_DROP`, `PG_WATERMARK`, `PORT_BUFFER_DROP`, `QUEUE`, `QUEUE_WATERMARK`

**[DPU](../../reference/glossary.md#term-dpu) (`switch_type == dpu`) でのみ** enable_counters.py が起動後に注入（エントリが空の場合のみ）:
`ENI`, `DASH_METER`

#### 特殊挙動・罠

| 種類 | 内容 |
|------|------|
| dead consumer (プラットフォーム依存) | `FLOW_CNT_ROUTE` は `getRouteFlowCounterSupported()` が false（SAI 未対応 [ASIC](../../reference/glossary.md#term-asic)）の場合、`enable` を書いても SAI 設定ゼロ・エラー通知なし |
| 経路依存連動 | `PORT_PHY_ATTR` を enable にすると `PORT_PHY_SERDES_ATTR` も **自動で連動** enable/disable される。CONFIG_DB に `PORT_PHY_SERDES_ATTR` キーを直接書く必要はなく、書いても orchagent は `PORT_PHY_ATTR` の値で上書く |
| 書込み順依存 | `allPortsReady()` が false の間は `doTask` が早期 return → `enable` エントリが m_toSync に蓄積され、全ポート ready 後に一括適用 |
| warm-reboot 遅延 | warm-reboot 時のみ: delay timer 60 秒間は全 SET が無視される (`m_delayTimerExpired = false`)。通常起動では即時適用 |
| FLOW_CNT_TRAP 前提条件 | `gCoppOrch` が null の場合 `generateHostIfTrapCounterIdList()` が呼ばれず、enable を書いても silent drop |
| 大文字小文字制約 | `enable`/`disable` のみ有効。その他の値は `SWSS_LOG_NOTICE("Unsupported field")` でスキップ |

### `FLEX_COUNTER_DELAY_STATUS` の暗黙デフォルト

YANG に `default` なし。未設定時は遅延なし（即時ポーリング開始）。

| 種類 | 内容 |
|------|------|
| 暗黙 reset (fast-reboot) | db_migrator `migrate_config_db_flex_counter_delay_status`: fast-reboot 前に全エントリの値を `true` に強制上書き |
| 暗黙削除 (version migration) | db_migrator `migrate_flex_counter_delay_status_removal`: cross-branch upgrade 時にフィールドを完全削除する migration が走る。フィールドの有無がバージョンに依存 |
| dead field (通常起動) | 通常起動では `m_delayTimerExpired = true`（コンストラクタで即セット）。`FLEX_COUNTER_DELAY_STATUS` は orchagent から参照されない（syncd 側での参照のみ）。通常は書き込み不要 |

### `POLL_INTERVAL` の暗黙デフォルト

YANG に `default` なし。counterpoll CLI の表示上のソフトデフォルト（orchagent / syncd にはハードコードなし）:

| グループ | CLI ソフトデフォルト | CLI 入力可能範囲 |
|---------|-------------------|----------------|
| `PORT` / `RIF` / `WRED_ECN_PORT` | 1000 ms | 100..30000 |
| `QUEUE` / `PG_DROP` / `ACL` / `TUNNEL` / `FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` / `WRED_ECN_QUEUE` / `SRV6` / `ENI` / `HA_SET` | 10000 ms | 1000..30000 |
| `BUFFER_POOL_WATERMARK` / `QUEUE_WATERMARK` / `PG_WATERMARK` / `SWITCH` | 60000 ms | 1000..60000 |
| `PORT_BUFFER_DROP` | 60000 ms | **30000..300000** (CPU 負荷大のため下限 30s) |
| `PORT_PHY_ATTR` | 10000 ms | 100..30000 |

**YANG vs CLI 乖離**: YANG の `poll_interval` typedef は `range 100..4294967295` で統一。CLI は group ごとに異なる上限を `IntRange` で強制しており、YANG バリデーションだけでは CLI の下限・上限が守られない。

### `BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX` の暗黙デフォルト

| 種類 | 内容 |
|------|------|
| 未設定時 fallback | 未設定時、orchagent は syncd へ `"NULL"` 文字列を送信 → syncd 側で chunk size 無限（上限なし）として扱われる |
| silent substitution | 片フィールドのみ設定した場合、もう片方は `"NULL"` で自動補完される（flexcounterorch.cpp:405）。ユーザーへの通知なし |
| 暗黙リセット | 両フィールドを同時に省略した UPDATE を送ると `m_groupsWithBulkChunkSize` から erase → `"NULL","NULL"` を送信してリセット |
| YANG 定義グループのみ | `BULK_CHUNK_SIZE` を YANG で定義するのは `PORT`, `PORT_BUFFER_DROP`, `QUEUE`, `QUEUE_WATERMARK`, `PG_DROP`, `PG_WATERMARK` のみ。他グループ (`DEBUG_COUNTER`, `PFCWD`, `RIF` 等) は YANG にも orchagent にも定義なし（書いても Unsupported field として無視） |

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp, sonic-swss/orchagent/orchdaemon.cpp -->

### orchdaemon 初期化順序

`FlexCounterOrch` は依存する全 Orch が生成済みの後に生成される（`orchdaemon.cpp:625`）。依存 Orch の生成順の抜粋:

| 順番 | オブジェクト | 役割 |
|------|------------|------|
| 1 | `gPortsOrch` | 物理ポート管理 |
| 2 | `gFlowCounterRouteOrch` | ルートフローカウンタ |
| 3 | `gIntfsOrch` | インタフェース/[RIF](../../reference/glossary.md#term-rif) 管理 |
| 4 | `gCoppOrch` | COPP/Trap 管理 |
| 5 | `gBufferOrch` | バッファプール/キュー管理 |
| 6 | `FlexCounterOrch` (本 Orch) | flex counter グループ制御 |

### doTask ガード順序

`FlexCounterOrch::doTask(Consumer &consumer)` の早期 return ガード（順番どおり）:

1. テーブルが `DEVICE_METADATA` なら `handleDeviceMetadataTable()` に委譲して即 return
2. `!m_delayTimerExpired` (warm-reboot 遅延 60 秒) の間は全処理を保留
3. `gPortsOrch->allPortsReady() == false` の間は全処理を保留（ポート初期化待ち）
4. `gFabricPortsOrch->allPortsReady() == false` の間は全処理を保留（Fabric ポート初期化待ち）
5. `flexCounterGroupMap` に存在しないキーは即破棄（`SWSS_LOG_NOTICE("Invalid flex counter group input")` → リトライなし）

### グループ別 enable 前提条件

`FLEX_COUNTER_STATUS=enable` の書込みは、対応 Orch が初期化完了していなければ silent drop（ガード無しで null ポインタ deref を避けるため）:

| グループ | 前提条件 |
|---------|---------|
| `PORT` / `PORT_BUFFER_DROP` / `QUEUE` / `QUEUE_WATERMARK` / `PG_DROP` / `PG_WATERMARK` / `WRED_ECN_PORT` / `WRED_ECN_QUEUE` / `PORT_PHY_ATTR` | `gPortsOrch` 非 NULL かつ `allPortsReady()` |
| `QUEUE` / `QUEUE_WATERMARK` / `PG_DROP` / `PG_WATERMARK` (`create_only_config_db_buffers=true` のみ) | `gBufferOrch` に BUFFER_QUEUE/[BUFFER_PG](../../reference/glossary.md#term-buffer-pg) の非ゼロ profile エントリが存在 |
| `RIF` | `gIntfsOrch` 非 NULL |
| `BUFFER_POOL_WATERMARK` | `gBufferOrch` 非 NULL |
| `TUNNEL` | `VxlanTunnelOrch` が `gDirectory` 登録済み |
| `ENI` / `DASH_METER` | `DashOrch` が `gDirectory` 登録済み |
| `HA_SET` | `DashHaOrch` が `gDirectory` 登録済み |
| `FLOW_CNT_TRAP` | `gCoppOrch` 非 NULL |
| `FLOW_CNT_ROUTE` | `gFlowCounterRouteOrch` 非 NULL かつ SAI 能力クエリで `set_implemented == true` |
| `SRV6` | `gSrv6Orch` 非 NULL |
| `SWITCH` | `gSwitchOrch` 非 NULL |

### 同一 SET 内のフィールド処理順

複数フィールドを 1 つの SET コマンドにまとめて送ると、ループ内で以下の順で適用される:

```
POLL_INTERVAL       → setFlexCounterGroupPollInterval()  (即時)
BULK_CHUNK_SIZE     → 変数に保管（ループ後にまとめて適用）
FLEX_COUNTER_STATUS → enable/disable アクション + setFlexCounterGroupOperation()
```

`POLL_INTERVAL` と `FLEX_COUNTER_STATUS` を同一 SET にまとめると、`POLL_INTERVAL` が必ず先に適用される。

### disable 時の非対称性

多くのグループは `disable` 時に [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) の per-OID エントリを削除しない（syncd がポーリングを止めるだけ）。例外として以下は明示削除を行う:

| グループ | disable 時のアクション |
|---------|---------------------|
| `FLOW_CNT_TRAP` | `gCoppOrch->clearHostIfTrapCounterIdList()` |
| `FLOW_CNT_ROUTE` | `gFlowCounterRouteOrch->clearRouteFlowStats()` |
| `PORT_PHY_ATTR` | `gPortsOrch->clearPortPhyAttrCounterMap()` + `clearPortPhySerdesAttrCounterMap()` |

### warm-reboot: bake() は意図的 no-op

`FlexCounterOrch::bake()` は `return true` のみ。`FLEX_COUNTER_TABLE` はデータプレーン整合性に不要なため reconciling 処理を行わない。60 秒の遅延タイマー満了後に通常通り SET を処理する。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp, sonic-swss/orchagent/orchdaemon.cpp,
     sonic-swss/orchagent/saihelper.cpp, sonic-swss/orchagent/portsorch.cpp;
     詳細調査: meta/_intermediate/cdb-flow/flex-counter-table-cross-refs.md -->

`FlexCounterOrch` が `FLEX_COUNTER_TABLE` を処理する際に暗黙的に参照・書き込む他テーブルを示す。YANG leafref として明示されない依存も含む。

| 参照先テーブル | DB | 方向 | 条件 | evidence |
|--------------|-----|------|------|---------|
| `DEVICE_METADATA\|localhost` (`create_only_config_db_buffers`) | CONFIG_DB | 読み（起動時 + 購読） | 常時。`create_only_config_db_buffers` フラグを取得し QUEUE/PG カウンタ対象を決定 | `flexcounterorch.cpp:107-124,488-537`; `orchdaemon.cpp:622` |
| `BUFFER_QUEUE` | [APPL_DB](../../reference/glossary.md#term-appl_db) | 読み（QUEUE/PG enable 時） | `create_only_config_db_buffers=true` かつ非 VOQ シャーシ。非ゼロ profile のエントリのみをカウンタ対象に登録 | `flexcounterorch.cpp:544-620` |
| `BUFFER_PG` | [APPL_DB](../../reference/glossary.md#term-appl_db) | 読み（PG enable 時） | `create_only_config_db_buffers=true`。非ゼロ profile の PG エントリのみを対象に | `flexcounterorch.cpp:623-670` |
| `FLEX_COUNTER_GROUP_TABLE\|<group>` | FLEX_COUNTER_DB | 書き | STATUS/INTERVAL/BULK_CHUNK_SIZE 変化のたびに更新。`gTraditionalFlexCounter=true` 時は ProducerTable 直接書込、`false` 時は SAI [Redis](../../reference/glossary.md#term-redis) 属性経由 | `saihelper.cpp:884` |
| `FLEX_COUNTER_TABLE\|<group>:<oid>` | FLEX_COUNTER_DB | 書き (enable) / 削除 (disable) | 初回 enable 後の `generateXxxMap()` が per-OID エントリ (`PORT_COUNTER_ID_LIST` 等) を書込。disable / オブジェクト削除時に DEL | `saihelper.cpp:1047,1075` |
| `COUNTERS_PORT_NAME_MAP` 等 | [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | 書き | `generatePortCounterMap()` / `generateQueueMap()` / `generatePriorityGroupMap()` が初回 enable 時に名前→SAI OID マッピングを書込。counterpoll / テレメトリが参照する | `portsorch.cpp:9102` |

!!! note "BUFFER_QUEUE / BUFFER_PG 参照の VOQ 例外"
    `gMySwitchType == "voq"` の VOQ シャーシでは `getQueueConfigurations()` が BUFFER_QUEUE を参照せず全ポート・全キューを一括登録する (`flexcounterorch.cpp:549`)。非 VOQ かつ `create_only_config_db_buffers=false` の場合も同様に全キュー対象となり BUFFER_QUEUE 参照は行われない。

!!! note "DEVICE_METADATA の二重参照"
    `FlexCounterOrch` は起動時に CONFIG_DB から `DEVICE_METADATA|localhost` をスナップショット読み込みし、さらに実行時購読も設定する。minigraph 適用等で `create_only_config_db_buffers` が変化すると `handleDeviceMetadataTable()` が `m_createOnlyConfigDbBuffers` を動的に更新する。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp -->

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 |
|---|---|---|---|
| `key` が未定義グループ名 | `doTask()` L183-188 | エントリをスキップ（設定未適用） | `SWSS_LOG_NOTICE("Invalid flex counter group input, %s")` |
| `FLEX_COUNTER_STATUS` に `enable`/`disable` 以外の値 | `doTask()` L235-393 | 各 orch ブロックすべてが silent skip。`setFlexCounterGroupOperation()` には不正値が渡る | なし（ログ未出力） |
| `POLL_INTERVAL` に非数値・YANG 範囲外の値を直接書き込み | `setFlexCounterGroupPollInterval()` | orchagent 側バリデーションなし。値をそのまま syncd に渡す。拒否はプラットフォーム依存 | なし |
| `gPortsOrch == nullptr` で PORT / QUEUE / PG / [WRED](../../reference/glossary.md#term-wred) 系を `enable` | `doTask()` L235 | `gPortsOrch` null チェックで全ブロックをスキップ → SAI カウンタ設定ゼロ | なし（silent drop） |
| `gCoppOrch == nullptr` で `FLOW_CNT_TRAP` を `enable` | `doTask()` L311 | `generateHostIfTrapCounterIdList()` 呼び出しスキップ → trap flow counter 未設定 | なし（silent drop） |
| `gFlowCounterRouteOrch` null または `getRouteFlowCounterSupported() == false` で `FLOW_CNT_ROUTE` を `enable` | `doTask()` L324 | ルートフローカウンタ設定ゼロ・`m_route_flow_counter_enabled` 更新なし | なし（silent drop） |
| `allPortsReady() == false` の間に SET | `doTask()` 早期 return | エントリが `m_toSync` に蓄積。全ポート ready 後に一括処理 | なし |
| warm-reboot 中（delay timer 60s 未満）に SET | delay guard | `m_delayTimerExpired == false` の間は全 SET が無視される | なし |
| `create_only_config_db_buffers` 読み取りで `std::system_error` | コンストラクタ L122-124 | `m_createOnlyConfigDbBuffers` がデフォルト (`false`) のまま → バッファカウンタ設定が変わる可能性 | `SWSS_LOG_ERROR("System error reading create_only_config_db_buffers: %s")` |
| `BUFFER_QUEUE` key がトークン数 ≠ 2 | `getQueueConfigurations()` L559-562 | エントリスキップ（カウンタ未適用） | `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]")` |
| queue / PG インデックスが非整数または範囲外 | `getQueueConfigurations()` L599-601 / `getPgConfigurations()` L661-663 | `std::invalid_argument` キャッチ → そのポートのカウンタ設定をスキップ | `SWSS_LOG_ERROR("Invalid queue/pg index ...")` |
| `BUFFER_PG` key がトークン数 ≠ 2 | `getPgConfigurations()` L628-631 | エントリスキップ | `SWSS_LOG_ERROR("Invalid BUFFER_PG key: [%s]")` |

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp, sonic-utilities/counterpoll/main.py -->

### warm-reboot 遅延定数

| 定数 | 値 | 用途 |
|------|----|------|
| `FLEX_COUNTER_DELAY_SEC` | `60` 秒 | warm-reboot 時のみ使用。`SelectableTimer` をこの秒数で起動し、期間中は全 SET を無視する (`m_delayTimerExpired = false`)。通常起動では即 `true` にセットされ不使用 |

### FLEX_COUNTER_STATUS enum 値

| 値 | 意味 |
|----|------|
| `"enable"` | カウンタポーリング有効化。各グループフラグ (`m_port_counter_enabled` 等) を `true` にセットし COUNTER_ID_LIST を syncd へ投入 |
| `"disable"` | カウンタポーリング停止。フラグを `false` にリセット |

`ENABLE = "enable"`, `DISABLE = "disable"` は counterpoll/main.py L15-16 でも定義。上記 2 値以外は `SWSS_LOG_NOTICE("Unsupported field")` でスキップ。

### POLL_INTERVAL CLI ソフトデフォルト

YANG に `default` 宣言なし。orchagent / syncd にもハードコードなし。counterpoll CLI の `show` が CONFIG_DB 未設定時に表示するソフトデフォルト値:

| 定数 | 値 | 対象グループ |
|------|----|------------|
| `DEFLT_1_SEC` | `1000` ms | `PORT`, `RIF`, `WRED_ECN_PORT` |
| `DEFLT_10_SEC` | `10000` ms | `QUEUE`, `PG_DROP`, `ACL`, `TUNNEL`, `FLOW_CNT_TRAP`, `FLOW_CNT_ROUTE`, `WRED_ECN_QUEUE`, `SRV6`, `ENI`, `HA_SET`, `PORT_PHY_ATTR` |
| `DEFLT_60_SEC` | `60000` ms | `BUFFER_POOL_WATERMARK`, `QUEUE_WATERMARK`, `PG_WATERMARK`, `SWITCH`, `PORT_BUFFER_DROP` |

### POLL_INTERVAL CLI 入力範囲制約

| グループ | 下限 (ms) | 上限 (ms) |
|---------|----------|----------|
| `PORT`, `RIF`, `QUEUE`, `PG_DROP`, `ACL`, `TUNNEL`, `FLOW_CNT_TRAP`, `FLOW_CNT_ROUTE`, `WRED_ECN_QUEUE`, `SRV6`, `ENI`, `HA_SET` | 100〜1000 | 30000 |
| `PORT_PHY_ATTR` | 100 | 30000 |
| `WATERMARK` 系 (`QUEUE_WATERMARK`, `PG_WATERMARK`, `BUFFER_POOL_WATERMARK`), `SWITCH` | 1000 | 60000 |
| `PORT_BUFFER_DROP` | **30000** (CPU 負荷大のため) | **300000** |

> YANG `poll_interval` typedef は `range 100..4294967295` で全グループ統一。CLI が group ごとに `IntRange` で上限を強制しており、YANG バリデーションだけでは CLI 制約が守られない。
<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: sonic-swss/orchagent/flexcounterorch.cpp, sonic-swss/orchagent/saihelper.cpp,
     sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp, sonic-swss/orchagent/portsorch.cpp -->

`FLEX_COUNTER_TABLE` への書込は `FlexCounterOrch` を通じて 2 つの副次 DB に波及する。

### FLEX_COUNTER_DB への書込

`setFlexCounterGroupOperation()` → `operateFlexCounterGroupDatabase()` が `FLEX_COUNTER_GROUP_TABLE` に書込む（`gTraditionalFlexCounter=true` モード）。`gTraditionalFlexCounter=false` 時は SAI [Redis](../../reference/glossary.md#term-redis) 属性 `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` 経由で syncd に通知する。

| テーブル | キーパターン | フィールド | トリガ |
|---------|------------|---------|-------|
| `FLEX_COUNTER_GROUP_TABLE` | `<group>` (例: `PORT`) | `FLEX_COUNTER_STATUS`, `POLL_INTERVAL`, `BULK_CHUNK_SIZE`, `BULK_CHUNK_SIZE_PER_PREFIX` | CONFIG_DB の当該フィールド変化時 (`saihelper.cpp:884`) |
| `FLEX_COUNTER_TABLE` | `<group>:<oid>` (例: `PORT:0x1000000000023`) | `PORT_COUNTER_ID_LIST`, `QUEUE_COUNTER_ID_LIST`, `STATS_MODE` 等 | `FLEX_COUNTER_STATUS=enable` 受信後 `generateXxxMap()` 内で `startFlexCounterPolling()` が書込 (`saihelper.cpp:1047`) |
| `FLEX_COUNTER_TABLE` | `<group>:<oid>` | (全削除) | disable 時 / オブジェクト削除時 `stopFlexCounterPolling()` (`saihelper.cpp:1075`) |

Gearbox 有効時は `PORT` / `MACSEC*` グループに対して `GB_FLEX_COUNTER_DB` 側にも同様の書込が発生する (`flexcounterorch.cpp:386`)。

`PORT_PHY_ATTR` グループの enable/disable は `PORT_PHY_SERDES_ATTR` グループへも自動で連動書込される (`flexcounterorch.cpp:392`)。

### COUNTERS_DB への書込

`FLEX_COUNTER_STATUS=enable` 受信後に呼ばれる `generatePortCounterMap()` 等が `PortsOrch` 内の各 `CounterNameMapUpdater` / `Table` オブジェクトを通じてポート・キュー・PG の名前→OID マッピングを書込む。

| テーブル | キーパターン | 内容 | トリガグループ |
|---------|------------|------|--------------|
| `COUNTERS_PORT_NAME_MAP` | `""` (hash: port_name → OID) | 物理ポート名→SAI OID | `PORT` enable (`portsorch.cpp:9102`) |
| `COUNTERS_QUEUE_NAME_MAP` | `""` (hash: `Ethernet0:0` → OID) | キュー名→SAI OID | `QUEUE` / `QUEUE_WATERMARK` enable (`portsorch.cpp:778`) |
| `COUNTERS_PG_NAME_MAP` | `""` (hash: `Ethernet0:0` → OID) | PG 名→SAI OID | `PG_DROP` / `PG_WATERMARK` enable (`portsorch.cpp:785`) |
| `COUNTERS_QUEUE_PORT_MAP` | `""` (hash: queue_OID → port_OID) | キュー→ポート逆引き | キュー追加時 |
| `COUNTERS_QUEUE_INDEX_MAP` | `""` (hash: queue_OID → index) | キュー→インデックス | キュー追加時 |
| `COUNTERS_QUEUE_TYPE_MAP` | `""` (hash: queue_OID → ucast/mcast) | キューのタイプ | キュー追加時 |
| `COUNTERS_PG_PORT_MAP` | `""` (hash: pg_OID → port_OID) | PG→ポート逆引き | PG 追加時 |
| `COUNTERS_PG_INDEX_MAP` | `""` (hash: pg_OID → index) | PG→インデックス | PG 追加時 |
| `COUNTERS_LAG_NAME_MAP` | `""` (hash: lag_name → OID) | [LAG](../../reference/glossary.md#term-lag) 名→OID | [LAG](../../reference/glossary.md#term-lag) ポート追加時 |

これらのマッピングテーブルが存在することで、syncd が SAI bulk counter API で取得したカウンタ値を `COUNTERS_DB` の `COUNTERS:<oid>` キーに書込み、`counterpoll show` / テレメトリ系サービスから名前ベースで参照できる。

<!-- /side-effects -->

<!-- platform -->
## プラットフォーム / SAI Capability 差異 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/flex-counter-table-platform.md -->

### VOQ シャーシ — キューカウンタの全ポート一括登録

`gMySwitchType == "voq"` の場合、`getQueueConfigurations()` は `BUFFER_QUEUE` 設定を無視し、全フロントパネルポートおよびシステムポートの egress / VOQ キューを `createAllAvailableBuffersStr` で一括登録する。非 VOQ 環境では `create_only_config_db_buffers` フラグに従って `BUFFER_QUEUE` の非ゼロ profile エントリのみを対象とする。

```
flexcounterorch.cpp:getQueueConfigurations()
  if (!isCreateOnlyConfigDbBuffers() || gMySwitchType == "voq")
    → 全キューを一括登録して即 return   // VOQ chassis fast path
  else
    → BUFFER_QUEUE テーブルから profile 付きエントリのみ列挙
```

| モード | QUEUE カウンタ登録対象 |
|--------|----------------------|
| 非 [VOQ](../../reference/glossary.md#term-voq) (`create_only_config_db_buffers=false`) | 全ポート / 全キュー |
| 非 [VOQ](../../reference/glossary.md#term-voq) (`create_only_config_db_buffers=true`) | `BUFFER_QUEUE` の非ゼロ profile エントリのみ |
| [VOQ](../../reference/glossary.md#term-voq) シャーシ | `create_only_config_db_buffers` 設定によらず全キューを一括登録 |

---

### SAI Capability — FLOW_CNT_ROUTE の有効化条件

`FLOW_CNT_ROUTE` グループへの `FLEX_COUNTER_STATUS=enable` 設定は、[SAI](../../reference/glossary.md#term-sai) が `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` の set 操作をサポートしている場合のみ有効となる。起動時に `sai_query_attribute_capability()` を呼び出し、`capability.set_implemented` が `false` またはクエリ失敗の [ASIC](../../reference/glossary.md#term-asic) では `FLOW_CNT_ROUTE` の enable は無操作になる。

```
flow_counter_handler.cpp:queryRouteFlowCounterCapability()
  sai_query_attribute_capability(SAI_OBJECT_TYPE_ROUTE_ENTRY,
                                 SAI_ROUTE_ENTRY_ATTR_COUNTER_ID)
  → capability.set_implemented == false  ⇒  FLOW_CNT_ROUTE 無効
```

---

### DASH / SmartSwitch (DPU) — ENI / DASH_METER / HA_SET グループ

`ENI`・`DASH_METER`・`HA_SET` グループの `FLEX_COUNTER_STATUS` 変更は、[DASH](../../reference/glossary.md#term-dash) 対応 [DPU](../../reference/glossary.md#term-dpu) OrchDaemon でのみ有効となる。通常 [NPU](../../reference/glossary.md#term-npu) 環境では `gDirectory.get<DashOrch*>()` が `nullptr` を返すため、これらグループへの enable/disable は無操作となる。

| プラットフォーム | [ENI](../../reference/glossary.md#term-eni) / DASH_METER / HA_SET 動作 |
|-----------------|-------------------------------|
| [DPU](../../reference/glossary.md#term-dpu) ([SmartSwitch](../../reference/glossary.md#term-smartswitch) の DPU サイド) | `DashOrch` / `DashHaOrch` が有効。enable/disable が Dash ハンドラに通知される |
| 通常 [NPU](../../reference/glossary.md#term-npu) / 非 [SmartSwitch](../../reference/glossary.md#term-smartswitch) | `dash_orch == nullptr` のため無操作 |

---

### Fabric シャーシ — Fabric ポートキュー統計

`gFabricPortsOrch` が有効な Fabric シャーシ構成では、`FLEX_COUNTER_STATUS=enable` 時に `gFabricPortsOrch->generateQueueStats()` が追加で呼び出される。非 Fabric 構成では `gFabricPortsOrch == nullptr` のためこのコールは skip される。

<!-- /platform -->

<!-- glossary-links-injected: d8d75455adfd -->
