---
title: COUNTERS_DB QUEUE カウンタ
description: "COUNTERS_DB における QUEUE カウンタエントリ — portsorch が SAI flex counter 経由で収集しキューごとに COUNTERS:<OID> へ格納する送信キュー統計フィールドの構造・デフォルト・書き込み経路の解説。"
area: reference
verification: code-verified
last_verified: 2026-05-15
hard: 0
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.h
    ref: 4305596156d7
  - repo: sonic-net/sonic-utilities
    path: scripts/queuestat
    ref: 39732bceb8bd
related:
  config_db:
    - FLEX_COUNTER_TABLE
    - BUFFER_QUEUE
    - QUEUE
  cli:
    - queuestat
    - counterpoll
---

# COUNTERS_DB QUEUE カウンタ

## 概要

[portsorch](../../reference/glossary.md#term-portsorch)（[orchagent](../../reference/glossary.md#term-orchagent) 内）が [SAI](../../reference/glossary.md#term-sai) の flex counter 機構を通じてポートの送信キューごとに取得する統計カウンタ群[^1]。値は `COUNTERS_DB` の `COUNTERS:<oid>` に格納され、`queuestat` コマンドが読み出す。

> **関連ページ**: PG（Priority Group）カウンタおよびウォーターマーク体系の全体像は [`COUNTERS_DB キュー / PG カウンタテーブル群`](counters-queue.md) を参照。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CFG[("CONFIG_DB<br/>FLEX_COUNTER_TABLE|QUEUE")]
  ORC["portsorch<br/>(orchagent)"]
  SYNCD["syncd<br/>FlexCounter"]
  HW["SAI<br/>sai_queue_api"]
  CNTDB[("COUNTERS_DB<br/>COUNTERS:&lt;oid&gt;")]
  CLI["queuestat"]

  CFG -- FLEX_COUNTER_STATUS=enable --> ORC
  ORC -- COUNTER_ID_LIST --> SYNCD
  SYNCD -- sai_get_queue_stats --> HW
  HW -- 実カウンタ値 --> SYNCD
  SYNCD --> CNTDB
  CNTDB --> CLI
```

!!! note "凡例"
    CONFIG_DB の `FLEX_COUNTER_TABLE|QUEUE` が `enable` になると portsorch が SAI カウンタ ID リストを syncd へ投入。syncd が 10 秒ごと（コードデフォルト）にポーリングして `COUNTERS:<oid>` を更新する。

<!-- /cdb-mermaid -->

## key 構造

### キュー名→OID マップ

```text
COUNTERS_DB / COUNTERS_QUEUE_NAME_MAP   (Hash)
  field: <port_alias>:<queue_index>    (例: Ethernet0:0)
  value: <SAI OID>                     (例: oid:0x00000000000001a0)
```

VoQ システムでは field 形式が `<system_port_alias>:<queue_index>`（例: `Linecard1|ASIC0|Ethernet0:0`）となる。

### 補助マッピングテーブル

```text
COUNTERS_QUEUE_PORT_MAP   field: <queue_oid>  → value: <port_oid>
COUNTERS_QUEUE_INDEX_MAP  field: <queue_oid>  → value: <queue_index (int)>
COUNTERS_QUEUE_TYPE_MAP   field: <queue_oid>  → value: SAI_QUEUE_TYPE_UNICAST |
                                                        SAI_QUEUE_TYPE_MULTICAST |
                                                        SAI_QUEUE_TYPE_ALL |
                                                        SAI_QUEUE_TYPE_UNICAST_VOQ
```

### カウンタハッシュ

```text
COUNTERS_DB / COUNTERS:<oid>   (Hash)
  field: <SAI_QUEUE_STAT_*>
  value: <uint64 カウンタ値 (文字列)>
```

## フィールド一覧

### 通常カウンタ（QUEUE_STAT_COUNTER グループ）

`FLEX_COUNTER_TABLE|QUEUE` が `enable` のときに収集。ソース: `portsorch.cpp:389-398` の `queue_stat_ids`[^2]。

| COUNTERS:<oid> フィールド | 説明 |
|--------------------------|------|
| `SAI_QUEUE_STAT_PACKETS` | キューからの送信パケット数（累積） |
| `SAI_QUEUE_STAT_BYTES` | キューからの送信バイト数（累積） |
| `SAI_QUEUE_STAT_DROPPED_PACKETS` | キュードロップパケット数（累積） |
| `SAI_QUEUE_STAT_DROPPED_BYTES` | キュードロップバイト数（累積） |
| `SAI_QUEUE_STAT_TRIM_PACKETS` | Packet Trimming 発生パケット数 |
| `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` | トリミング後ドロップパケット数 |
| `SAI_QUEUE_STAT_TX_TRIM_PACKETS` | トリミング後送信パケット数 |

VoQ システムでは追加フィールド `SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`（Credit Watchdog 削除パケット数）が加わる[^2]。

### ウォーターマーク（QUEUE_WATERMARK_STAT_COUNTER グループ）

`FLEX_COUNTER_TABLE|QUEUE_WATERMARK` が `enable` のときに収集。`StatsMode::READ_AND_CLEAR`（ポーリングごとに SAI 側ウォーターマークレジスタをリセット）。ソース: `portsorch.cpp:405-408` の `queueWatermarkStatIds`[^2]。

| COUNTERS:<oid> フィールド | 説明 |
|--------------------------|------|
| `SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES` | 共有バッファ使用量ウォーターマーク（バイト） |

### WRED/ECN カウンタ（WRED_ECN_QUEUE_STAT_COUNTER グループ）

`FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` が `enable` かつ SAI が WRED ケイパビリティをサポートする場合のみ収集[^3]。ソース: `portsorch.cpp:429-435` の `wred_queue_stat_ids`。

| COUNTERS:<oid> フィールド | 説明 |
|--------------------------|------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | WRED ECN マーキングパケット数 |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | WRED ECN マーキングバイト数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | WRED ドロップパケット数 |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | WRED ドロップバイト数 |

## FlexCounter グループとポーリング間隔

| FlexCounter グループ名 | CONFIG_DB キー | StatsMode | コードデフォルトポーリング間隔 |
|--------------------|--------------|-----------|--------------------------|
| `QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE` | READ | 10000 ms |
| `QUEUE_WATERMARK_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | READ_AND_CLEAR | 60000 ms |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | READ | 10000 ms |

`counterpoll queue interval <ms>` / `counterpoll queue-watermark interval <ms>` で上書き可能。

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

<!-- evidence: sonic-swss/orchagent/portsorch.cpp (ref:4305596156d7),
     sonic-swss/orchagent/portsorch.h (ref:4305596156d7),
     sonic-utilities/scripts/queuestat (ref:39732bceb8bd) -->

### カウンタフィールドセットはコードハードコード

`queue_stat_ids`（portsorch.cpp:389-398）はソースコードに静的配列として定義される。YANG モデル・CONFIG_DB・`FLEX_COUNTER_TABLE` のいずれからも変更不可[^4]。ハードウェアが当該カウンタをサポートしない場合、`queuestat` の表示では `N/A` となる。

### Packet Trimming フィールドは常時 queue_stat_ids に含まれる

`SAI_QUEUE_STAT_TRIM_PACKETS` / `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` / `SAI_QUEUE_STAT_TX_TRIM_PACKETS` は、Packet Trimming 機能の有効・無効に関係なく `queue_stat_ids` に含まれる。Trimming 非対応 ASIC では値 `0` か `N/A`。`queuestat` の `--all`（`-a`）フラグで表示列が追加される（デフォルト `queuestat` では非表示）。

### ポーリング間隔のコードデフォルト

`FLEX_COUNTER_TABLE|QUEUE` に `POLL_INTERVAL` が未設定の場合、portsorch がコードにハードコードされた初期値を syncd に投入する[^4]。

| グループ | ハードコード定数（portsorch.cpp:90-91） | 値 |
|--------|--------------------------------------|-----|
| `QUEUE_STAT_COUNTER` | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | **10000 ms** |
| `QUEUE_WATERMARK_STAT_COUNTER` | `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | **60000 ms** |
| `WRED_ECN_QUEUE_STAT_COUNTER` | `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS`（共用） | **10000 ms** |

### WRED カウンタは SAI ケイパビリティチェック必須

`SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` 等の WRED 統計は `checkWredCapability()`（portsorch.cpp:1894-1909）が SAI のケイパビリティクエリを実施し、サポートを確認したポートの queue にのみ `wred_queue_stat_manager` へ追加される[^3]。未サポート ASIC では `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE` を `enable` にしても `COUNTERS:<oid>` に WRED フィールドが現れない（silent 非追加）。

### ウォーターマークは READ_AND_CLEAR で動作

`QUEUE_WATERMARK_STAT_COUNTER` グループは `StatsMode::READ_AND_CLEAR`（portsorch.cpp:735）で初期化される。syncd がポーリングするたびに SAI 側のウォーターマークレジスタがクリアされる。これは `watermarkstat` が PERIODIC / PERSISTENT / USER の 3 テーブルに分岐する基盤動作であり、異常ではない。

### VoQ システムでは voq_stat_ids が自動合算

`gMySwitchType == "voq"` の場合、`addQueueFlexCountersPerPortPerQueueIndex` が `voq=true` で呼ばれ、`queue_stat_ids` に加えて `voq_stat_ids`（`SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`）が合算される（portsorch.cpp:8601-8614）。VoQ モード以外では Credit WD フィールドは `COUNTER_ID_LIST` に含まれない。

### isQueueMapGenerated 冪等ガード

`generateQueueMap()`（`COUNTERS_QUEUE_NAME_MAP` 等のマッピング書き込み）は `m_isQueueMapGenerated` フラグで一度だけ実行される（portsorch.cpp:8393-8396）。orchagent 再起動時に `COUNTERS_DB` のマッピングが重複書きされることはない。

### FLEX_COUNTER_STATUS 未設定時の挙動

`FLEX_COUNTER_TABLE|QUEUE` の `FLEX_COUNTER_STATUS` が `enable` になるまで、syncd は SAI ポーリングを行わない。カウンタ値は `0` のまま（または初期化前）。ポートが allPortsReady 前の場合、`enable` 受信後も FlexCounter への登録は遅延し、全ポート ready 後に一括適用される。

<!-- /defaults -->

<!-- ordering -->
## 書込み順序依存・タイミング依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/portsorch.cpp (ref:4305596156d7),
     sonic-swss/orchagent/flexcounterorch.cpp (ref:4305596156d7) -->

### 1. SAI OID フェッチが先行必須

`PortsOrch::initializePorts()`（`portsorch.cpp:6583-6598`）が `initializeQueuesBulk()` で SAI から各ポートの Queue OID リスト（`SAI_PORT_ATTR_QOS_QUEUE_LIST`）を取得して `port.m_queue_ids` へキャッシュするまで、`generateQueueMap()` / `generateQueueMapPerPort()` は OID が空のまま動作してマッピングを書き込まない[^5]。`FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が `false` の間 `return` する（`flexcounterorch.cpp:164-167`）ため、`FLEX_COUNTER_TABLE|QUEUE = enable` を orchagent 起動前に書き込んでいても、全ポート ready 後まで `generateQueueMap()` 呼び出しは自動的に遅延する。

### 2. Warm-reboot 時の 60 秒遅延

`FlexCounterOrch` コンストラクタ（`flexcounterorch.cpp:127-136`）は warm-reboot 時に `FLEX_COUNTER_DELAY_SEC = 60` 秒のタイマーを設定し、`doTask()` 先頭の `if (!m_delayTimerExpired) return;`（`flexcounterorch.cpp:156-158`）で全 FlexCounter 処理をブロックする。cold boot では即 `m_delayTimerExpired = true` になり遅延なし。warm-reboot 中に `FLEX_COUNTER_TABLE|QUEUE = enable` を書き込んでも最大 60 秒間 `COUNTERS:<oid>` の更新が停止する[^5]。

### 3. `BUFFER_QUEUE` と `FLEX_COUNTER_TABLE|QUEUE = enable` の順序

`BUFFER_QUEUE` SET が届いたときに `createPortBufferQueueCounters()`（`portsorch.cpp:8700-8755`）が `flexCounterOrch->getQueueCountersState()` を確認し、`false`（= `FLEX_COUNTER_TABLE|QUEUE` が disable）ならカウンタ登録をスキップする。`BUFFER_QUEUE` を先に書いた後に `enable` を書くと、`enable` 処理時に `addQueueFlexCounters(getQueueConfigurations())` が実行され、その時点で非ゼロプロファイルを持つ `BUFFER_QUEUE` エントリが一括登録される[^5]。逆順（`enable` 先・`BUFFER_QUEUE` 後）でも即時登録されるため、**どちらの順序でも最終状態は同じ**。

### 4. `m_isQueueMapGenerated` — `generateQueueMap()` は一度だけ実行

`generateQueueMap()`（`portsorch.cpp:8391-8396`）は `m_isQueueMapGenerated` フラグで保護されており、初回のみ実行される。`FLEX_COUNTER_TABLE|QUEUE` と `FLEX_COUNTER_TABLE|QUEUE_WATERMARK` の enable 順序に関係なく最初の enable で一度だけ走る。`m_isQueueMapGenerated` がセット済みの状態で新規ポートが追加された場合は `createPortBufferQueueCounters()` 経由でマッピングが生成される[^5]。

### 5. `isCreateOnlyConfigDbBuffers` の事後変更は限定的

`FlexCounterOrch` は起動時に `DEVICE_METADATA|localhost|create_only_config_db_buffers` を読み込み `m_createOnlyConfigDbBuffers` にキャッシュする。`true` の場合、`getQueueConfigurations()` は `BUFFER_QUEUE` に非ゼロプロファイルが設定されたキューのみ対象にする（デフォルト `false` = 全キュー）。起動後に値を変更しても、既に `m_isQueueMapGenerated = true` でガードされている場合は以後の `getQueueConfigurations()` 呼び出しにのみ影響し、既登録カウンタは変更されない。既存カウンタを変更するには orchagent 再起動が必要[^5]。

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI OID フェッチ (`initializeQueuesBulk`) → `generateQueueMap()` | 先行必須 | `allPortsReady()` チェックで自動待機 |
| 2 | Warm-reboot 時 60 秒 delay timer | 強制遅延 | 定数 `FLEX_COUNTER_DELAY_SEC=60`。60 秒後に自動再開 |
| 3 | `BUFFER_QUEUE` SET と `FLEX_COUNTER_TABLE\|QUEUE = enable` の順序 | どちらが先でも最終状態は同じ | enable 後に `addQueueFlexCounters()` で追加 |
| 4 | `m_isQueueMapGenerated` ガード | 冪等保護（順序非依存） | 新規ポートは `createPortBufferQueueCounters()` 経由 |
| 5 | `DEVICE_METADATA.create_only_config_db_buffers` 事後変更 | 以後の呼び出しにのみ影響 | 既存カウンタ変更には orchagent 再起動が必要 |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

YANG leafref を超えた他テーブル・他 DB・プラットフォームファイルへの実装上の依存関係。

| 参照先 | DB / 場所 | 方向 | 契機 | 根拠コード |
|--------|-----------|------|------|-----------|
| `FLEX_COUNTER_TABLE\|QUEUE` | CONFIG_DB | READ | `FLEX_COUNTER_STATUS = enable` を受信した時点で `addQueueFlexCounters()` を呼び SAI カウンタ登録を開始。`disable` で `clearQueueFlexCounters()` を呼びカウンタ登録を解除 | `flexcounterorch.cpp:247-252` |
| `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | CONFIG_DB | READ | `enable` 受信時に `addQueueWatermarkFlexCounters()` を呼び `QUEUE_WATERMARK_STAT_COUNTER` グループを開始。`disable` で解除 | `flexcounterorch.cpp:258-264` |
| `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | CONFIG_DB | READ | `enable` 受信時に `addWredQueueFlexCounters(getQueueConfigurations())` を呼び WRED カウンタ登録を開始。SAI ケイパビリティ未サポートポートは silent にスキップ | `flexcounterorch.cpp:276-281` |
| `BUFFER_QUEUE` | CONFIG_DB | READ | `create_only_config_db_buffers = true` の場合、`getQueueConfigurations()` が `BUFFER_QUEUE` に非ゼロプロファイルが設定されたキューのみを対象にする。`false`（デフォルト）では全キューを対象 | `flexcounterorch.cpp:544-554` |
| `DEVICE_METADATA\|localhost` | CONFIG_DB | READ | 起動時に `create_only_config_db_buffers` を 1 回読み込み `m_createOnlyConfigDbBuffers` にキャッシュ。`handleDeviceMetadataTable()` が動的更新を購読 | `flexcounterorch.cpp:106-124, 488-521` |
| `COUNTERS_QUEUE_NAME_MAP` | COUNTERS_DB | WRITE | `generateQueueMap()` が `<port_alias>:<queue_index>` → SAI OID マッピングを書き込む。`m_isQueueMapGenerated` フラグで冪等保護（初回のみ） | `portsorch.cpp:8391-8443` |
| `COUNTERS_QUEUE_PORT_MAP` | COUNTERS_DB | WRITE | `<queue_oid>` → `<port_oid>` の逆引きマップ。`generateQueueMapPerPort()` で書き込まれ、`queuestat` がキューをポートに紐付ける際に参照 | `portsorch.cpp:778-782` |
| `COUNTERS_QUEUE_INDEX_MAP` | COUNTERS_DB | WRITE | `<queue_oid>` → `<queue_index>` の逆引きマップ。`generateQueueMapPerPort()` で書き込まれ、`queuestat` が表示列の並べ替えに使用 | `portsorch.cpp:780-781` |
| `COUNTERS_QUEUE_TYPE_MAP` | COUNTERS_DB | WRITE | `<queue_oid>` → `SAI_QUEUE_TYPE_*` の逆引きマップ。UC / MC / ALL / VOQ の判別に使用 | `portsorch.cpp:781-782` |
| SAI `SAI_PORT_ATTR_QOS_QUEUE_LIST` | SAI（ハードウェア） | READ | `initializeQueuesBulk()` が各ポートの Queue OID リストを SAI から取得して `port.m_queue_ids` へキャッシュ。このフェッチが完了するまで `generateQueueMap()` はマッピングを書き込まない | `portsorch.cpp:6583-6598` |

### 補足

- **`FLEX_COUNTER_TABLE` との依存は双方向**: `COUNTERS_DB` の `COUNTERS:<oid>` は `FLEX_COUNTER_TABLE` の enable/disable 状態が `true` の間のみ syncd がポーリングして更新する。disable にするとポーリングは停止するが、`COUNTERS_QUEUE_NAME_MAP` 等のマッピングテーブルは削除されない。
- **`BUFFER_QUEUE` との依存は条件付き**: `create_only_config_db_buffers = false`（デフォルト）では `BUFFER_QUEUE` の設定内容に関係なく全キューのカウンタが有効化される。この場合 `BUFFER_QUEUE` の書込み順序はカウンタ有効化の最終状態に影響しない（Phase B 依存 #3 参照）。
- **VoQ モード固有**: `gMySwitchType == "voq"` の場合、`FLEX_COUNTER_TABLE|QUEUE` の enable 状態に関係なく `generateQueueMapPerPort()` が直接 `addQueueFlexCountersPerPortPerQueueIndex()` を呼ぶため、VoQ 環境では上記 `FLEX_COUNTER_TABLE` 依存の一部が無効化される（`portsorch.cpp:8499-8514`）。

<!-- /cross-refs -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB FLEX_COUNTER_TABLE](flex-counter-table.md)
- [CONFIG_DB BUFFER_QUEUE](buffer-queue.md)
- [COUNTERS_DB キュー / PG カウンタ全体](counters-queue.md)
- CLI: `queuestat`、`counterpoll`

<!-- ref-triangle:end -->

## 引用元

[^1]: portsorch.cpp:758-782 — COUNTERS_DB 接続と COUNTERS_QUEUE_NAME_MAP / COUNTERS_QUEUE_PORT_MAP / COUNTERS_QUEUE_INDEX_MAP / COUNTERS_QUEUE_TYPE_MAP 初期化。<https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/portsorch.cpp#L758>

[^2]: portsorch.cpp:389-408 — `queue_stat_ids` / `voq_stat_ids` / `queueWatermarkStatIds` 静的配列定義。<https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/portsorch.cpp#L389>

[^3]: portsorch.cpp:1894-1909 — `checkWredCapability()` による SAI ケイパビリティ問い合わせ。サポート確認後のみ FlexCounter に WRED 統計を追加。<https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/portsorch.cpp#L1894>

[^4]: portsorch.h:34-42 および portsorch.cpp:90-91 — FlexCounter グループ名定数とハードコードポーリング間隔定義。<https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/portsorch.h#L34>

[^5]: `sonic-swss/orchagent/portsorch.cpp:6583-6598,8391-8443,8700-8755` / `sonic-swss/orchagent/flexcounterorch.cpp:127-136,156-167,247-252,544-554` — 書込み順序依存・タイミング依存の実装根拠。<https://github.com/sonic-net/sonic-swss/blob/4305596156d7/orchagent/flexcounterorch.cpp>
