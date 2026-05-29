---
title: COUNTERS_DB キュー / PG カウンタテーブル群
description: "COUNTERS_DB の Queue / Priority Group カウンタ関連テーブル — portsorch が orchestrate する SAI カウンタ収集、FlexCounter グループ、ウォーターマーク体系の詳細リファレンス。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.h
    ref: master
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: master
  - repo: sonic-net/sonic-sairedis
    path: syncd/FlexCounter.cpp
    ref: master
  - repo: sonic-net/sonic-utilities
    path: scripts/queuestat
    ref: master
  - repo: sonic-net/sonic-utilities
    path: scripts/pg-drop
    ref: master
  - repo: sonic-net/sonic-utilities
    path: scripts/watermarkstat
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/high_frequency_telemetry/counternameupdater.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/high_frequency_telemetry/hftelorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/countercheckorch.cpp
    ref: master
related:
  config_db:
    - FLEX_COUNTER_TABLE
    - BUFFER_QUEUE
    - BUFFER_PG
  cli:
    - queuestat
    - pg-drop
    - watermarkstat
    - counterpoll
---

# COUNTERS_DB キュー / PG カウンタテーブル群

## 概要

[SONiC](../../reference/glossary.md#term-sonic) の `portsorch`（[orchagent](../../reference/glossary.md#term-orchagent) 内）は、ポートの Queue（送信キュー）と [Priority Group](../../reference/glossary.md#term-priority-group)（優先度グループ、PG）ごとの [SAI](../../reference/glossary.md#term-sai) ハードウェアカウンタを [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に収集する[^1]。このページではカウンタ収集に使われる [Redis](../../reference/glossary.md#term-redis) テーブル群・フィールド一覧・[FlexCounter](../../reference/glossary.md#term-flexcounter) グループのコード由来デフォルトを解説する。

---

## COUNTERS_DB テーブル体系

### ベースカウンタ / マッピングテーブル

| テーブル名 | 内容 | 書き込み主体 |
|-----------|------|------------|
| `COUNTERS:<OID>` | 各 Queue / PG の [SAI](../../reference/glossary.md#term-sai) カウンタ値（field=value） | [syncd](../../reference/glossary.md#term-syncd) [FlexCounter](../../reference/glossary.md#term-flexcounter) |
| `COUNTERS_QUEUE_NAME_MAP` | `<port>:<queue_index>` → [SAI](../../reference/glossary.md#term-sai) OID のハッシュ | [portsorch](../../reference/glossary.md#term-portsorch) |
| `COUNTERS_VOQ_NAME_MAP` | VoQ 用 `<sysport>:<index>` → SAI OID | [portsorch](../../reference/glossary.md#term-portsorch)（VoQ モードのみ） |
| `COUNTERS_QUEUE_PORT_MAP` | Queue OID → ポート OID のハッシュ | [portsorch](../../reference/glossary.md#term-portsorch) |
| `COUNTERS_QUEUE_INDEX_MAP` | Queue OID → キューインデックス（0 始まり） | portsorch |
| `COUNTERS_QUEUE_TYPE_MAP` | Queue OID → `SAI_QUEUE_TYPE_UNICAST` / `SAI_QUEUE_TYPE_MULTICAST` 等 | portsorch |
| `COUNTERS_PG_NAME_MAP` | `<port>:<pg_index>` → SAI OID のハッシュ | portsorch |
| `COUNTERS_PG_PORT_MAP` | PG OID → ポート OID のハッシュ | portsorch |
| `COUNTERS_PG_INDEX_MAP` | PG OID → PG インデックス（0 始まり） | portsorch |

### ウォーターマークテーブル

| テーブルプレフィクス | 内容 |
|--------------------|------|
| `PERIODIC_WATERMARKS:<OID>` | 周期リセット型ウォーターマーク（counterpoll 周期ごとにクリア） |
| `PERSISTENT_WATERMARKS:<OID>` | 永続型ウォーターマーク（手動 clear まで保持） |
| `USER_WATERMARKS:<OID>` | ユーザクリア後からの累積（`watermarkstat -c` でリセット） |

---

## キー形式

```text
COUNTERS:<hex_oid>
COUNTERS_QUEUE_NAME_MAP  field="Ethernet0:0"  value="0x00000000000001a0"
COUNTERS_PG_NAME_MAP     field="Ethernet0:3"  value="0x00000000000001b0"
```

- Queue: `<port_alias>:<queue_index>`（例: `Ethernet0:0`）
- VoQ: `<system_port_alias>:<queue_index>`（例: `Linecard1|ASIC0|Ethernet0:0`）
- PG: `<port_alias>:<pg_index>`（例: `Ethernet0:3`）

---

## SAI カウンタフィールド一覧

### Queue 通常カウンタ（QUEUE グループ）

`FLEX_COUNTER_TABLE|QUEUE` が `enable` のときに収集。ソース: `portsorch.cpp` の `queue_stat_ids`[^2]。

| COUNTERS:<OID> フィールド | 説明 |
|--------------------------|------|
| `SAI_QUEUE_STAT_PACKETS` | 送信パケット数（合計） |
| `SAI_QUEUE_STAT_BYTES` | 送信バイト数（合計） |
| `SAI_QUEUE_STAT_DROPPED_PACKETS` | ドロップパケット数 |
| `SAI_QUEUE_STAT_DROPPED_BYTES` | ドロップバイト数 |
| `SAI_QUEUE_STAT_TRIM_PACKETS` | パケットトリミング発生数 |
| `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` | トリミング後ドロップ数 |
| `SAI_QUEUE_STAT_TX_TRIM_PACKETS` | トリミング後送信数 |

VoQ モードでは追加フィールド `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`（Credit Watchdog 削除パケット数）が加わる。

### Queue ウォーターマーク（QUEUE_WATERMARK グループ）

`FLEX_COUNTER_TABLE|QUEUE_WATERMARK` が `enable` のときに収集。`StatsMode::READ_AND_CLEAR`（ポーリングごとに SAI 側リセット）。

| フィールド | 説明 |
|---------|------|
| `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` | 共有バッファ使用量ウォーターマーク（バイト） |

### WRED/ECN Queue カウンタ（WRED_ECN_QUEUE グループ）

`FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` が `enable` かつ SAI が [WRED](../../reference/glossary.md#term-wred) ケイパビリティをサポートする場合のみ収集[^3]。

| フィールド | 説明 |
|---------|------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | [ECN](../../reference/glossary.md#term-ecn) マーキングパケット数 |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | [ECN](../../reference/glossary.md#term-ecn) マーキングバイト数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | [WRED](../../reference/glossary.md#term-wred) ドロップパケット数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | [WRED](../../reference/glossary.md#term-wred) ドロップバイト数 |

### PG ドロップカウンタ（PG_DROP グループ）

`FLEX_COUNTER_TABLE|PG_DROP` が `enable` のときに収集。`StatsMode::READ`。

| フィールド | 説明 |
|---------|------|
| `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` | イングレス PG ドロップパケット数 |

### PG ウォーターマーク（PG_WATERMARK グループ）

`FLEX_COUNTER_TABLE|PG_WATERMARK` が `enable` のときに収集。`StatsMode::READ_AND_CLEAR`。

| フィールド | 説明 |
|---------|------|
| `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES` | XOFF リザーブ使用量ウォーターマーク（バイト） |
| `SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` | 共有バッファ使用量ウォーターマーク（バイト） |

---

## FlexCounter グループとハードコードデフォルト

各グループは `portsorch.h` / `portsorch.cpp` にコード直書きの [FlexCounter](../../reference/glossary.md#term-flexcounter) グループ名とポーリング間隔を持つ[^4]。

| FlexCounter グループ名 | [CONFIG_DB](../../reference/glossary.md#term-config_db) キー | StatsMode | コードデフォルトポーリング間隔 | counterpoll CLI 上書き可否 |
|--------------------|--------------|-----------|--------------------------|--------------------------|
| `QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE` | READ | 10000 ms | 可（`counterpoll queue interval`） |
| `QUEUE_WATERMARK_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | READ_AND_CLEAR | 60000 ms | 可 |
| `PG_DROP_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|PG_DROP` | READ | 10000 ms | 可 |
| `PG_WATERMARK_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|PG_WATERMARK` | READ_AND_CLEAR | 60000 ms | 可 |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | READ | 10000 ms | 可 |

!!! warning "READ_AND_CLEAR の副作用"
    `QUEUE_WATERMARK` / `PG_WATERMARK` グループは `READ_AND_CLEAR` モードで動作する。SAI からポーリングするたびにハードウェアのウォーターマークレジスタがクリアされる。`watermarkstat` の PERIODIC / PERSISTENT / USER テーブル分岐は syncd 側の lua スクリプトが処理する。

<!-- ordering -->
## 書込み順依存・初期化タイミング

<!-- evidence: sonic-swss/orchagent/portsorch.cpp (initializeQueuesBulk, generateQueueMap,
     generateQueueMapPerPort, addQueueFlexCounters, addQueueFlexCountersPerPortPerQueueIndex,
     addPortBufferQueueCounters, createPortBufferQueueCounters),
     sonic-swss/orchagent/flexcounterorch.cpp (doTask, getQueueConfigurations,
     FlexCounterOrch constructor, handleDeviceMetadataTable) -->

### allPortsReady 前の自動ブロック

`FlexCounterOrch::doTask()` (`flexcounterorch.cpp:164-167`) は `gPortsOrch->allPortsReady()` が false の間 `return` する。`FLEX_COUNTER_TABLE|QUEUE|FLEX_COUNTER_STATUS = enable` を [orchagent](../../reference/glossary.md#term-orchagent) 起動前に [CONFIG_DB](../../reference/glossary.md#term-config_db) へ書き込んでも、`initializeQueuesBulk()` によるポート SAI OID フェッチ（`SAI_PORT_ATTR_QOS_QUEUE_LIST`）が完了するまで `generateQueueMap()` は実行されない。[COUNTERS_DB](../../reference/glossary.md#term-counters_db) へのマッピング書き込みは allPortsReady 後に自動的に一括実行される。

### Warm-reboot 60 秒遅延

Warm-reboot 時のみ `m_delayTimerExpired` フラグが false のままタイマーが起動し（`FLEX_COUNTER_DELAY_SEC = 60`、`flexcounterorch.cpp:44`）、60 秒間すべての FlexCounter 処理をブロックする。Cold boot ではこの遅延はなく即時処理される。Warm-reboot 中に `FLEX_COUNTER_TABLE|QUEUE = enable` を書き込んでも最大 60 秒間 `generateQueueMap()` が呼ばれず、[COUNTERS_DB](../../reference/glossary.md#term-counters_db) のキュー統計が更新されない期間が生じる。

### `BUFFER_QUEUE` と `FLEX_COUNTER_TABLE|QUEUE` の書込み順序

ランタイム中に `BUFFER_QUEUE` エントリが追加されると `createPortBufferQueueCounters()` (`portsorch.cpp:8700-8755`) が呼ばれ、その時点で `getQueueCountersState()` が `true` の場合のみ `addQueueFlexCountersPerPortPerQueueIndex()` が実行される。

- **BUFFER_QUEUE 先・FLEX_COUNTER_TABLE 後**: `BUFFER_QUEUE` 書込み時はカウンタ未登録（`getQueueCountersState()` が false）。後から `FLEX_COUNTER_TABLE|QUEUE = enable` を書くと `addQueueFlexCounters(getQueueConfigurations())` で非ゼロプロファイル付き BUFFER_QUEUE を対象にカウンタが一括登録される。
- **FLEX_COUNTER_TABLE 先・BUFFER_QUEUE 後**: `BUFFER_QUEUE` 書込み時に `getQueueCountersState()` が `true` のため `createPortBufferQueueCounters()` 内で即時カウンタ登録される。
- どちらの順序でも最終状態（[FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) のカウンタ登録）は同じになる。

### `m_isQueueMapGenerated` 冪等保護

`generateQueueMap()` (`portsorch.cpp:8391`) は `m_isQueueMapGenerated` フラグで保護されており、一度だけ実行される。`FLEX_COUNTER_TABLE|QUEUE` と `FLEX_COUNTER_TABLE|QUEUE_WATERMARK` を個別に `enable` にしても、2 回目の `generateQueueMap()` 呼び出しは即 `return` する。実際のマッピング生成は最初の enable 処理時のみ。Warm-reboot や [orchagent](../../reference/glossary.md#term-orchagent) 再起動後はフラグがリセットされ再実行される。

### `DEVICE_METADATA.create_only_config_db_buffers` の影響

`FlexCounterOrch` コンストラクタ起動時に `create_only_config_db_buffers` を読み込み内部キャッシュする。この値が `false`（デフォルト）または VoQ モードでは全ポートの全キューにカウンタを有効化する。`true` の場合は `BUFFER_QUEUE` 非ゼロプロファイル付きキューのみ対象。`DEVICE_METADATA` の事後変更は `handleDeviceMetadataTable()` で動的に反映されるが、`m_isQueueMapGenerated` がすでに `true` のため既登録カウンタには影響しない。既存カウンタを変更するには orchagent 再起動が必要。

### VoQ モードの例外

`gMySwitchType == "voq"` では `generateQueueMapPerPort()` が `getQueueCountersState()` を確認せずに `addQueueFlexCountersPerPortPerQueueIndex()` を直接呼ぶ。また `getQueueConfigurations()` は `createAllAvailableBuffersStr` を返して全キュー有効化する。VoQ モードでは `FLEX_COUNTER_TABLE|QUEUE = disable` / `BUFFER_QUEUE` の書込み順序に関わらずカウンタが収集され続ける。

### BUFFER_QUEUE DEL によるカウンタ停止

`BUFFER_QUEUE` エントリを DEL すると `deletePortBufferQueueCounters()` が呼ばれ、`COUNTERS_QUEUE_NAME_MAP` から該当エントリが削除されて `queue_stat_manager.clearCounterIdList()` でカウンタ登録が抹消される。この操作は `FLEX_COUNTER_TABLE|QUEUE` の状態（enable/disable）に依存しない。`FLEX_COUNTER_TABLE|QUEUE = disable` を先に行う必要はない。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル

<!-- evidence: sonic-swss/orchagent/portsorch.cpp (createPortBufferQueueCounters,
     createPortBufferPgCounters, addPortBufferQueueCounters, initializeQueuesBulk),
     sonic-swss/orchagent/flexcounterorch.cpp (getQueueConfigurations, getPgConfigurations,
     getQueueCountersState, getPgCountersState, handleDeviceMetadataTable) -->

`FlexCounterOrch` / `PortsOrch` がキュー・PG カウンタを処理する際に暗黙的に参照する他テーブルを示す。[YANG](../../reference/glossary.md#term-yang) の leafref として定義されたものはなく、コードのみで表現された依存関係である。

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---|---|---|---|---|
| `createPortBufferQueueCounters()` の FlexCounter 登録判断 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|QUEUE` | `getQueueCountersState()=true`（`FLEX_COUNTER_STATUS=enable`）のときのみ SAI カウンタを [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に登録。`false` の場合は COUNTERS_QUEUE_NAME_MAP へのマッピングのみ書込み | `portsorch.cpp:8731`, `flexcounterorch.cpp:453` |
| `createPortBufferQueueCounters()` の Watermark 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | `getQueueWatermarkCountersState()=true` の場合のみ Watermark FlexCounter を登録 | `portsorch.cpp:8736-8738` |
| `createPortBufferQueueCounters()` の WRED 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | `getWredQueueCountersState()=true` の場合のみ WRED FlexCounter を登録 | `portsorch.cpp:8741-8745` |
| `createPortBufferPgCounters()` の PG_DROP 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|PG_DROP` | `getPgCountersState()=true` の場合のみ PG ドロップカウンタを登録 | `portsorch.cpp:8925-8927` |
| `createPortBufferPgCounters()` の PG_WATERMARK 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|PG_WATERMARK` | `getPgWatermarkCountersState()=true` の場合のみ PG Watermark カウンタを登録 | `portsorch.cpp:8930-8933` |
| `getQueueConfigurations()` のキュー範囲決定 | [`BUFFER_QUEUE`](buffer-queue.md) | `BUFFER_QUEUE\|<port>:<queue_range>` | `create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つキューのみ FlexCounter 登録対象。`false`（デフォルト）または VoQ モードでは全キューを対象 | `flexcounterorch.cpp:545-554` |
| `getPgConfigurations()` の PG 範囲決定 | [`BUFFER_PG`](buffer-pg.md) | `BUFFER_PG\|<port>:<pg_range>` | `create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つ PG のみ FlexCounter 登録対象 | `flexcounterorch.cpp:620-623` |
| `getQueueConfigurations()` / `getPgConfigurations()` のモード分岐 | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` フィールド `create_only_config_db_buffers` | バッファモード切替フラグ。`true` → BUFFER_QUEUE / [BUFFER_PG](../../reference/glossary.md#term-buffer-pg) 限定。`false`（デフォルト）→ 全対象。実行時変更は `handleDeviceMetadataTable()` で反映されるが既登録カウンタは変更されない | `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:508-513` |
| `generateQueueMap()` の前提 | `PORT` | `APP_PORT_TABLE\|<port_name>` | `allPortsReady()` が false の間 `FlexCounterOrch::doTask()` は即 return。ポートの SAI OID（`port.m_queue_ids`）が確定しないと `generateQueueMap()` のループが 0 回で終わる | `portsorch.cpp:6583-6598`, `flexcounterorch.cpp:164-167` |

### 解決タイミング

- **FLEX_COUNTER_TABLE**: `FlexCounterOrch::doTask()` が即時評価。`enable` 書込み時点でカウンタ登録処理が実行される（allPortsReady 後）。
- **BUFFER_QUEUE / [BUFFER_PG](../../reference/glossary.md#term-buffer-pg)**: `getQueueConfigurations()` / `getPgConfigurations()` が呼ばれるたびに `gBufferOrch->getBufferObjectsWithNonZeroProfile()` で動的に再取得される（`create_only_config_db_buffers=true` 時のみ）。
- **[DEVICE_METADATA](../../reference/glossary.md#term-device_metadata)**: コンストラクタで 1 回読込み + `handleDeviceMetadataTable()` で動的更新。既登録カウンタへの遡及適用はなく、orchagent 再起動が必要。
- **PORT**: `allPortsReady()` による自動待機。portsorch が全ポート初期化完了後に `FlexCounterOrch` のキュー処理がアンブロックされる。
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動・retry / recovery


### retry / failure パターン概要

キュー / PG カウンタ経路における失敗は「orchagent クラッシュ」「silent スキップ（エントリ欠落）」「保留（自動再開）」の 3 パターンに分類される。

| パターン | 代表的なトリガー | 挙動 |
|---|---|---|
| **orchagent クラッシュ** | `initializeQueuesBulk()` SAI エラー、[Redis](../../reference/glossary.md#term-redis) 接続断、未対応 Queue type | 例外 throw → supervisor 再起動 |
| **silent スキップ** | 不正 BUFFER_QUEUE / [BUFFER_PG](../../reference/glossary.md#term-buffer-pg) キー形式、WRED 能力チェック失敗、`getQueueTypeAndIndex()` SAI 一時エラー | 当該エントリのみ除外、他処理は継続 |
| **保留（自動再開）** | `allPortsReady()` が false、Warm-reboot 60 秒遅延 | doTask() が即 return し m_toSync を保持、条件成立後に自動処理 |

### `initializeQueuesBulk()` — SAI エラーで orchagent クラッシュ

orchagent 起動時の `initializeQueuesBulk()` (`portsorch.cpp:6883`, `6928`) は全ポートの Queue 数・OID リストを SAI から一括取得する。SAI 呼び出しが 1 件でも失敗すると即座に例外を投げる:

```
SWSS_LOG_ERROR("Failed to get number of queues for port %s rv:%d", ...)
throw runtime_error("PortsOrch initialization failure.")
```

supervisor による orchagent 自動再起動後に再試行される。SAI ドライバ / [ASIC](../../reference/glossary.md#term-asic) 側の問題である場合、再起動ループに入る。

### `getQueueTypeAndIndex()` — SAI 一時エラーで該当 Queue をスキップ

`generateQueueMapPerPort()` から呼ばれる `getQueueTypeAndIndex()` (`portsorch.cpp:3641`) は Queue OID から type・index を取得する。SAI 失敗時は `return false` を返し、呼び出し元が当該 Queue エントリを `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_TYPE_MAP` / `COUNTERS_QUEUE_INDEX_MAP` から除外する（エラーログのみ出力、silent 欠落）。不正な Queue type が返った場合は `throw runtime_error("Got unsupported queue type")` で orchagent クラッシュ (`portsorch.cpp:3656`)。

`generateQueueMap()` は `m_isQueueMapGenerated` フラグで 1 回しか実行されないため、スキップされた Queue の recovery には orchagent 再起動が必要。

### 不正な BUFFER_QUEUE / BUFFER_PG キー形式 — silent スキップ

`getQueueConfigurations()` / `getPgConfigurations()` は `<port>:<queue_range>` 形式を期待する (`flexcounterorch.cpp:561`, `630`)。コロン区切りが 2 トークンでない場合、または queue/pg インデックスが数値でない / 範囲外の場合は `SWSS_LOG_ERROR` を出力して当該エントリをスキップする。当該 Queue / PG は [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) に登録されず、queuestat / pg-drop で列が欠落する。他エントリの処理は継続するため、全体への影響はない。

### 不正な FLEX_COUNTER_TABLE グループキー — 即削除

`FlexCounterOrch::doTask()` (`flexcounterorch.cpp:183-188`) は未知キーを受信すると `SWSS_LOG_NOTICE` を出力して即エントリ削除する。`FLEX_COUNTER_TABLE|QUEUE` のタイポ（例: `FLEX_COUNTER_TABLE|QUEUES`）は処理されず削除されるため、Queue カウンタが enable にならない。

### `allPortsReady()` が false / Warm-reboot 遅延タイマー

`FlexCounterOrch::doTask()` は以下の条件で即 `return` し、キュー・PG FlexCounter の登録処理をすべて保留する:

- `gPortsOrch->allPortsReady()` が false（`flexcounterorch.cpp:164-167`）: [portsyncd](../../reference/glossary.md#term-portsyncd) 異常終了等で PortInitDone が届かない場合、保留状態が永続する。orchagent 再起動が必要。
- Warm-reboot 時の `m_delayTimerExpired = false`（`flexcounterorch.cpp:155-158`）: `FLEX_COUNTER_DELAY_SEC = 60` 秒のタイマー満了まで全処理がブロックされる。起動後 60 秒間はキュー / PG カウンタの更新が停止する。

### WRED 能力チェック — silent 非登録

`isPortStatSupported()` (`portsorch.cpp:664-680`) が `sai_query_stats_capability` で WRED stat サポートを確認できない場合（`SAI_STATUS_SUCCESS` 以外）、`return false` を返して WRED 統計を silent に非登録にする。エラーログは出力されない。

[ASIC](../../reference/glossary.md#term-asic) が WRED/[ECN](../../reference/glossary.md#term-ecn) 統計をサポートしない環境では `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE = enable` にしても COUNTERS_DB に WRED フィールドが現れない。`counterpoll show` の STATUS が enable に見えても実カウンタは常にゼロになる。

### Redis 接続断 — orchagent クラッシュ

`queue_stat_manager.setCounterIdList()` / `pg_stat_manager.setCounterIdList()` は FLEX_COUNTER_DB への [Redis](../../reference/glossary.md#term-redis) 書き込みを行う。Redis 接続断等で `RedisReply` 例外が発生した場合は orchagent 全体がクラッシュする（明示的な catch なし）。全カウンタ収集が停止し、supervisor 再起動後に復旧する。

<!-- /failure -->

<!-- constants -->
## ハードコード定数


### FlexCounter グループ名（ソースコードハードコード）

| マクロ名 | 文字列値（FLEX_COUNTER_DB キー） | 定義ファイル |
|---------|-------------------------------|------------|
| `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_STAT_COUNTER"` | `portsorch.h:34` |
| `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_WATERMARK_STAT_COUNTER"` | `portsorch.h:35` |
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | `portsorch.h:36` |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | `portsorch.h:37` |
| `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_QUEUE_STAT_COUNTER"` | `portsorch.h:42`, `flexcounterorch.cpp:42` |

これらのグループ名は [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) から変更できない。`counterpoll show` の GROUP 列に表示される文字列と一致する。

### ポーリング間隔デフォルト値

| マクロ名 | 値 | 対象グループ | 収集モード | 定義 |
|---------|-----|------------|---------|------|
| `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | QUEUE_STAT_COUNTER | READ | `portsorch.cpp:90` |
| `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` ms | QUEUE_WATERMARK_STAT_COUNTER | READ_AND_CLEAR | `portsorch.cpp:91` |
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` ms | PG_WATERMARK_STAT_COUNTER | READ_AND_CLEAR | `portsorch.cpp:92` |
| `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | PG_DROP_STAT_COUNTER | READ | `portsorch.cpp:93` |

WRED_ECN_QUEUE グループは `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS`（10000 ms）を共用する（`portsorch.cpp:739`）。CONFIG_DB の `FLEX_COUNTER_TABLE|<GROUP>|POLL_INTERVAL` で上書き可能だが、orchagent 起動時の初期値は上記定数から設定される。`READ_AND_CLEAR` モード（QUEUE_WATERMARK / PG_WATERMARK）では、[syncd](../../reference/glossary.md#term-syncd) がポーリングするたびにハードウェアのウォーターマークレジスタがクリアされる。

### Warm-reboot 遅延定数

| マクロ名 | 値 | 用途 | 定義 |
|---------|-----|------|------|
| `FLEX_COUNTER_DELAY_SEC` | `60` 秒 | Warm-reboot 時に全 FlexCounter 処理をブロックする SelectableTimer の秒数 | `flexcounterorch.cpp:44` |

Cold boot では `m_delayTimerExpired = true` に即初期化され（`flexcounterorch.cpp:136`）、この遅延は適用されない。

### SAI カウンタ ID 静的配列

これらの配列はソースコードに固定されており、CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) から変更不可。ハードウェアが非サポートの場合は SAI が `0` を返すか `SAI_STATUS_NOT_SUPPORTED` でスキップされる。

| 配列名 | フィールド（SAI stat ID） | グループ | 定義行 |
|------|------------------------|---------|------|
| `queue_stat_ids` | `SAI_QUEUE_STAT_PACKETS`, `_BYTES`, `_DROPPED_PACKETS`, `_DROPPED_BYTES`, `_TRIM_PACKETS`, `_DROPPED_TRIM_PACKETS`, `_TX_TRIM_PACKETS` | QUEUE_STAT_COUNTER | `portsorch.cpp:389` |
| `voq_stat_ids` | `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` | QUEUE_STAT_COUNTER（VoQ 専用） | `portsorch.cpp:399` |
| `queueWatermarkStatIds` | `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` | QUEUE_WATERMARK_STAT_COUNTER | `portsorch.cpp:405` |
| `ingressPriorityGroupWatermarkStatIds` | `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES`, `_SHARED_WATERMARK_BYTES` | PG_WATERMARK_STAT_COUNTER | `portsorch.cpp:410` |
| `ingressPriorityGroupDropStatIds` | `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` | PG_DROP_STAT_COUNTER | `portsorch.cpp:416` |
| `wred_queue_stat_ids` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS`, `_MARKED_BYTES`, `_DROPPED_PACKETS`, `_DROPPED_BYTES` | WRED_ECN_QUEUE_STAT_COUNTER | `portsorch.cpp:429` |

### COUNTERS_DB テーブル名定数（`schema.h`）

| マクロ名 | 文字列値（Redis キー） | 行 |
|---------|---------------------|-----|
| `COUNTERS_QUEUE_NAME_MAP` | `"COUNTERS_QUEUE_NAME_MAP"` | 225 |
| `COUNTERS_VOQ_NAME_MAP` | `"COUNTERS_VOQ_NAME_MAP"` | 226 |
| `COUNTERS_QUEUE_PORT_MAP` | `"COUNTERS_QUEUE_PORT_MAP"` | 227 |
| `COUNTERS_QUEUE_INDEX_MAP` | `"COUNTERS_QUEUE_INDEX_MAP"` | 228 |
| `COUNTERS_QUEUE_TYPE_MAP` | `"COUNTERS_QUEUE_TYPE_MAP"` | 229 |
| `COUNTERS_PG_NAME_MAP` | `"COUNTERS_PG_NAME_MAP"` | 230 |
| `COUNTERS_PG_PORT_MAP` | `"COUNTERS_PG_PORT_MAP"` | 231 |
| `COUNTERS_PG_INDEX_MAP` | `"COUNTERS_PG_INDEX_MAP"` | 232 |
| `PERIODIC_WATERMARKS_TABLE` | `"PERIODIC_WATERMARKS"` | 268 |
| `PERSISTENT_WATERMARKS_TABLE` | `"PERSISTENT_WATERMARKS"` | 269 |
| `USER_WATERMARKS_TABLE` | `"USER_WATERMARKS"` | 270 |
| `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` | `"QUEUE_COUNTER_CAPABILITIES"` | 528 |

`PERIODIC_WATERMARKS` / `PERSISTENT_WATERMARKS` / `USER_WATERMARKS` テーブルへの振り分けは [syncd](../../reference/glossary.md#term-syncd) 側の Lua スクリプト（`watermark_stat.lua`）が処理する。`QUEUE_COUNTER_CAPABILITIES` は [STATE_DB](../../reference/glossary.md#term-state_db) に書き込まれ、WRED/ECN サポート状況を外部公開する。

<!-- /constants -->

<!-- side-effects -->
## COUNTERS_DB 書き込みの副作用


### CounterNameMapUpdater → HFTelOrch 連鎖（高周波テレメトリ有効時）

`COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` へのキー追加・削除は `CounterNameMapUpdater::setCounterNameMap()` / `delCounterNameMap()` 経由で行われる。高周波テレメトリ（HFT）機能が有効な場合（`gHFTOrch != null`）、Redis への `hset` の前に `HFTelOrch::locallyNotify()` が**同期**呼び出しされる[^5]。

```
generateQueueMap() / createPortBufferQueueCounters()
  └─ m_queueCounterNameMapUpdater->setCounterNameMap(queueVector)
       ├─ gHFTOrch->locallyNotify(msg)   # HFT 有効時のみ・同期
       │    ├─ m_counter_name_cache 更新
       │    └─ profile->tryCommitConfig()  # TAM 設定を syncd 送信
       └─ COUNTERS_DB COUNTERS_QUEUE_NAME_MAP hset
```

`HFTelOrch::SUPPORT_COUNTER_TABLES` には `COUNTERS_QUEUE_NAME_MAP` (`SAI_OBJECT_TYPE_QUEUE`) と `COUNTERS_PG_NAME_MAP` (`SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP`) が含まれるため、Queue / PG マッピング変更はすべて HFT プロファイルキャッシュに即時反映される。`locallyNotify()` は同期処理のため、呼び出しコストが大きい（アクティブな HFT プロファイルが多い）場合は portsorch メインループの遅延要因になる。HFT が無効（デフォルト）の場合この副作用は発生しない。

### CounterCheckOrch への Port 登録（MC/PFC カウンタ監視）

Queue / PG マッピング書き込み関数は COUNTERS_DB 更新と同時に `CounterCheckOrch::getInstance().addPort(port)` を呼んで当該ポートを MC フレーム監視リストに登録する[^6]。`BUFFER_QUEUE` / `BUFFER_PG` を DEL すると `CounterCheckOrch::removePort(port)` で監視リストから除外される。

`CounterCheckOrch` は 5 分間隔のタイマーで `mcCounterCheck()` と `pfcFrameCounterCheck()` を実行し、COUNTERS_DB から SAI カウンタを読み取ってロスレスキューへの Multicast フレーム到着や [PFC](../../reference/glossary.md#term-pfc) 異常を `SWSS_LOG_WARN` で報告する。**この監視は `FLEX_COUNTER_TABLE` の enable/disable 状態とは独立して動作する**（FlexCounter ポーリングではなく orchagent が直接 `sai_get_queue_stats` を呼ぶ）。

### QUEUE_WATERMARK / PG_WATERMARK の READ_AND_CLEAR 副作用

`queue_watermark_manager` と `pg_watermark_manager` は `StatsMode::READ_AND_CLEAR` で初期化される。FlexCounter がウォーターマーク統計をポーリングするたびにハードウェアのウォーターマークレジスタが自動クリアされる。この副作用は `FLEX_COUNTER_TABLE|QUEUE_WATERMARK` / `PG_WATERMARK` が enable の間は継続する。

複数の監視ツールが `watermarkstat` を同時に実行すると互いのウォーターマーク値をクリアし合う可能性がある。クリアを避けたい場合は `USER_WATERMARKS` テーブルを使用し、`watermarkstat -c` で明示的にリセットする運用とする。

### WRED 能力チェック → STATE_DB への QUEUE_COUNTER_CAPABILITIES 書き込み

`checkWredCapability()` が WRED/ECN サポートを確認した後、`QUEUE_COUNTER_CAPABILITIES` テーブルが [STATE_DB](../../reference/glossary.md#term-state_db) に書き込まれ、外部ツール・オーケストレータが WRED サポート状況を参照可能になる。[ASIC](../../reference/glossary.md#term-asic) が WRED をサポートしない場合はこのエントリが存在しない。外部ツールは `key not found` を「未サポート」として扱う必要がある。

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム


### Producer/Consumer ペア

キュー / PG カウンタ経路は複数の独立した通信メカニズムを組み合わせる。

| 区間 | 方式 | チャンネル / パターン |
|------|------|--------------------|
| CONFIG_DB → FlexCounterOrch | `SubscriberStateTable` | `__keyspace@{config_db_id}__:FLEX_COUNTER_TABLE\|*` |
| CONFIG_DB → WatermarkOrch | `SubscriberStateTable` | `__keyspace@{config_db_id}__:WATERMARK_TABLE\|*` / `FLEX_COUNTER_TABLE\|*` |
| FlexCounterOrch → syncd | FLEX_COUNTER_DB 直接書き込み | `FLEX_COUNTER_DB HSET COUNTER_ID_LIST` / `POLL_INTERVAL` |
| syncd FlexCounter → SAI | SAI API 直接呼び出し | `sai_get_queue_stats` / `sai_get_ingress_priority_group_stats` |
| syncd → COUNTERS_DB | Redis HSET | `COUNTERS:<OID>` |
| syncd Lua → COUNTERS_DB | Redis Lua スクリプト | `watermark_queue.lua` / `watermark_pg.lua`（COUNTERS → WATERMARK 転写） |
| `watermarkstat -c` → WatermarkOrch | Redis publish | `APPL_DB WATERMARK_CLEAR_REQUEST` |
| WatermarkOrch → COUNTERS_DB | Redis HSET | `PERIODIC_WATERMARKS` / `PERSISTENT_WATERMARKS` / `USER_WATERMARKS` |

### FlexCounterOrch の SubscriberStateTable 購読

`orchdaemon.cpp:620-625` にて `FlexCounterOrch` は `FLEX_COUNTER_TABLE` と `DEVICE_METADATA` の 2 テーブルを `SubscriberStateTable` で購読する。CONFIG_DB keyspace notification でエントリ変化を検出し、`FlexCounterOrch::doTask(Consumer&)` (`flexcounterorch.cpp:148`) が処理する。

`FLEX_COUNTER_STATUS = enable` が届くと、キーに応じて以下のメソッドを呼び出す（`flexcounterorch.cpp:247-281`）:

| CONFIG_DB キー | 呼び出し先 |
|----------------|-----------|
| `QUEUE` | `generateQueueMap()` + `addQueueFlexCounters()` |
| `QUEUE_WATERMARK` | `generateQueueMap()` + `addQueueWatermarkFlexCounters()` |
| `PG_DROP` | `generatePriorityGroupMap()` + `addPriorityGroupFlexCounters()` |
| `PG_WATERMARK` | `generatePriorityGroupMap()` + `addPriorityGroupWatermarkFlexCounters()` |
| `WRED_ECN_QUEUE` | `generateQueueMap()` + `addWredQueueFlexCounters()` |

未知キーは `SWSS_LOG_NOTICE` を出力して即削除される（`flexcounterorch.cpp:183-188`）。`DEVICE_METADATA` テーブルの変化は `handleDeviceMetadataTable()` へ委譲され、`create_only_config_db_buffers` フラグを動的更新する。

### WatermarkOrch の二経路通信

`orchdaemon.cpp:432-437` にて `WatermarkOrch` が `WATERMARK_TABLE` と `FLEX_COUNTER_TABLE` を購読する（`SubscriberStateTable`）。さらにコンストラクタ (`watermarkorch.cpp:35-38`) にて [APPL_DB](../../reference/glossary.md#term-appl_db) の `WATERMARK_CLEAR_REQUEST` チャンネルを `NotificationConsumer` で購読する。

**クリア要求フロー**（`watermarkstat -c` 実行時）:

```
watermarkstat -c
  └─ db.publish('APPL_DB', 'WATERMARK_CLEAR_REQUEST', '<op>:<data>')
       WatermarkOrch::doTask(NotificationConsumer&)
         op == "PERSISTENT" → PERSISTENT_WATERMARKS テーブルの該当 OID を 0 クリア
         op == "USER"       → USER_WATERMARKS テーブルの該当 OID を 0 クリア
```

`data` は `PG_HEADROOM` / `PG_SHARED` / `Q_SHARED_UNI` / `Q_SHARED_MULTI` / `Q_SHARED_ALL` のいずれかで、対象テーブルのフィールドと OID セットを決定する（`watermarkorch.cpp:184-230`）。

### Lua スクリプトによる COUNTERS → WATERMARK テーブル転写

syncd が `READ_AND_CLEAR` モードでウォーターマーク統計をポーリングするたびに `watermark_queue.lua` / `watermark_pg.lua` が Redis 内で Lua アトミック実行される:

1. `COUNTERS:<OID>` から最新のウォーターマーク値を読み取り
2. `PERIODIC_WATERMARKS:<OID>` / `PERSISTENT_WATERMARKS:<OID>` / `USER_WATERMARKS:<OID>` の現在値と max 比較
3. max 値でウォーターマークテーブルを更新

この転写処理は orchagent / WatermarkOrch の介在なしに syncd 内で完結する。

### 周期クリアタイマー

`WatermarkOrch` は `SelectableTimer`（デフォルト 120 秒、`DEFAULT_TELEMETRY_INTERVAL`、`watermarkorch.cpp:9`）を持ち、タイマー満了時に `PERIODIC_WATERMARKS` テーブルの全 Queue / PG ウォーターマークを 0 クリアする（`watermarkorch.cpp:233-281`）。インターバルは `WATERMARK_TABLE|TELEMETRY_INTERVAL` で変更可能。

### データフロー図

```
CONFIG_DB[FLEX_COUNTER_TABLE|QUEUE|FLEX_COUNTER_STATUS=enable]
  ↓ SubscriberStateTable (keyspace notification)
FlexCounterOrch::doTask()
  ↓ [m_delayTimerExpired チェック]
  ↓ [gPortsOrch->allPortsReady() チェック]
  ↓ generateQueueMap() → COUNTERS_DB COUNTERS_QUEUE_NAME_MAP / COUNTERS_QUEUE_TYPE_MAP 等
  ↓ addQueueFlexCounters()
    ↓ queue_stat_manager.setCounterIdList()
      → FLEX_COUNTER_DB[QUEUE_STAT_COUNTER|<OID>|COUNTER_ID_LIST]

syncd FlexCounter (polling thread, 10000 ms)
  ↓ sai_get_queue_stats(<OID>, queue_stat_ids)
  ↓ COUNTERS_DB HSET COUNTERS:<OID> SAI_QUEUE_STAT_PACKETS ...
  ↓ watermark_queue.lua (READ_AND_CLEAR ポーリング時)
    ↓ PERIODIC_WATERMARKS:<OID> / PERSISTENT_WATERMARKS:<OID> / USER_WATERMARKS:<OID> 更新

watermarkstat -c (ユーザー操作)
  ↓ db.publish('APPL_DB', 'WATERMARK_CLEAR_REQUEST', 'USER:Q_SHARED_UNI')
WatermarkOrch::doTask(NotificationConsumer&)
  ↓ USER_WATERMARKS:<OID> SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES → 0

WatermarkOrch SelectableTimer (120 秒)
  ↓ PERIODIC_WATERMARKS 全 Queue / PG OID → 0 クリア

CLI: queuestat / watermarkstat / pg-drop
  └─ COUNTERS_DB 直接読み取り（pub/sub なし）
```

> **Evidence**: `orchdaemon.cpp:432-437,620-625`; `flexcounterorch.cpp:100-167,183-281`; `watermarkorch.cpp:23-45,144-231,233-281`; `watermarkstat:325`; `watermark_queue.lua`, `watermark_pg.lua`
<!-- /pubsub -->

<!-- platform -->
## プラットフォーム固有挙動


キュー / PG カウンタの収集挙動はプラットフォーム（`platform` 環境変数）およびスイッチタイプ（`gMySwitchType`）によって以下の点が異なる。

### DPU モード — キュー / PG 初期化を完全スキップ

`gMySwitchType == "dpu"` の場合、`initializePorts()` (`portsorch.cpp:6589`) は `initializeQueuesBulk()` / `initializePriorityGroupsBulk()` / `initializeSchedulerGroupsBulk()` を呼ばない。`m_queue_ids` が未初期化となるため `generateQueueMap()` のループが 0 回で終わり、`COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` は書き込まれない。通常の queuestat / pg-drop / watermarkstat は [DPU](../../reference/glossary.md#term-dpu) では機能しない。

[DPU](../../reference/glossary.md#term-dpu) モードで唯一登録されるキューカウンタはホスト TX キューのみ。`m_host_tx_queue_configured` が true かつ `m_queue_ids.size() > m_host_tx_queue`（`portsorch.cpp:6454-6458`）が成立する場合に限り `createPortBufferQueueCounters()` が呼ばれる。それ以外のキューに対する FlexCounter 登録は行われない。

### VoQ モード — カウンタ常時有効・専用テーブル

VoQ システム（`gMySwitchType == "voq"`）では `generateQueueMapPerPort()` (`portsorch.cpp:8446`) が以下の特別挙動を持つ:

- `FLEX_COUNTER_TABLE|QUEUE = disable` の設定に関わらず `addQueueFlexCountersPerPortPerQueueIndex()` を強制呼び出しする（`portsorch.cpp:8483-8484`：「VoQ カウンタを無効化するメカニズムが存在しない」とコメントあり）
- `voq_stat_ids`（`SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` 1 件）を通常 `queue_stat_ids` に追加して登録
- Queue OID → 名前マッピングを `COUNTERS_QUEUE_NAME_MAP`（物理ポートのイーグレスキュー）と `COUNTERS_VOQ_NAME_MAP`（仮想出力キュー）の両方に書き込む (`portsorch.cpp:8520`)

VoQ モードでは egress queue カウンタも常時 enable となるため、`FLEX_COUNTER_TABLE|QUEUE = disable` を書き込んでも VoQ 分のカウンタは停止しない。

### Mellanox (NVIDIA) — trim stat Lua プラグイン補完

`isMlnxPlatform()` (`portsorch.cpp:689`) は環境変数 `platform` に `"mellanox"` が含まれる場合に `true` を返す（`orch.h:42`）。以下の 4 条件がすべて成立するとき、`nvda_port_trim_drop.lua` が PORT_STAT FlexCounter グループのプラグインとして登録される (`portsorch.cpp:857-863`):

1. `isMlnxPlatform()` が true
2. `SAI_PORT_STAT_TRIM_PACKETS` が SAI でサポートされている
3. `SAI_PORT_STAT_TX_TRIM_PACKETS` が SAI でサポートされている
4. `SAI_PORT_STAT_DROPPED_TRIM_PACKETS` が SAI で**サポートされていない**

このプラグインは Redis Lua として PORT ポーリング周期ごとに実行され、`SAI_PORT_STAT_DROPPED_TRIM_PACKETS = SAI_PORT_STAT_TRIM_PACKETS − SAI_PORT_STAT_TX_TRIM_PACKETS` を計算して `COUNTERS:<port_oid>` に書き込む。ASIC が `SAI_PORT_STAT_DROPPED_TRIM_PACKETS` を直接サポートする場合（条件 4 が不成立）はプラグインは登録されない。

Queue 側の trim 統計（`SAI_QUEUE_STAT_TRIM_PACKETS`、`SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS`、`SAI_QUEUE_STAT_TX_TRIM_PACKETS`）は `queue_stat_ids` に静的に含まれており、Lua プラグイン補完は行われない（`portsorch.cpp:389-398`）。

### PFC Watchdog とキュー統計のプラットフォーム別分岐

[PFC Watchdog](../../reference/glossary.md#term-pfc-watchdog)（`PfcWdSwOrch`）は `orchdaemon.cpp:635-843` にてプラットフォームごとに異なるキュー統計・ハンドラクラスでインスタンス化される。これらは `FLEX_COUNTER_TABLE` 経路とは独立した専用 FlexCounter グループを使う。

| `platform` 値 | [PFC](../../reference/glossary.md#term-pfc) port stat に含む追加カウンタ | Queue stat | ハンドラ |
|---|---|---|---|
| `"mellanox"` / `"vs"` | `PFC_N_RX_PAUSE_DURATION_US` (0-7), `PFC_N_RX_PKTS` (0-7) | `PACKETS`, `CURR_OCCUPANCY_BYTES` | ZeroBuffer / Lossy |
| `"broadcom"` | `PFC_N_RX_PKTS` (0-7), `PFC_N_ON2OFF_RX_PKTS` (0-7) | `PACKETS`, `CURR_OCCUPANCY_BYTES` | DLR / [ACL](../../reference/glossary.md#term-acl)（`PFC_DLR_INIT_ENABLE` 環境変数で切替可） |
| `"marvell-teralynx"` / `"marvell-prestera"` / `"clounix"` / `"nephos"` | `PFC_N_RX_PAUSE_DURATION` (0-7), `PFC_N_RX_PKTS` (0-7) | `PACKETS`, `CURR_OCCUPANCY_BYTES` | ZeroBuffer / Lossy |
| `"barefoot"` | `PFC_N_RX_PAUSE_DURATION` (0-7), `PFC_N_RX_PKTS` (0-7) | `PACKETS`, `CURR_OCCUPANCY_BYTES` | [ACL](../../reference/glossary.md#term-acl) / Lossy |
| `"cisco-8000"` | `PFC_N_RX_PKTS` (0-7), `PFC_N_TX_PKTS` (0-7) | `PACKETS` のみ | SaiDlrInit / ActionHandler |
| その他 / 未設定 | — | — | PfcWd orch インスタンス化なし |

Broadcom の `PFC_DLR_INIT_ENABLE` 環境変数は `gSwitchOrch->checkPfcDlrInitEnable()` 戻り値を上書きできる（`"1"` で DLR 強制 ON、`"0"` で OFF）。

### WRED 能力チェックとプラットフォーム透過的 STATE_DB 書き込み

`initCounterCapabilities(gSwitchId)` (`portsorch.cpp:1107`) は orchagent 起動時に 1 回だけ実行される。プラットフォーム種別を問わず同じ API（`sai_query_stats_capability`）を使うが、WRED/ECN の SAI サポート有無は ASIC ごとに異なる:

- `SAI_STATUS_BUFFER_OVERFLOW` が返った場合はバッファを確保して再呼び出しする 2 段取得方式
- 成功時は `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` / `_BYTE_COUNTER` / `WRED_DROPPED_PKT_COUNTER` / `_BYTE_COUNTER` の各フィールドを `isSupported: true/false` で [STATE_DB](../../reference/glossary.md#term-state_db) の `QUEUE_COUNTER_CAPABILITIES` テーブルに書き込む
- 能力問合せ失敗時は全フィールドが `isSupported: false`（初期化値）のまま残る

この STATE_DB エントリは外部ツール・オーケストレータが WRED サポート状況を確認するためのものであり、FlexCounter の実際の登録可否は `isPortStatSupported()` による別経路で判断される。

<!-- /platform -->

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動


### カウンタフィールドセットはコードハードコード

`queue_stat_ids` / `queueWatermarkStatIds` / `ingressPriorityGroupDropStatIds` / `ingressPriorityGroupWatermarkStatIds` は `portsorch.cpp` のソースコードに静的配列として定義される。YANG モデル・CONFIG_DB・FLEX_COUNTER_TABLE のいずれからも変更不可。ハードウェアが SAI で当該カウンタをサポートしない場合、syncd が `sai_get_*_stats` を呼んでも値 `0` が返るか、`SAI_STATUS_NOT_SUPPORTED` でスキップされる（COUNTERS: キーに field が存在しないケースあり）。

### WRED カウンタは SAI ケイパビリティチェック必須

`SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` 等の WRED 統計は `checkWredCapability()`（portsorch.cpp:1894-1909）が SAI のケイパビリティクエリを実施し、サポートを確認したポートの queue にのみ追加される。未サポートの ASIC では `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` を `enable` にしても `COUNTERS:<OID>` に WRED フィールドが現れない（silent 非追加）。

### isQueueMapGenerated / isPriorityGroupMapGenerated ガード

`generateQueueMap()` と `generatePriorityGroupMap()` は `m_isQueueMapGenerated` / `m_isPriorityGroupMapGenerated` フラグで冪等保護されており、一度だけ実行される。orchagent の再起動時に COUNTERS_DB のマッピングが二重書きされることはない。

### VoQ システムのキュー常時 enable

VoQ（Virtual Output Queue）システムでは `gMySwitchType == "voq"` 判定が入り、egress queue も含めて `FLEX_COUNTER_STATUS` の状態に関係なく `addQueueFlexCountersPerPortPerQueueIndex` が常時呼び出される。buffer queue config が sysport に紐付くためで、phy port 側の FLEX_COUNTER_TABLE 設定を `disable` にしてもカウンタが収集され続ける点に注意。

### PG カウンタは createPortBufferPgCounters 経由で条件付き追加

`createPortBufferPgCounters`（BUFFER_PG テーブルへの設定イベントで呼び出される）内で `getPgCountersState()` / `getPgWatermarkCountersState()` を確認後にのみ SAI カウンタを追加。FLEX_COUNTER_TABLE の `PG_DROP` / `PG_WATERMARK` が `enable` でない状態で BUFFER_PG を設定しても SAI カウンタは投入されない。後から `enable` にした場合は `addPriorityGroupFlexCounters()` / `addPriorityGroupWatermarkFlexCounters()` の再実行で追加される。

### allPortsReady 前の遅延

`addQueueFlexCounters` / `addPriorityGroupFlexCounters` は全ポート ready 後に呼ばれるため、orchagent 起動直後（ポート ready 前）に FLEX_COUNTER_TABLE を `enable` にしても FlexCounter への登録は遅延する。起動後に一括適用される。

<!-- /defaults -->

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# キューカウンタ表示
queuestat

# キュー通常カウンタ + トリミング全カウンタ
queuestat -a

# PG ドロップカウンタ
pg-drop -c show

# キュー・PG ウォーターマーク（ユーザーリセット型）
watermarkstat queue unicast
watermarkstat priority-group headroom

# COUNTERS_DB を直接確認
sonic-db-cli COUNTERS_DB hgetall COUNTERS_QUEUE_NAME_MAP
sonic-db-cli COUNTERS_DB hgetall "COUNTERS:<OID>"
```

### よくある誤解

- `FLEX_COUNTER_TABLE|QUEUE` を `enable` にしただけでは BUFFER_QUEUE 設定のないキューのカウンタは収集されない（VoQ システムを除く）
- WRED フィールドが `N/A` 表示になる場合、ASIC が WRED ケイパビリティを SAI に報告していない可能性がある
- `PG_WATERMARK` の値が頻繁に 0 にリセットされるのは `READ_AND_CLEAR` の仕様であり異常ではない
<!-- /ops-hint -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`FLEX_COUNTER_TABLE`](flex-counter-table.md)
- CONFIG_DB: [`BUFFER_QUEUE`](buffer-queue.md)
- CONFIG_DB: [`BUFFER_PG`](buffer-pg.md)
- CLI: `queuestat`、`pg-drop`、`watermarkstat`、`counterpoll`

<!-- ref-triangle:end -->

## 引用元

[^1]: portsorch.cpp:758-787 — COUNTERS_DB 接続と各マッピングテーブル初期化。<https://github.com/sonic-net/sonic-swss/blob/master/orchagent/portsorch.cpp>

[^2]: portsorch.cpp:389-435 — `queue_stat_ids` / `voq_stat_ids` / `queueWatermarkStatIds` / `ingressPriorityGroupWatermarkStatIds` / `ingressPriorityGroupDropStatIds` 静的配列定義。

[^3]: portsorch.cpp:1894-1909 — `checkWredCapability()` による SAI ケイパビリティ問い合わせ。サポート確認後のみ FlexCounter に WRED 統計を追加。

[^4]: portsorch.h:34-42 および portsorch.cpp:90-93 — FlexCounter グループ名定数とハードコードポーリング間隔定義。

[^5]: counternameupdater.cpp:21-34 および hftelorch.cpp:106-170 — `CounterNameMapUpdater::setCounterNameMap()` 内での `gHFTOrch->locallyNotify()` 同期呼び出し。`SUPPORT_COUNTER_TABLES` に `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` が含まれる (`hftelorch.cpp:25-30`)。<https://github.com/sonic-net/sonic-swss/blob/master/orchagent/high_frequency_telemetry/counternameupdater.cpp>

[^6]: portsorch.cpp:8525, 8754, 8819, 8886, 8941, 9099 — Queue / PG マッピング書き込み・削除関数での `CounterCheckOrch::getInstance().addPort()` / `removePort()` 呼び出し。`countercheckorch.cpp:43-50` の 5 分タイマーで `mcCounterCheck()` と `pfcFrameCounterCheck()` を実行。

<!-- glossary-links-injected: 7071347b3cf9 -->
