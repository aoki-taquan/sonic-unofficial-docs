---
title: STATE_DB カウンタ能力テーブル
description: "STATE_DB に格納されるカウンタ能力情報テーブル群 (PORT_COUNTER_CAPABILITIES / QUEUE_COUNTER_CAPABILITIES / DEBUG_COUNTER_CAPABILITIES) — orchagent が SAI 問い合わせ結果を書き込み、portstat や show debug-counter が参照する能力フラグの構造・デフォルト・書き込み経路の解説。"
area: reference
verification: code-verified
last_verified: 2026-05-15
hard: 0
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/portsorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/debugcounterorch.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss
    path: orchagent/debug_counter/drop_counter.cpp
    ref: 4305596156d7
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d
  - repo: sonic-net/sonic-utilities
    path: utilities_common/portstat.py
    ref: 39732bceb8bd
related:
  config_db:
    - FLEX_COUNTER_TABLE
    - DEBUG_COUNTER
  cli:
    - portstat
    - counterpoll
---

# STATE_DB カウンタ能力テーブル

## 概要

[orchagent](../../reference/glossary.md#term-orchagent) は起動時に [SAI](../../reference/glossary.md#term-sai) へカウンタ能力を問い合わせ、その結果を `STATE_DB` の 3 つのテーブルに書き込む[^1]。これらのテーブルは **読み取り専用** の能力情報であり、ユーザが [CONFIG_DB](../../reference/glossary.md#term-config_db) から書き込む設定テーブルではない。

| [STATE_DB](../../reference/glossary.md#term-state_db) テーブル | 書き込み元 | 参照先 |
|-----------------|----------|--------|
| `PORT_COUNTER_CAPABILITIES` | [portsorch](../../reference/glossary.md#term-portsorch) (`initCounterCapabilities`) | portstat.py、portstat CLI |
| `QUEUE_COUNTER_CAPABILITIES` | [portsorch](../../reference/glossary.md#term-portsorch) (`initCounterCapabilities`) | queuestat CLI |
| `DEBUG_COUNTER_CAPABILITIES` | debugcounterorch (`publishDropCounterCapabilities`) | show debug-counter capabilities |

---

## PORT_COUNTER_CAPABILITIES テーブル

### key 構造

```text
STATE_DB / PORT_COUNTER_CAPABILITIES | <counter_group_name>   (Hash)
  field: isSupported   value: "true" | "false"
```

### フィールド一覧

| key (counter_group_name) | isSupported 条件 | 対応 [SAI](../../reference/glossary.md#term-sai) 統計 |
|--------------------------|----------------|--------------|
| `WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` がプラットフォームでサポートされている | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` |
| `WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER` | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` がサポートされている | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` |
| `WRED_ECN_PORT_WRED_RED_DROP_COUNTER` | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` がサポートされている | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` |
| `WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER` | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` がサポートされている | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` |

### 書き込みタイミング

1. **起動直後**: [portsorch](../../reference/glossary.md#term-portsorch) コンストラクタが `initCounterCapabilities()` を呼ぶ。まず全フィールドを `isSupported="false"` で書き込む[^2]
2. **[SAI](../../reference/glossary.md#term-sai) 問い合わせ後**: `sai_query_stats_capability(SAI_OBJECT_TYPE_PORT, ...)` でプラットフォームのポート統計能力を取得し、サポートされる統計 enum ごとに `isSupported="true"` に更新[^3]
3. **SAI 失敗時**: 問い合わせが失敗すると全フィールドが `"false"` のままになる。`SWSS_LOG_NOTICE` を出力するのみで [orchagent](../../reference/glossary.md#term-orchagent) はエラー終了しない

---

## QUEUE_COUNTER_CAPABILITIES テーブル

### key 構造

```text
STATE_DB / QUEUE_COUNTER_CAPABILITIES | <counter_group_name>   (Hash)
  field: isSupported   value: "true" | "false"
```

### フィールド一覧

| key (counter_group_name) | isSupported 条件 | 対応 SAI 統計 |
|--------------------------|----------------|--------------|
| `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` がサポートされている | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` |
| `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` がサポートされている | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` |
| `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` がサポートされている | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` |
| `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` がサポートされている | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` |

PORT_COUNTER_CAPABILITIES と同様に全フィールドが起動時 `"false"` で初期化され、`sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE, ...)` の結果に基づいて `"true"` に更新される[^4]。

---

## DEBUG_COUNTER_CAPABILITIES テーブル

### key 構造

```text
STATE_DB / DEBUG_COUNTER_CAPABILITIES | <counter_type>   (Hash)
  field: count     value: "<整数文字列>"   — 利用可能な debug counter 数
  field: reasons   value: '["<drop_reason>",...]'   — サポートされる drop reason 一覧
```

### counter_type キー

| counter_type | 説明 |
|-------------|------|
| `PORT_INGRESS_DROPS` | ポート単位の ingress drop カウンタ |
| `PORT_EGRESS_DROPS` | ポート単位の egress drop カウンタ |
| `SWITCH_INGRESS_DROPS` | スイッチ全体の ingress drop カウンタ |
| `SWITCH_EGRESS_DROPS` | スイッチ全体の egress drop カウンタ |

### 書き込みロジック

`DebugCounterOrch::publishDropCounterCapabilities()` が起動時に呼ばれ、以下の順で [STATE_DB](../../reference/glossary.md#term-state_db) を更新する[^5]。

1. SAI drop reason 能力を取得: `getSupportedDropReasons(SAI_DEBUG_COUNTER_ATTR_IN_DROP_REASON_LIST)` および `..._OUT_DROP_REASON_LIST`
2. サポートされる counter_type を取得: `getSupportedCounterTypes()` が `sai_query_attribute_enum_values_capability()` を呼ぶ
3. 条件が揃ったエントリのみ書き込み:
   - `count = "0"` の counter_type は書き込まない
   - `reasons` が空文字列の counter_type は書き込まない

!!! note "エントリ不存在の意味"
    `DEBUG_COUNTER_CAPABILITIES` にキーが存在しない counter_type はプラットフォームが SAI debug counter query をサポートしないことを示す。`show debug-counter capabilities` の出力が空の場合も同様。

---

<!-- defaults -->
## 暗黙デフォルト・コード由来挙動 (Phase A)

<!-- evidence: sonic-swss/orchagent/portsorch.cpp, sonic-swss/orchagent/debugcounterorch.cpp,
     sonic-swss/orchagent/debug_counter/drop_counter.cpp,
     sonic-utilities/utilities_common/portstat.py -->

### 起動時 false 初期化と更新競合ウィンドウ

| 種類 | 詳細 |
|------|------|
| コード由来デフォルト | 全フィールドが `"false"` で先書きされる (portsorch.cpp:1868-1879)。SAI 問い合わせ完了まで数ミリ秒間、portstat.py が参照すると [WRED](../../reference/glossary.md#term-wred) カウンタが N/A と表示される |
| SAI 失敗時残存 | `sai_query_stats_capability()` 失敗時は全フィールドが `"false"` のまま。SWSS_LOG_NOTICE のみで silent 継続 (portsorch.cpp:1965-1968) |

### portstat.py の WRED silent skip

`portstat.py:297-329` で `isSupported` が `"true"` でない場合、対応する SAI カウンタを `counter_bucket_dict` から削除する。[COUNTERS_DB](../../reference/glossary.md#term-counters_db) のポーリング対象から外れ、エラーなく `N/A` となる[^6]。

| 条件 | 挙動 |
|------|------|
| `isSupported = "true"` | [COUNTERS_DB](../../reference/glossary.md#term-counters_db) から `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` をポーリング |
| `isSupported = "false"` または キーなし | ポーリング対象から除外。portstat 表示は `N/A` |

### DEBUG_COUNTER_CAPABILITIES の選択的書き込み

| 条件 | 挙動 |
|------|------|
| プラットフォームが SAI debug counter を未サポート | `getSupportedDropReasons()` が空集合返却 → テーブルエントリ書き込みなし |
| count=0 の counter_type | `publishDropCounterCapabilities()` が書き込みをスキップ (debugcounterorch.cpp:348-354) |
| SAI query 失敗 | `getSupportedCounterTypes()` が空集合返却。全 counter_type がスキップされテーブル自体が空 |

<!-- /defaults -->

---

<!-- ordering -->
## 書込み順・タイミング依存 (Phase B)

<!-- evidence: sonic-swss/orchagent/portsorch.cpp, sonic-swss/orchagent/debugcounterorch.cpp,
     sonic-swss/orchagent/flexcounterorch.cpp, sonic-swss/orchagent/orchdaemon.cpp -->

### 1. false 先書き → SAI 問い合わせ → true 更新（自己完結型）

`PortsOrch::initCounterCapabilities()` は **単一コンストラクタ呼び出し内** で 2 フェーズに分けて [STATE_DB](../../reference/glossary.md#term-state_db) を更新する[^7]。

1. 全 [WRED](../../reference/glossary.md#term-wred) フィールドを `isSupported="false"` で先書き (portsorch.cpp:1872-1879)
2. `sai_query_stats_capability()` 成功後、サポートされる enum ごとに `isSupported="true"` に上書き (portsorch.cpp:1892-1968)

| タイミング | PORT_COUNTER_CAPABILITIES | QUEUE_COUNTER_CAPABILITIES |
|-----------|--------------------------|---------------------------|
| コンストラクタ開始直後 | 全フィールド `"false"` | 全フィールド `"false"` |
| SAI 問い合わせ成功後 | サポート済みフィールドのみ `"true"` | サポート済みフィールドのみ `"true"` |
| SAI 問い合わせ失敗時 | 全フィールド `"false"` のまま | 全フィールド `"false"` のまま |

!!! note "一時的な false 観測"
    portsorch 初期化完了前に portstat 等が STATE_DB を参照すると全フィールドが `"false"` の中間状態を観測することがある。portstat はカウンタをポーリング対象から除外するだけでエラーを出さない。

### 2. portsorch → debugcounterorch の書き込み順保証

orchdaemon が STATE_DB への書き込み順序を確定的に決定する[^8]。

```
orchdaemon.cpp:232  gPortsOrch = new PortsOrch(...)
                      └─ portsorch.cpp:1107 initCounterCapabilities()
                           → PORT_COUNTER_CAPABILITIES / QUEUE_COUNTER_CAPABILITIES 書き込み
orchdaemon.cpp:452  gDebugCounterOrch = new DebugCounterOrch(...)
                      └─ debugcounterorch.cpp:37 publishDropCounterCapabilities()
                           → DEBUG_COUNTER_CAPABILITIES 書き込み
```

`DebugCounterOrch` コンストラクタ内で `gPortsOrch->attach(this)` が呼ばれるのは `publishDropCounterCapabilities()` の**後**であり、DEBUG_COUNTER_CAPABILITIES 書き込みは PORT_COUNTER_CAPABILITIES 完了後に来ることが orchdaemon 構造上保証される。

### 3. warm-reboot 時の flexcounterorch 60 秒遅延は STATE_DB に無影響

- `FlexCounterOrch` は warm-reboot 時に `FLEX_COUNTER_DELAY_SEC = 60` 秒のタイマーを起動し、`doTask()` を遅延させる (flexcounterorch.cpp:44, 127-137)。
- この遅延は **[FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) へのカウンタポーリング登録**を遅らせるためのものであり、`STATE_DB / *_COUNTER_CAPABILITIES` の書き込みには影響しない。
- `FlexCounterOrch::bake()` は warm-reboot reconcile フェーズで意図的に何もしない（コメント: "FCs are not data plane configuration required during reconciling process"）(flexcounterorch.cpp:525-535)。
- 結果として STATE_DB 能力テーブルは常に [orchagent](../../reference/glossary.md#term-orchagent) 起動直後（warm-reboot 開始直後）に書き込まれ、60 秒遅延の影響外となる。

### 4. generatePortCounterMap() との順序関係

| ステップ | 発生タイミング | STATE_DB への影響 |
|---------|-------------|----------------|
| `initCounterCapabilities()` | portsorch コンストラクタ（orchagent 起動直後） | `PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` 書き込み |
| `generatePortCounterMap()` | flexcounterorch が PORT カウンタ enable を受信したとき | `FLEX_COUNTER_DB` への登録のみ（STATE_DB 非関与） |
| portstat が `PORT_COUNTER_CAPABILITIES` を参照 | カウンタポーリング実行時 | `isSupported` に基づきポーリング対象を決定 |

`generatePortCounterMap()` は `PORT_COUNTER_CAPABILITIES` テーブルを**参照しない**。portstat.py が STATE_DB を参照する時点では常に `initCounterCapabilities()` 完了後であるため、能力情報が未書き込みの状態で参照されることはない[^9]。

### 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `"false"` 先書き → SAI query → `"true"` 更新 | 自己完結（コンストラクタ内） | 起動直後の transient `"false"` は portstat の N/A 表示のみ |
| 2 | portsorch 初期化 → debugcounterorch 初期化 | orchdaemon が強制保証 | 変更不要 |
| 3 | warm-reboot 60 秒遅延 | STATE_DB には無影響 | 能力テーブルはコンストラクタで同期書き込み済み |
| 4 | `initCounterCapabilities` < `generatePortCounterMap` | 常に保証 | portstat 参照時点では能力テーブル書き込み済み |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-cross-refs.md`

`PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` / `DEBUG_COUNTER_CAPABILITIES` はいずれも [YANG](../../reference/glossary.md#term-yang) 未モデル化のオペレーショナルテーブルであり、orchagent が **書き手 (producer only)** として書き込む。ここでの暗黙参照は、生成側（portsorch / debugcounterorch）が依存する SAI / DB リソースと、消費側（portstat / dropconfig）が参照するテーブルを指す。

### 生成側 (producer) の暗黙依存

| 参照先リソース | 依存 orchagent | 条件 | 依存種別 | evidence |
|---|---|---|---|---|
| SAI `sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE, ...)` | `portsorch::initCounterCapabilities` | orchagent 起動直後（コンストラクタ内） | SAI 接続確立 + `gSwitchId` 確定が前提。失敗時は全フィールドが `"false"` のまま残存 | `portsorch.cpp:1882-1921` |
| SAI `sai_query_stats_capability(SAI_OBJECT_TYPE_PORT, ...)` | `portsorch::initCounterCapabilities` | 同上 | SAI query 失敗時 `SWSS_LOG_NOTICE` のみ。エラー終了なし | `portsorch.cpp:1929-1967` |
| SAI `sai_query_attribute_enum_values_capability(...)` | `debugcounterorch::publishDropCounterCapabilities` | debugcounterorch コンストラクタ内 | `getSupportedDropReasons()` が空返却 → テーブル書き込みなし | `debugcounterorch.cpp:315-363` |
| `STATE_DB` 接続（`m_state_db`） | `portsorch` / `debugcounterorch` | 起動時 | 接続失敗時は `Table` 生成例外 → orchagent クラッシュ | `portsorch.cpp:793-794`, `debugcounterorch.cpp:31` |

### 消費側 (consumer) の暗黙参照

| 参照元 | 参照テーブル | 参照フィールド | 参照タイミング | 挙動（不在時） | evidence |
|---|---|---|---|---|---|
| `portstat.py`（[sonic-utilities](../../reference/glossary.md#term-sonic-utilities)） | `PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_*_DROP_COUNTER` | `isSupported` | ポーリング実行前（毎回 HGET） | `"true"` 以外 → 対応 SAI カウンタをポーリング対象から silent 除外 → `N/A` 表示 | `portstat.py:297-329` |
| `scripts/dropconfig`（[sonic-utilities](../../reference/glossary.md#term-sonic-utilities)） | `DEBUG_COUNTER_CAPABILITIES\|<counter_type>` | `count`, `reasons` | `show debug-counter capabilities` 実行時 | テーブルが空 → 出力が空（エラーなし） | `dropconfig:423-455` |

### YANG 非定義による暗黙制約

上記いずれの参照も [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) に leafref として記述されていない。[WRED](../../reference/glossary.md#term-wred) カウンタが `N/A` になる場合は以下のコマンドで STATE_DB を直接確認すること:

```bash
# PORT_COUNTER_CAPABILITIES 確認
sonic-db-cli STATE_DB hgetall 'PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER'

# QUEUE_COUNTER_CAPABILITIES 確認
sonic-db-cli STATE_DB keys 'QUEUE_COUNTER_CAPABILITIES|*'

# DEBUG_COUNTER_CAPABILITIES 確認
sonic-db-cli STATE_DB keys 'DEBUG_COUNTER_CAPABILITIES|*'
```

<!-- /cross-refs -->

---

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-failure.md`

<!-- evidence: sonic-swss/orchagent/portsorch.cpp:1850-1968,
     sonic-swss/orchagent/debugcounterorch.cpp:315-363,
     sonic-swss/orchagent/debug_counter/drop_counter.cpp:298-446 -->

これらの STATE_DB テーブルは orchagent 起動直後にコンストラクタ内で書き込まれる。SAI query 失敗はすべて **silent 継続** であり orchagent を停止させない。ユーザへの影響はカウンタが `N/A` になるか、`show debug-counter capabilities` が空になるかのいずれかである。

| # | 失敗箇所 | ログレベル | orchagent 継続 | STATE_DB への影響 | 診断コマンド |
|---|---------|-----------|--------------|-----------------|------------|
| 1 | `sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE, ...)` 失敗 | `SWSS_LOG_NOTICE` | 継続 | `QUEUE_COUNTER_CAPABILITIES` 全フィールドが `"false"` のまま残存 | `sonic-db-cli STATE_DB hgetall 'QUEUE_COUNTER_CAPABILITIES\|WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER'` |
| 2 | `sai_query_stats_capability(SAI_OBJECT_TYPE_PORT, ...)` 失敗 | `SWSS_LOG_NOTICE` | 継続 | `PORT_COUNTER_CAPABILITIES` 全フィールドが `"false"` のまま残存 | `sonic-db-cli STATE_DB hgetall 'PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER'` |
| 3 | `getSupportedDropReasons()` SAI query 失敗 | `SWSS_LOG_NOTICE` | 継続 | `DEBUG_COUNTER_CAPABILITIES` テーブルが空（エントリ書き込みなし） | `sonic-db-cli STATE_DB keys 'DEBUG_COUNTER_CAPABILITIES\|*'` |
| 4 | `getSupportedCounterTypes()` SAI query 失敗 または SAI メタデータ null | `SWSS_LOG_NOTICE` / `SWSS_LOG_ERROR` | 継続 | 同上 | 同上 |
| 5 | `getSupportedDebugCounterAmounts()` が 0 返却（query 失敗またはリソース枯渇） | `SWSS_LOG_NOTICE` | 継続 | 対応 counter_type のエントリが欠落（count=0 は書き込みスキップ） | 同上 |
| 6 | `STATE_DB` 接続失敗 (`DBConnector` / `Table` コンストラクタ例外) | 例外スロー | クラッシュ（orchagent 再起動） | 書き込みなし | `systemctl status swss` |

### SAI_STATUS_BUFFER_OVERFLOW の特殊処理

`sai_query_stats_capability()` が `SAI_STATUS_BUFFER_OVERFLOW` を返した場合、portsorch は必要なバッファを確保して **自動リトライ** する (portsorch.cpp:1883-1888, 1930-1934)。リトライ後も失敗した場合にのみ `SWSS_LOG_NOTICE` が出力される。リトライ自体は透過的に処理され、ユーザへの影響はない。

### DEBUG_COUNTER_CAPABILITIES のリソース枯渇警告

コードコメント (drop_counter.cpp:425-431) によると、プラットフォームの debug counter リソースは [ASIC](../../reference/glossary.md#term-asic) の他オブジェクト（[ACL](../../reference/glossary.md#term-acl) 等）とハードウェアリソースを共有する場合がある。`getSupportedDebugCounterAmounts()` が返す count は起動時以降に変化する可能性があるが、STATE_DB への再書き込みは行われない（コンストラクタ呼び出し時のスナップショットのみ）。

<!-- /failure -->

---

<!-- constants -->
## ハードコード定数 (Phase E)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-constants.md`

<!-- evidence: sonic-swss/orchagent/portsorch.cpp:421-435,1866-1879,
     sonic-swss/orchagent/debugcounterorch.cpp:357-358,
     sonic-swss/orchagent/debug_counter/debug_counter.h:27-30,
     sonic-swss/orchagent/debug_counter/drop_counter.cpp:17-18,86,
     sonic-swss-common/common/schema.h:438,528-529 -->

### STATE_DB テーブル名定数

| 定数名 | 値 | 定義箇所 |
|--------|-----|---------|
| `STATE_PORT_COUNTER_CAPABILITIES_NAME` | `"PORT_COUNTER_CAPABILITIES"` | `schema.h:529` |
| `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` | `"QUEUE_COUNTER_CAPABILITIES"` | `schema.h:528` |
| `STATE_DEBUG_COUNTER_CAPABILITIES_NAME` | `"DEBUG_COUNTER_CAPABILITIES"` | `schema.h:438` |

これら 3 定数は `sonic-swss-common/common/schema.h` の `#define` で一元管理される。portsorch / debugcounterorch は `Table()` コンストラクタにこれらを渡す。

### PORT_COUNTER_CAPABILITIES / QUEUE_COUNTER_CAPABILITIES の固定 key 名

[YANG](../../reference/glossary.md#term-yang) に未定義。`portsorch.cpp:1872-1879` 内ソースリテラルのみで管理される。

| key 名 | テーブル | 対応 SAI enum |
|--------|---------|--------------|
| `"WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` |
| `"WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER"` | `QUEUE_COUNTER_CAPABILITIES` | `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` |
| `"WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_GREEN_WRED_DROPPED_PACKETS` |
| `"WRED_ECN_PORT_WRED_YELLOW_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_YELLOW_WRED_DROPPED_PACKETS` |
| `"WRED_ECN_PORT_WRED_RED_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_RED_WRED_DROPPED_PACKETS` |
| `"WRED_ECN_PORT_WRED_TOTAL_DROP_COUNTER"` | `PORT_COUNTER_CAPABILITIES` | `SAI_PORT_STAT_WRED_DROPPED_PACKETS` |

フィールド名 `"isSupported"` / 値 `"true"` / `"false"` も YANG 未定義のソースリテラル (portsorch.cpp:1866-1869)。

### DEBUG_COUNTER_CAPABILITIES の固定定数

| 種別 | 定数 / リテラル | 値 | evidence |
|------|---------------|-----|---------|
| counter_type key | `PORT_INGRESS_DROPS` | `"PORT_INGRESS_DROPS"` | `debug_counter.h:27` |
| counter_type key | `PORT_EGRESS_DROPS` | `"PORT_EGRESS_DROPS"` | `debug_counter.h:28` |
| counter_type key | `SWITCH_INGRESS_DROPS` | `"SWITCH_INGRESS_DROPS"` | `debug_counter.h:29` |
| counter_type key | `SWITCH_EGRESS_DROPS` | `"SWITCH_EGRESS_DROPS"` | `debug_counter.h:30` |
| フィールド名 | `"count"` リテラル | `"count"` | `debugcounterorch.cpp:357` |
| フィールド名 | `"reasons"` リテラル | `"reasons"` | `debugcounterorch.cpp:358` |

### drop_counter.cpp の SAI 問い合わせバッファ定数

| 定数 | 値 | 用途 |
|-----|-----|------|
| `maxDropReasons` | `100` | `sai_query_attribute_enum_values_capability()` に渡す drop reason バッファサイズ上限。コードコメント "gives us plenty of space for both ingress and egress drop reasons" (drop_counter.cpp:84-86) |
| `INGRESS_DROP_REASON_PREFIX_LENGTH` | `19` | `"SAI_IN_DROP_REASON_"` の文字数。SAI enum 文字列からプレフィクスを除去し短縮 key を生成する際に使用 (drop_counter.cpp:17) |
| `EGRESS_DROP_REASON_PREFIX_LENGTH` | `20` | `"SAI_OUT_DROP_REASON_"` の文字数。同上 (drop_counter.cpp:18) |

!!! note "YANG 未定義の影響"
    上記 key 名・フィールド名はすべて YANG スキーマに定義されておらず、バリデーションなしでコードが直接 STATE_DB に書き込む。名称変更にはソースコードと参照側 (`portstat.py`、`dropconfig` 等) の両方の修正が必要。

<!-- /constants -->

---

<!-- side-effects -->
## 副作用 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-side.md`

<!-- evidence: sonic-swss/orchagent/portsorch.cpp:9476-9494,
     sonic-swss/orchagent/flexcounterorch.cpp:271-279,
     sonic-utilities/utilities_common/portstat.py:295-331 -->

これらの STATE_DB テーブルは orchagent コンストラクタが **SAI 問い合わせ結果を起動時 1 回限りで書き込む**ものであり、通常の [CONFIG_DB](../../reference/glossary.md#term-config_db) SET/DEL に連動する副作用とは性質が異なる。書き込み後の値を consumer が参照した際に下流で何が変化するかを以下に示す。

### 1. COUNTERS_DB ポーリング対象の変化（portstat.py）

`portstat.py` は起動時（またはカウンタポーリング実行前）に `PORT_COUNTER_CAPABILITIES` を参照し、WRED カウンタを `counter_bucket_dict` に含めるか除外するかを決定する[^10]。

| `isSupported` の値 | portstat.py の挙動 | portstat CLI 表示 |
|-------------------|------------------|-----------------|
| `"true"` | `SAI_PORT_STAT_*_WRED_*` を [COUNTERS_DB](../../reference/glossary.md#term-counters_db) ポーリング対象に保持 | WRED カラムに数値が表示される |
| `"false"` または キー不存在 | 対応 SAI カウンタを `counter_bucket_dict` から削除 | WRED カラムが `N/A` になる |

!!! warning "WRED カウンタ N/A の真因"
    `portstat` で WRED カラムが `N/A` になる場合、原因は 2 つある。(1) プラットフォームが SAI WRED 統計を未サポート（`isSupported="false"` が正常動作）、(2) orchagent 起動直後の false 初期化ウィンドウ中に portstat が実行された（transient 現象）。`sonic-db-cli STATE_DB hgetall 'PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER'` で判別できる。

### 2. DEBUG_COUNTER_CAPABILITIES → show debug-counter capabilities 出力

`DEBUG_COUNTER_CAPABILITIES` テーブルの有無が `show debug-counter capabilities` コマンドの出力を直接決定する。

| テーブル状態 | show debug-counter capabilities 出力 | 後続 CLI 操作への影響 |
|------------|-------------------------------------|-------------------|
| エントリあり（`count` ≥ 1 かつ `reasons` に値） | counter_type ごとの件数・drop reason 一覧 | `config debug-counter install <type>` が意味を持つ |
| テーブルが空（プラットフォーム非サポート） | 出力が空 | debug counter のインストールは SAI レベルで失敗する可能性が高い |

### 3. FLEX_COUNTER_DB（WRED ポーリング）への間接的非影響

`FlexCounterOrch` が `FLEX_COUNTER_TABLE|WRED_ECN_PORT` を `enable` にすると `gPortsOrch->generateWredPortCounterMap()` が呼ばれ、全 PHY ポートに `wred_port_stat_ids` を `FLEX_COUNTER_DB` に登録する（flexcounterorch.cpp:273, portsorch.cpp:9491）。この処理は `PORT_COUNTER_CAPABILITIES` テーブルを**参照しない**。

結果として SAI 側の WRED カウンタ収集と portstat の N/A 表示が**独立して動作**する可能性がある:

| 状態 | SAI ポーリング | portstat 表示 |
|------|-------------|-------------|
| SAI サポートあり（`isSupported="true"`） | [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) 登録あり → COUNTERS_DB に値 | 数値表示 |
| SAI サポートなし（`isSupported="false"`） | [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) 登録あり（能力チェックなし）→ COUNTERS_DB に 0 または欠損 | N/A 表示 |

### 副作用サマリ

| 副作用 | 対象コンポーネント | トリガー | 可逆性 |
|--------|----------------|---------|--------|
| WRED カウンタポーリング対象の追加/除外 | portstat.py / COUNTERS_DB | 起動時 STATE_DB 書込み後の portstat 実行 | orchagent 再起動で再評価 |
| show debug-counter capabilities 出力の有無 | dropconfig CLI | 同上 | orchagent 再起動で再評価 |
| portstat WRED カラム N/A | portstat CLI 表示 | `isSupported="false"` | プラットフォーム依存（変更不可） |

<!-- /side-effects -->

---

<!-- pubsub -->
## 通信メカニズム (Phase G)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-pubsub.md`

これらの STATE_DB テーブルは CONFIG_DB テーブルとは根本的に異なる通信パターンを持つ。書き込み側は `Table::set()` による **スナップショット書き込み** (起動時 1 回限り) であり、読み取り側は `db.get()` / `db.get_all()` による **on-demand polling** である。keyspace 通知や `SubscriberStateTable` は使用しない。

### 書き込みパス（Producer 側）

| 要素 | 詳細 |
|------|------|
| 書き込みクラス | `Table` (生 `HSET`。`ProducerStateTable` / `NotificationProducer` は不使用) |
| 書き込みタイミング | orchagent コンストラクタ呼び出し時の **1 回限り** |
| トリガー | `PortsOrch::initCounterCapabilities(gSwitchId)` (portsorch.cpp:1107) / `DebugCounterOrch::publishDropCounterCapabilities()` (debugcounterorch.cpp:37) |
| [APPL_DB](../../reference/glossary.md#term-appl_db) 中継 | なし |
| 再書き込み | orchagent 再起動時のみ（オンライン変更不可） |

### 読み取りパス（Consumer 側）

keyspace 通知を購読する実装は [SONiC](../../reference/glossary.md#term-sonic) ソース内に存在しない。CLI ツールが実行時に直接 HGET/HGETALL でスナップショット取得する。

| 読み取り元 | 対象テーブル | [Redis](../../reference/glossary.md#term-redis) 操作 | コード |
|-----------|------------|-----------|--------|
| `portstat.py` | `PORT_COUNTER_CAPABILITIES\|<key>` | `db.get(STATE_DB, key, "isSupported")` | portstat.py:299-311 |
| `dropconfig` | `DEBUG_COUNTER_CAPABILITIES\|*` | `db.keys(STATE_DB, ...)` + `db.get_all()` | dropconfig:423-431 |
| `dropconfig` (個別) | `DEBUG_COUNTER_CAPABILITIES\|<counter_type>` | `db.get_all(STATE_DB, key)` | dropconfig:444-455 |

`QUEUE_COUNTER_CAPABILITIES` を参照する CLI ツールは [SONiC](../../reference/glossary.md#term-sonic) ソース内に確認できない（orchagent が書くが読者不在）。

### データフロー

```
SAI / ASIC
  │ sai_query_stats_capability() / sai_query_attribute_enum_values_capability()
  ▼
orchagent (PortsOrch::initCounterCapabilities / DebugCounterOrch::publishDropCounterCapabilities)
  │ Table::set() → Redis HSET（起動時 1 回）
  ▼
STATE_DB
  ├─ PORT_COUNTER_CAPABILITIES|<key>        {isSupported: "true"/"false"}
  ├─ QUEUE_COUNTER_CAPABILITIES|<key>       {isSupported: "true"/"false"}
  └─ DEBUG_COUNTER_CAPABILITIES|<type>      {count: "<N>", reasons: "[...]"}

読み取り経路（on-demand polling、keyspace 通知なし）:
  portstat.py → db.get(STATE_DB, "PORT_COUNTER_CAPABILITIES|...", "isSupported")
  dropconfig  → db.get_all(STATE_DB, "DEBUG_COUNTER_CAPABILITIES|...")
```

<!-- /pubsub -->

---

<!-- platform -->
## プラットフォーム / SAI Capability 差異 (Phase H)

> 調査証跡: `meta/_intermediate/cdb-flow/counters-state-platform.md`

これらの STATE_DB テーブルの内容は CONFIG_DB 設定ではなく **[ASIC](../../reference/glossary.md#term-asic) が SAI を通じて公開する能力** によって決まる。プラットフォームによって書き込まれる値が根本的に異なる。

### WRED カウンタ能力 — ASIC 依存

`PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` の `isSupported` は `sai_query_stats_capability()` の返却 enum リストに対応する統計が含まれるかどうかで決まる[^3][^4]。

| プラットフォーム状況 | 挙動 |
|---------------------|------|
| WRED をハードウェア実装した [ASIC](../../reference/glossary.md#term-asic) (Broadcom Tomahawk 系・Mellanox Spectrum 系等) | 対応する WRED 統計 enum が返却 → 該当フィールドが `isSupported="true"` に更新 |
| WRED サポートなし ASIC / [VS](../../reference/glossary.md#term-vs) (virtual switch) | `SAI_STATUS_SUCCESS` でも対象 enum が含まれない → 全フィールドが `"false"` のまま残る |
| SAI query 自体が失敗 (`SAI_STATUS_NOT_IMPLEMENTED` 等) | `SWSS_LOG_NOTICE` を出力して続行。全フィールドが初期値 `"false"` のまま |

`sai_query_stats_capability()` は 2 段階クエリを採用する: 最初に `count=0 / list=nullptr` で呼び出し、`SAI_STATUS_BUFFER_OVERFLOW` が返った場合に返却 count 分のバッファを確保して再クエリ (portsorch.cpp:1883-1895, 1930-1942)。`BUFFER_OVERFLOW` でも `SUCCESS` でもない戻り値 (`NOT_IMPLEMENTED` 等) の場合は再クエリせず全フィールドが `"false"` のまま。

### DEBUG_COUNTER_CAPABILITIES — debug counter 未サポート ASIC

`sai_query_attribute_enum_values_capability(SAI_OBJECT_TYPE_DEBUG_COUNTER, ...)` が失敗した場合、`getSupportedDropReasons()` および `getSupportedCounterTypes()` が空集合を返す。この場合 `DEBUG_COUNTER_CAPABILITIES` テーブルにエントリが一切書き込まれない (drop_counter.cpp:305-315, 376-391)。

```
getSupportedDropReasons() の失敗パス:
  sai_query_attribute_enum_values_capability(SAI_OBJECT_TYPE_DEBUG_COUNTER,
                                             SAI_DEBUG_COUNTER_ATTR_IN_DROP_REASON_LIST) != SUCCESS
  → SWSS_LOG_NOTICE("This device does not support querying drop reasons")
  → return {}  ⇒ DEBUG_COUNTER_CAPABILITIES 書き込みゼロ

getSupportedCounterTypes() の失敗パス:
  sai_query_attribute_enum_values_capability(SAI_OBJECT_TYPE_DEBUG_COUNTER,
                                             SAI_DEBUG_COUNTER_ATTR_TYPE) != SUCCESS
  → SWSS_LOG_NOTICE("This device does not support querying drop counters")
  → return {}  ⇒ DEBUG_COUNTER_CAPABILITIES 書き込みゼロ
```

| プラットフォーム状況 | DEBUG_COUNTER_CAPABILITIES |
|---------------------|---------------------------|
| SAI debug counter サポートあり ASIC | counter_type ごとにエントリが書き込まれる (count, reasons フィールド) |
| SAI debug counter 未サポート ASIC | テーブルが空のまま。`show debug-counter capabilities` の出力も空 |
| [VS](../../reference/glossary.md#term-vs) (virtual switch) | SAI stub 実装により通常 debug counter サポートなし → テーブル空 |

### portstat.py の列数とプラットフォームの関係

`portstat.py` は起動時に `PORT_COUNTER_CAPABILITIES` を参照し、`isSupported != "true"` のカウンタを `counter_bucket_dict` から除外する[^10]。WRED をサポートしない ASIC では `portstat` の出力から WRED 関連列が N/A として表示される（または非表示）。これは設定変更では制御できない ASIC 固有の制約である。

<!-- /platform -->

---

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB FLEX_COUNTER_TABLE](flex-counter-table.md) — ポーリング有効化・間隔設定
- [COUNTERS_DB PORT カウンタ](counters-port.md) — ポート統計の実体
- [COUNTERS_DB QUEUE カウンタ](counters-queue.md) — キュー統計の実体
- [CONFIG_DB DEBUG_COUNTER](debug-counter.md) — デバッグカウンタ設定
- CLI: `show interface counters` (`portstat`)、`show debug-counter capabilities`

<!-- ref-triangle:end -->

[^1]: schema.h:438,528,529 で定数定義。`STATE_PORT_COUNTER_CAPABILITIES_NAME = "PORT_COUNTER_CAPABILITIES"`、`STATE_QUEUE_COUNTER_CAPABILITIES_NAME = "QUEUE_COUNTER_CAPABILITIES"`、`STATE_DEBUG_COUNTER_CAPABILITIES_NAME = "DEBUG_COUNTER_CAPABILITIES"`
[^2]: portsorch.cpp:1868-1879。`fieldValuesFalse` に `("isSupported","false")` を格納し全 4 フィールドに書き込む
[^3]: portsorch.cpp:1936-1964。`SAI_STATUS_SUCCESS` の場合のみ更新。失敗時は SWSS_LOG_NOTICE で通知
[^4]: portsorch.cpp:1881-1918。`SAI_STATUS_SUCCESS` の場合のみ更新
[^5]: debugcounterorch.cpp:315-363。`publishDropCounterCapabilities()` はコンストラクタで呼ばれる (debugcounterorch.cpp:37)
[^6]: portstat.py:314-329。`is_wred_stats_reqd` が False または `isSupported != "true"` の場合に除外
[^7]: portsorch.cpp:1850-1968。`initCounterCapabilities()` は portsorch コンストラクタ末尾 (portsorch.cpp:1107) で呼ばれる
[^8]: orchdaemon.cpp:232 (PortsOrch), orchdaemon.cpp:452 (DebugCounterOrch)。debugcounterorch.cpp:37 で `publishDropCounterCapabilities()` が `gPortsOrch->attach(this)` より前に実行される
[^9]: portsorch.cpp:9102-9129 (`generatePortCounterMap`)。FLEX_COUNTER_DB への登録のみで STATE_DB への読み書きなし
[^10]: portstat.py:295-331。`wred_green_pkt_stat_capable` 等のグローバル変数に `STATE_DB HGET` 結果を格納し、`!= "true"` の場合に `counter_bucket_dict` から該当 SAI カウンタを削除する

<!-- glossary-links-injected: 0af8863862be -->
