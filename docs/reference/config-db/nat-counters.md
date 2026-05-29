---
title: COUNTERS_DB NAT カウンタテーブル群
description: "COUNTERS_DB:COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT / COUNTERS_GLOBAL_NAT — orchagent/NatOrch が SAI から定期取得するパケット・バイト数カウンタおよびグローバル統計テーブルの定義。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/natorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - NAT_GLOBAL
    - NAT_POOL
    - NAT_BINDINGS
  cli:
    - show nat statistics
  yang:
    - sonic-nat
---

# COUNTERS_DB NAT カウンタテーブル群

## 概要

[NAT](../../reference/glossary.md#term-nat) 機能の実行時カウンタは `COUNTERS_DB` 上の 5 つのテーブルに書き込まれる。`orchagent/NatOrch` が [SAI](../../reference/glossary.md#term-sai) [NAT](../../reference/glossary.md#term-nat) API から 5 秒周期でパケット数・バイト数を取得し更新する。`show nat statistics` はこれらのテーブルを読み取る。

| テーブル | キー形式 | 用途 |
|---------|---------|------|
| `COUNTERS_NAT` | `<external_ip>` | 単体 [NAT](../../reference/glossary.md#term-nat) (SNAT/DNAT) エントリのカウンタ |
| `COUNTERS_NAPT` | `<proto>:<ip>:<port>` | 単体 NAPT エントリのカウンタ |
| `COUNTERS_TWICE_NAT` | `<src_ip>:<dst_ip>` | Twice NAT エントリのカウンタ |
| `COUNTERS_TWICE_NAPT` | `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` | Twice NAPT エントリのカウンタ |
| `COUNTERS_GLOBAL_NAT` | `Values` (固定) | グローバル統計・設定サマリ |

## key 構造

```text
COUNTERS_DB:COUNTERS_NAT|<external_ip>
COUNTERS_DB:COUNTERS_NAPT|<proto>:<ip>:<port>
COUNTERS_DB:COUNTERS_TWICE_NAT|<src_ip>:<dst_ip>
COUNTERS_DB:COUNTERS_TWICE_NAPT|<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>
COUNTERS_DB:COUNTERS_GLOBAL_NAT|Values
```

## 主要フィールド

### COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT

全エントリカウンタテーブルは同一フィールド構成を持つ。

| フィールド | 型 | 初期値 | 説明 |
|-----------|-----|--------|------|
| `NAT_TRANSLATIONS_PKTS` | uint64 (文字列) | `"0"` | [SAI](../../reference/glossary.md#term-sai) から取得したパケット数。エントリ登録直後に `0` で初期化される |
| `NAT_TRANSLATIONS_BYTES` | uint64 (文字列) | `"0"` | [SAI](../../reference/glossary.md#term-sai) から取得したバイト数。エントリ登録直後に `0` で初期化される |

- **書き込み元**: `NatOrch::updateNatCounters()` / `updateNaptCounters()` / `updateTwiceNatCounters()` / `updateTwiceNaptCounters()` (`natorch.cpp:4049-4135`)
- **削除**: エントリ削除時に `deleteNatCounters()` 等で対応エントリを削除
- **更新周期**: `NAT_HITBIT_N_CNTRS_QUERY_PERIOD = 5` 秒[^1]

### COUNTERS_GLOBAL_NAT|Values

キー: `"Values"` (固定)

#### 起動時のみ書き込まれるフィールド

NatOrch コンストラクタ初回実行時に一度だけ書き込まれる。その後の [CONFIG_DB](../../reference/glossary.md#term-config_db) 変更では更新されない。

| フィールド | 型 | 初期値 | 説明 |
|-----------|-----|--------|------|
| `MAX_NAT_ENTRIES` | uint32 (文字列) | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 取得値 (失敗時 `"0"`) | プラットフォームが許容する最大 SNAT エントリ数 |
| `TIMEOUT` | uint32 (文字列) | `"600"` | 非 TCP/UDP NAT エントリのアイドルタイムアウト秒 |
| `UDP_TIMEOUT` | uint32 (文字列) | `"300"` | UDP NAT エントリのアイドルタイムアウト秒 |
| `TCP_TIMEOUT` | uint32 (文字列) | `"86400"` | TCP NAT エントリのアイドルタイムアウト秒 (1 日) |

#### エントリ数フィールド (実行時更新)

| フィールド | 型 | 初期値 | 更新タイミング |
|-----------|-----|--------|---------------|
| `STATIC_NAT_ENTRIES` | int (文字列) | `"0"` | static NAT エントリ追加/削除時 |
| `STATIC_NAPT_ENTRIES` | int (文字列) | `"0"` | static NAPT エントリ追加/削除時 |
| `STATIC_TWICE_NAT_ENTRIES` | int (文字列) | `"0"` | static Twice NAT エントリ追加/削除時 |
| `STATIC_TWICE_NAPT_ENTRIES` | int (文字列) | `"0"` | static Twice NAPT エントリ追加/削除時 |
| `DYNAMIC_NAT_ENTRIES` | int (文字列) | `"0"` | dynamic NAT エントリ追加/削除時 |
| `DYNAMIC_NAPT_ENTRIES` | int (文字列) | `"0"` | dynamic NAPT エントリ追加/削除時 |
| `DYNAMIC_TWICE_NAT_ENTRIES` | int (文字列) | `"0"` | dynamic Twice NAT エントリ追加/削除時 |
| `DYNAMIC_TWICE_NAPT_ENTRIES` | int (文字列) | `"0"` | dynamic Twice NAPT エントリ追加/削除時 |
| `SNAT_ENTRIES` | int (文字列) | `"0"` | SNAT エントリ (static/dynamic 合算) 追加/削除時 |
| `DNAT_ENTRIES` | int (文字列) | `"0"` | DNAT エントリ (static/dynamic 合算) 追加/削除時 |

## 制約

- COUNTERS カウンタは `NAT_HITBIT_N_CNTRS_QUERY_PERIOD = 5` 秒周期で更新される。リアルタイム値ではない。
- `MAX_NAT_ENTRIES = 0` の場合、`gIsNatSupported = false` となり NAT 機能全体が無効化される。
- `COUNTERS_GLOBAL_NAT|Values` の `TIMEOUT` / `TCP_TIMEOUT` / `UDP_TIMEOUT` は起動時の初期値のみ書き込まれ、[CONFIG_DB](../../reference/glossary.md#term-config_db) 変更では更新されない。

## 購読者

- `orchagent/NatOrch`: SAI NAT カウンタを 5 秒周期でポーリングし各 `COUNTERS_NAT*` テーブルを更新する[^1]。
- `show nat statistics`: `COUNTERS_NAT`・`COUNTERS_NAPT`・`COUNTERS_GLOBAL_NAT` を読み取り統計を表示する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `NAT_GLOBAL`、`NAT_POOL`、`NAT_BINDINGS`
- 関連 CLI: `show nat statistics`、`show nat translations`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-nat`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`NAT_GLOBAL / NAT_POOL`](nat.md)
- CONFIG_DB: [`NAT_BINDINGS`](nat-bindings.md)
- CONFIG_DB: [`NAT_RESTORE_TABLE / STATE_DB`](nat-state.md)
- CLI: [`config nat`](../cli/config-nat.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: NAT カウンタ実装: `natorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/natorch.cpp>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: NAT / DHCP Relay / Time-DNS Services](../../topics/16-nat-dhcp-dns/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# NAT カウンタ統計 (CLIで確認)
show nat statistics

# COUNTERS_DB を直接参照
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_GLOBAL_NAT|Values'
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_NAT|<external_ip>'
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_NAPT|TCP:10.0.0.1:1024'

# すべての NAT カウンタキーを一覧表示
sonic-db-cli COUNTERS_DB keys 'COUNTERS_NAT*'
```

### MAX_NAT_ENTRIES=0 の対処

`COUNTERS_GLOBAL_NAT|Values` の `MAX_NAT_ENTRIES` が `"0"` の場合、プラットフォームが NAT をハードウェア的にサポートしていない。`gIsNatSupported=false` が設定され、CONFIG_DB に `admin_mode=enabled` を設定しても NAT 機能は動作しない。

### カウンタリセット

`sonic-clear nat statistics` でカウンタをリセットできる。内部では `FLUSHNATSTATISTICS` 通知を [APPL_DB](../../reference/glossary.md#term-appl_db) に送信し、`NatOrch` が SAI API でカウンタをクリアする。
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::NatOrch() / updateNatCounters / checkIfNatEntryIsActive -->

- **`MAX_NAT_ENTRIES=0` → NAT 無効化**: NatOrch コンストラクタで `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 取得が失敗または 0 → `maxAllowedSNatEntries=0` のまま書き込み → `gIsNatSupported=false` → `enableNatFeature()` 冒頭で即 return (`natorch.cpp:2541-2544`)。
- **TIMEOUT 系フィールドの静止**: `COUNTERS_GLOBAL_NAT|Values` の `TIMEOUT` / `TCP_TIMEOUT` / `UDP_TIMEOUT` は NatOrch 起動時の一度のみ書き込まれる。その後 `config nat set timeout <N>` 等で CONFIG_DB を変更しても [COUNTERS_DB](../../reference/glossary.md#term-counters_db) には反映されない。実際の運用タイムアウトは `show nat config globalvalues` で確認すること。
- **Static エントリのカウンタ更新**: `entry_type="static"` のエントリもカウンタ取得対象。`checkIfNatEntryIsActive()` が static エントリを常に `active=1` として扱うためエージアウトされず、カウンタは継続して更新される (`natorch.cpp:4160-4163`)。
- **カウンタ更新の非同期性**: `NAT_TRANSLATIONS_PKTS` / `NAT_TRANSLATIONS_BYTES` は最大 5 秒遅延する。フロー完了直後に参照してもゼロのままの場合がある。

<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch コンストラクタ / enableNatFeature -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `COUNTERS_GLOBAL_NAT\|Values.MAX_NAT_ENTRIES` | `"0"` | `gIsNatSupported=false` → NAT 機能全体が無効化される |
| `COUNTERS_GLOBAL_NAT\|Values.MAX_NAT_ENTRIES` | `"N"` (N>0) | NAT エントリが最大 N 件まで SAI に登録可能 |
| `COUNTERS_NAT\|<ip>.NAT_TRANSLATIONS_PKTS` | `"0"` | エントリ登録直後または統計クリア直後の状態 |
| `COUNTERS_NAT\|<ip>.NAT_TRANSLATIONS_PKTS` | `"N"` (N>0) | フォワードされたパケット数 (最大 5 秒遅延) |
| `COUNTERS_GLOBAL_NAT\|Values.SNAT_ENTRIES` | `"N"` | 現在 SAI に登録済みの SNAT エントリ数 |
| `COUNTERS_GLOBAL_NAT\|Values.DNAT_ENTRIES` | `"N"` | 現在 SAI に登録済みの DNAT エントリ数 |

<!-- /value-behavior -->

<!-- cross-refs -->
## 暗黙参照テーブル

`COUNTERS_DB` NAT カウンタテーブル群は `NatOrch` が**書き手専用 (producer only)** として書き込む。カウンタエントリの生成・更新・削除は以下の CONFIG_DB / [APPL_DB](../../reference/glossary.md#term-appl_db) / SAI リソースへの依存によって決まる。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `NAT_GLOBAL_TABLE\|Values.admin_mode` ([APPL_DB](../../reference/glossary.md#term-appl_db)) | トリガ：`"enabled"` 時に `enableNatFeature()` → SAI 一括登録 → カウンタ初期化 | 常時。`admin_mode="disabled"` の間は `COUNTERS_NAT*` エントリが存在しない | `natorch.cpp:2534-2582` (`enableNatFeature`), `natorch.cpp:2617-2680` (`doNatGlobalTableTask`) |
| `APP_NAT_TABLE\|<global_ip>` / `APP_NAPT_TABLE\|<proto>:<ip>:<port>` (APPL_DB) | SET → `addHwSnatEntry()` / `addHwDnatEntry()` 成功 → `updateNatCounters(…,0,0)` | SAI 登録成功時のみカウンタエントリ生成 | `natorch.cpp:789` (`addSnatEntry`), `natorch.cpp:873` (`addNaptEntry`), `natorch.cpp:4049-4061` (`updateNatCounters`) |
| `APP_NAT_TWICE_TABLE\|<src_ip>:<dst_ip>` / `APP_NAPT_TWICE_TABLE\|…` (APPL_DB) | SET → `addHwTwiceNatEntry()` 成功 → `updateTwiceNatCounters(…,0,0)` | SAI 登録成功時のみ `COUNTERS_TWICE_NAT*` エントリ生成 | `natorch.cpp:1343-1430` (`addHwTwiceNatEntry`), `natorch.cpp:4108-4135` (`updateTwiceNatCounters`) |
| `FLUSHNATSTATISTICS` 通知 (APPL_DB) | 受信 → SAI `reset_nat_entry_attribute` → カウンタ 0 リセット | `sonic-clear nat statistics` 発行時 | `natorch.cpp:3271-3303` (`clearCounters`), コンストラクタ `NotificationConsumer("FLUSHNATSTATISTICS")` |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` | SAI クエリ → `MAX_NAT_ENTRIES` 書込み | NatOrch コンストラクタで 1 回のみ。失敗時は `"0"` → `gIsNatSupported=false` | `natorch.cpp:115-130` |
| `SAI NAT カウンタ API` (`get_nat_entry_attribute`) | 5 秒周期タイマ → `queryCounters()` → COUNTERS_NAT* 更新 | `admin_mode="enabled"` かつ タイマ起動中 | `natorch.cpp:3118-3177` (`queryCounters`), `natorch.cpp:3095-3117` (`doTask(SelectableTimer)`) |
| `RouteOrch` (DNAT 用 NH 解決) | `attach/detach` コールバック → DNAT エントリ追加可否 | NH が解決されるまで `addHwDnatEntry()` は呼ばれず、カウンタも不在 | `natorch.cpp:155-202` (`update`), `natorch.cpp:390-432` (`addDnatToNhCache`) |

!!! note "COUNTERS_DB NAT テーブルは「書き出し専用」のランタイムステータスレジスタ"
    `NatOrch` 以外の書き手は存在しない。`show nat statistics` / `show nat translations` は読み手のみ。
    `COUNTERS_GLOBAL_NAT|Values` のエントリ数フィールド (`SNAT_ENTRIES` 等) は `addHwSnatEntry()` / `removeHwSnatEntry()` 成功のたびにリアルタイム更新される (`natorch.cpp:4574`)。

<!-- /cross-refs -->

<!-- defaults -->
## フィールド暗黙デフォルト (コード由来)

[YANG](../../reference/glossary.md#term-yang) 定義外の [COUNTERS_DB](../../reference/glossary.md#term-counters_db) 実行時テーブルのためコード hardcode 値のみ。

| フィールド | テーブル | 初期値 | ソース |
|-----------|---------|--------|--------|
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_NAT` / `COUNTERS_NAPT` 各エントリ | `"0"` | `natorch.cpp:789,873` (エントリ登録直後の `update*Counters(…,0,0)` 呼び出し) |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_NAT` / `COUNTERS_NAPT` 各エントリ | `"0"` | `natorch.cpp:789,873` |
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` 各エントリ | `"0"` | `natorch.cpp` 各 `addTwice*Entry` 直後の `updateTwice*Counters(…,0,0)` |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` 各エントリ | `"0"` | 同上 |
| `MAX_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 値 (失敗時 `"0"`) | `natorch.cpp:127` |
| `TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"600"` | `natorch.cpp:128` (コンストラクタ `timeout=600`) |
| `UDP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"300"` | `natorch.cpp:129` (コンストラクタ `udp_timeout=300`) |
| `TCP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"86400"` | `natorch.cpp:130` (コンストラクタ `tcp_timeout=86400`) |
| `STATIC_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4486` (初期 `totalStaticNatEntries=0`) |
| `STATIC_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4497` |
| `STATIC_TWICE_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4508` |
| `STATIC_TWICE_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4519` |
| `DYNAMIC_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4530` |
| `DYNAMIC_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4541` |
| `DYNAMIC_TWICE_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4552` |
| `DYNAMIC_TWICE_NAPT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4563` |
| `SNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4574` (初期 `totalSnatEntries=0`) |
| `DNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:4585` (初期 `totalDnatEntries=0`) |

### COUNTERS_GLOBAL_NAT の TIMEOUT フィールドと CONFIG_DB の乖離

`COUNTERS_GLOBAL_NAT|Values` の `TIMEOUT` / `TCP_TIMEOUT` / `UDP_TIMEOUT` フィールドは NatOrch 起動時に一度だけ書き込まれ、その後 CONFIG_DB の `NAT_GLOBAL.nat_timeout` が変更されても**更新されない**。実際のタイムアウト値は `show nat config globalvalues` で確認すること。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存

`NatOrch` が [COUNTERS_DB](../../reference/glossary.md#term-counters_db) の 5 つのカウンタテーブルを書き込む際の順序依存を示す。書き込みは「コンストラクタ初期化 → エントリ追加時のゼロ初期化 → タイマー周期ポーリング」という 3 段階で行われ、各段階の前提条件が成立しない場合にカウンタが更新されない状態が発生する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | コンストラクタ SAI クエリ → `COUNTERS_GLOBAL_NAT\|Values` 初期化 | 強制先行（`enableNatFeature()` / エントリ追加より前） | 起動直後に `MAX_NAT_ENTRIES` が確定。SAI クエリ失敗時は `"0"` → NAT 機能全体が無効化 |
| 2 | `gIsNatSupported=false` → カウンタ更新タイマー不起動 | **ブロック**（永続） | `enableNatFeature()` が即 return → `m_natQueryTimer->start()` 未到達 → `COUNTERS_NAT*` は 0 のまま継続 |
| 3 | `NAT_GLOBAL.admin_mode=enabled` → タイマー起動 → 周期更新開始 | 強制先行（admin_mode SET が先） | タイマー起動前に追加済みのエントリは次のタイマー周期 (最大 5 秒後) まで非ゼロ値を持たない |
| 4 | SAI エントリ作成成功 → `update*Counters(0,0)` (ゼロ初期化) → 5 秒後に実カウンタ反映 | **2 段階**（即時 0 → 遅延更新） | エントリ追加直後は常に `PKTs=0, BYTES=0`。非ゼロ値は最初の `queryCounters()` 呼び出し後に出現 |
| 5 | SAI エントリ削除 → `delete*Counters()` (即時キー削除) | 即時 | 削除後は該当 COUNTERS_DB キーが消滅。タイマー周期との競合は「空振り」のみで実害なし |
| 6 | `APP_NAT_GLOBAL_TABLE_NAME` の処理優先度が最低 (50) | 後処理 | エントリ系テーブル (51–55) が先にキューを消化し、admin_mode は最後に評価される |

### 主要な制約詳細

**コンストラクタ → COUNTERS_GLOBAL_NAT の強制先行 (依存 #1)**: `NatOrch::NatOrch()` 末尾で `sai_switch_api->get_switch_attribute(SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY)` を実行し、結果を `maxAllowedSNatEntries` に格納した後 `m_countersGlobalNatTable.set("Values", values)` で `MAX_NAT_ENTRIES` / `TIMEOUT` / `UDP_TIMEOUT` / `TCP_TIMEOUT` を一括書き込む。この書き込みは [orchagent](../../reference/glossary.md#term-orchagent) 初期化フェーズで 1 回だけ行われ、以後の CONFIG_DB 変更では更新されない (`natorch.cpp:111-134`)。

**NAT 未サポートプラットフォームでのカウンタ停止 (依存 #2)**: `gIsNatSupported` は `orchagent/main.cpp:936-948` で SAI switch 属性 `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を照会し、戻り値が 0 より大きい場合のみ `true` に設定されるグローバル変数。`false` の場合 `enableNatFeature()` が冒頭で return し (`natorch.cpp:2541-2543`)、タイマーが起動しない。結果として `COUNTERS_NAT` 等のテーブルはエントリ追加時の `update*Counters(0,0)` のみで書かれ、以後 5 秒周期更新を受けない。

**2 段階カウンタ出現 (依存 #4)**: `addNatEntry()` が SAI `create_nat_entry` 成功後に `updateNatCounters(ip_address, 0, 0)` を呼んでカウンタキーを `0,0` で作成する (`natorch.cpp:789`)。`addNaptEntry()` も同様 (`natorch.cpp:873`)。実際のパケット・バイト数は次の `queryCounters()` → `getNatCounters()` → `update*Counters(pkts, bytes)` が実行されて初めて書き込まれる (最大 5 秒後)。監視ツールがエントリ追加直後にカウンタを読んだ場合、常に `0` を観測する。

**タイマー多重化 (依存 #3 補足)**: `doTask(SelectableTimer)` は 2 種のタイマーを区別する。`m_natQueryTimer` (5 秒周期) が `queryHitBits()` + `queryCounters()` を駆動し、`m_natTimeoutTimer` (1 日周期) が conntrack エントリ更新を行う。カウンタ更新に関係するのは前者のみ (`natorch.cpp:3099-3122`)。

<!-- /ordering -->

<!-- failure -->
## 失敗挙動

`NatOrch` が COUNTERS_DB の NAT カウンタテーブルを書き込む際の失敗経路を示す。基本パターンは「SAI エントリ登録失敗 → カウンタエントリ不在」「SAI カウンタ取得失敗 → 0 上書き」の 2 種類。

### COUNTERS_NAT / COUNTERS_NAPT / COUNTERS_TWICE_NAT / COUNTERS_TWICE_NAPT 失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | 書き込み結果 |
|---|---|---|---|
| SAI `create_nat_entry` 失敗 | `addHwDnatEntry()` / `addHwSnatEntry()` 等 — `natorch.cpp:774-783, 856-865, 1307-1316` | `parseHandleSaiStatusFailure()` で return。`updateNatCounters()` 未到達 | 該当キーが COUNTERS_DB に存在しない |
| 5 秒ポーリング中に SAI `get_nat_entry_attribute` 失敗 | `getNatCounters()` — `natorch.cpp:3546-3574` | `nat_translations_pkts=0, bytes=0` のまま `updateNatCounters(0,0)` を呼ぶ | `COUNTERS_NAT\|<ip>.NAT_TRANSLATIONS_PKTS/BYTES` が `"0"` に上書きされ前回値が失われる |
| 5 秒ポーリング中に Twice NAT SAI クエリ失敗 | `getTwiceNatCounters()` — `natorch.cpp:3609-3623` | 同上、`updateTwiceNatCounters(0,0)` を呼ぶ | `COUNTERS_TWICE_NAT*\|<key>` が `"0"` に上書き |
| `addedToHw=false` (NH 未解決 or NAT 無効) | `getNatCounters()` 先頭ガード — `natorch.cpp:3517-3521` | SAI クエリをスキップ。`updateNatCounters()` 未呼び出し | COUNTERS_DB の値は前回値 (またはゼロ初期化値) のまま |
| `clock_gettime` 失敗 | `queryCounters()` — `natorch.cpp:3125-3128` | 即 return。当該周期のカウンタ更新全スキップ | COUNTERS_DB 全エントリが更新されない (次周期で自動リトライ) |
| `FLUSHNATSTATISTICS` 受信後の SAI reset 失敗 | `clearCounters()` — `natorch.cpp:3271-3303` | `SWSS_LOG_ERROR` 出力のみ、処理継続 | COUNTERS_DB の値は前回値のまま (0 リセット失敗) |

### COUNTERS_GLOBAL_NAT 失敗パターン

| 失敗ケース | 発生箇所 | 挙動 | 書き込み結果 |
|---|---|---|---|
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` クエリ失敗 | NatOrch コンストラクタ — `natorch.cpp:115-135` | `maxAllowedSNatEntries=0` のまま `COUNTERS_GLOBAL_NAT\|Values` を書き込み | `MAX_NAT_ENTRIES="0"` → `gIsNatSupported=false` → NAT 機能全体が無効化 |
| `gIsNatSupported=false` → タイマー未起動 | `enableNatFeature()` — `natorch.cpp:2541-2544` | `m_natQueryTimer->start()` 未到達 → `queryCounters()` が永遠に呼ばれない | `COUNTERS_NAT*` エントリのカウンタは 0 初期化値のまま更新されない |

### 主要な制約詳細

**SAI カウンタ取得失敗時の 0 上書き問題 (ポーリング失敗)**: `getNatCounters()` (`natorch.cpp:3507`) は `nat_translations_pkts / bytes` を 0 で初期化し、SAI `get_nat_entry_attribute` が失敗した場合はこの 0 のまま `updateNatCounters(ipAddr, 0, 0)` を呼ぶ (`natorch.cpp:3573-3574`)。これはカウンタが前回値ではなく `"0"` に上書きされることを意味する。SAI 一時障害（[ASIC](../../reference/glossary.md#term-asic) リセット中など）でポーリングが 1 回失敗するだけで統計が消える。`show nat statistics` で突然カウンタがゼロになった場合、SAI ポーリング失敗の疑いがある。

**SAI 登録失敗のカウンタ不在 vs ポーリング失敗の 0**: SAI `create_nat_entry` が失敗した場合は COUNTERS_DB にキー自体が作成されない（エントリ不在）。一方、SAI `get_nat_entry_attribute` の 5 秒ポーリングが失敗した場合はキーが存在しながら `"0"` が書かれる。どちらも `show nat statistics` では 0 と表示されるため、区別には `sonic-db-cli COUNTERS_DB exists 'COUNTERS_NAT|<ip>'` でキーの存在を確認する必要がある。

**MAX_NAT_ENTRIES=0 による NAT 全体無効**: `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` クエリが失敗 (`natorch.cpp:115-117`) するか 0 を返した場合 (`main.cpp:945-948`)、`gIsNatSupported=false` が設定される。この状態では `enableNatFeature()` が即 return し NAT エントリの SAI 登録が一切行われない。`COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES="0"` が診断の手がかりとなる。

> **証跡**: `natorch.cpp:774-783` (addHwDnatEntry SAI 失敗)、`natorch.cpp:3546-3574` (getNatCounters SAI 失敗 → 0 上書き)、`natorch.cpp:3609-3623` (getTwiceNatCounters SAI 失敗)、`natorch.cpp:3517-3521` (addedToHw ガード)、`natorch.cpp:3125-3128` (clock_gettime 失敗)、`natorch.cpp:2541-2544` (gIsNatSupported ガード)、`natorch.cpp:115-135` (コンストラクタ SAI クエリ)、`main.cpp:940-948` (gIsNatSupported 設定)。

<!-- /failure -->

<!-- constants -->
## ハードコード定数

`NatOrch` が COUNTERS_DB NAT カウンタテーブル群を書き込む際に使用する、CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) で管理されないハードコード定数の一覧。出典は `sonic-swss/orchagent/natorch.h` および `sonic-swss/orchagent/natorch.cpp`。

### カウンタ更新タイマー周期定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `NAT_HITBIT_N_CNTRS_QUERY_PERIOD` | `5` 秒 | NAT エントリのパケット・バイトカウンタおよびヒットビットを SAI から定期取得する周期。COUNTERS_NAT\* テーブルの更新間隔を決定する | `natorch.h:37` |
| `NAT_CONNTRACK_TIMEOUT_PERIOD` | `86400` 秒 (1 日) | conntrack エントリの老化チェック通知タイマー周期。カウンタ更新には関与しない | `natorch.h:38` |
| `NAT_HITBIT_QUERY_MULTIPLE` | `6` | ヒットビットクエリ周期の倍率。カウンタは 5 秒周期で更新されるが、ヒットビット (エントリのアクティブ判定) は `5 × 6 = 30` 秒周期でのみ問い合わせる | `natorch.h:39` |

### NatOrch コンストラクタ ハードコードデフォルト (COUNTERS_GLOBAL_NAT への初期書込値)

| フィールド名 | 値 | ソース変数 | ソース |
|-------------|-----|-----------|--------|
| `TIMEOUT` | `600` 秒 | `timeout = 600` | `natorch.cpp:67` |
| `TCP_TIMEOUT` | `86400` 秒 (1 日) | `tcp_timeout = 86400` | `natorch.cpp:70` |
| `UDP_TIMEOUT` | `300` 秒 | `udp_timeout = 300` | `natorch.cpp:73` |

これらは NatOrch コンストラクタで 1 回だけ `COUNTERS_GLOBAL_NAT|Values` に書き込まれ、以後 CONFIG_DB の `NAT_GLOBAL.nat_timeout` 等が変更されても更新されない。YANG default (`sonic-nat`) と同値のため、YANG バリデーション迂回が起きた場合でも同一値が初期化される。

### テーブル名定数 (schema.h)

| 定数名 | 値 | ソース |
|--------|-----|--------|
| `COUNTERS_NAT_TABLE` | `"COUNTERS_NAT"` | `schema.h:260` |
| `COUNTERS_NAPT_TABLE` | `"COUNTERS_NAPT"` | `schema.h:261` |
| `COUNTERS_TWICE_NAT_TABLE` | `"COUNTERS_TWICE_NAT"` | `schema.h:262` |
| `COUNTERS_TWICE_NAPT_TABLE` | `"COUNTERS_TWICE_NAPT"` | `schema.h:263` |
| `COUNTERS_GLOBAL_NAT_TABLE` | `"COUNTERS_GLOBAL_NAT"` | `schema.h:264` |

### APPL_DB コンシューマ優先度定数

NatOrch が消費する APPL_DB テーブルの優先度（小さい値 = 高優先）。COUNTERS_DB への書き込み順に影響する。

| テーブル名 | 優先度 | ソース |
|-----------|--------|--------|
| `APP_NAT_DNAT_POOL_TABLE_NAME` | `55` (`natorch_base_pri + 5`) | `orchdaemon.cpp:457` |
| `APP_NAT_TABLE_NAME` | `54` | `orchdaemon.cpp:458` |
| `APP_NAPT_TABLE_NAME` | `53` | `orchdaemon.cpp:459` |
| `APP_NAT_TWICE_TABLE_NAME` | `52` | `orchdaemon.cpp:460` |
| `APP_NAPT_TWICE_TABLE_NAME` | `51` | `orchdaemon.cpp:461` |
| `APP_NAT_GLOBAL_TABLE_NAME` | `50` (最低) | `orchdaemon.cpp:462` |

`APP_NAT_GLOBAL_TABLE_NAME` の優先度が最低のため、`admin_mode` の変更はエントリ系テーブルの処理完了後に評価される。

### プラットフォーム依存定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` | `getenv("platform")` の部分一致チェック。Broadcom プラットフォームでのみ `gNhTrackingSupported = true` を設定し DNAT ネクストホップ追跡を有効化 | `orch.h:43`、`natorch.cpp:145-148` |

`gNhTrackingSupported` が `false` (非 Broadcom) の場合、DNAT エントリのネクストホップ解決待ちが行われず、`addedToHw=false` のままとなる可能性がある。これはカウンタ SAI クエリのガード条件 (`natorch.cpp:3517-3521`) に影響し、`COUNTERS_NAT` の更新がスキップされうる。

<!-- /constants -->

<!-- side-effects -->
## 副作用・波及挙動

`NatOrch` が 5 秒タイマーで `COUNTERS_DB` を更新する処理には、カウンタ書き込み以外の副次的な挙動が含まれる。以下はコードから確認できる主要な副作用。

### 副作用一覧

| # | 副作用 | トリガ | 対象 DB / システム | 可逆性 |
|---|--------|--------|-------------------|--------|
| 1 | 動的 NAT エントリのエージアウト → `COUNTERS_NAT*` キー削除 | 30 秒ポーリング + ヒットビット = 0 + タイムアウト超過 | APPL_DB (`SETTIMEOUTNAT`), COUNTERS_DB | 再フロー時に新エントリ追加で復元 |
| 2 | SAI ヒットビットのクリア (read-and-clear) | 30 秒ごとの `checkIfNatEntryIsActive()` 呼び出し | SAI 内部状態 | 次のフロー通過で SAI がビットをセット |
| 3 | conntrack タイムアウトリセット通知 | 1 日周期タイマー (`m_natTimeoutTimer`) | カーネル conntrack テーブル | 周期的動作 |
| 4 | `SNAT_ENTRIES` / `DNAT_ENTRIES` リアルタイム更新 | SAI エントリ追加/削除成功 | `COUNTERS_GLOBAL_NAT\|Values` | 状態反映（即時） |
| 5 | `COUNTERS_NAT*` 全エントリ一括削除 | natorch docker 停止 (`NAT_DB_CLEANUP_NOTIFICATION`) | COUNTERS_DB | docker 再起動 + `admin_mode=enabled` で復元 |

### 副作用の詳細

**カウンタポーリングがエージアウトを駆動 (副作用 #1)**: `doTask(SelectableTimer)` は 5 秒ごとに `natTimerTickCntr++` を評価し、`% 6 == 0`（30 秒に 1 度）のときだけ `queryHitBits()` を呼ぶ (`natorch.cpp:3101-3104`)。`queryHitBits()` は SAI から `HIT_BIT` を取得し、ヒットビット = 0 かつ `now - activeTime >= timeout` を満たす動的 SNAT エントリに対して `setTimeoutNotifier->send("AGEOUT-SINGLE-NAT", key, ...)` を `SETTIMEOUTNAT` チャンネルへ送信する (`natorch.cpp:3316-3338`)。natsyncd がこれを受信して APPL_DB エントリを削除し、最終的に `deleteNatCounters()` で COUNTERS_DB のカウンタエントリが消滅する。**カウンタを参照するタイミングと同期して COUNTERS_DB からキーが削除されうる**ことに注意。

**ヒットビット取得は read-and-clear 操作 (副作用 #2)**: `checkIfNatEntryIsActive()` (`natorch.cpp:4166-4171`) は SAI 属性 `SAI_NAT_ENTRY_ATTR_HIT_BIT` と `SAI_NAT_ENTRY_ATTR_HIT_BIT_COR=1` を同時に要求する。これは「取得しながら同時にクリアする」操作であり、NatOrch 以外が SAI を直接参照した場合、30 秒ポーリング後はヒットビットがゼロになっている。

**conntrack タイムアウトリセット通知 (副作用 #3)**: `m_natTimeoutTimer`（86400 秒 = 1 日周期）が起動すると `updateAllConntrackEntries()` を呼ぶ (`natorch.cpp:3107-3111`)。この関数は HW 登録済みの全動的 SNAT / NAPT / Twice NAT エントリに対して `setTimeoutNotifier->send("SET-SINGLE-NAT" / "SET-SINGLE-NAPT" / ...)` を送信し、カーネル conntrack エントリのタイムアウトをリセットする。COUNTERS_DB への書き込みは行われないが、同じ SelectableTimer dispatch からトリガされる (`natorch.cpp:3443-3505`)。

**docker 停止時の全カウンタ削除 (副作用 #5)**: natorch docker 停止シグナルを受けた際、APPL_DB の `NAT_DB_CLEANUP_NOTIFICATION` チャンネルに通知が届く。`doTask(NotificationConsumer)` がこれを受信して `cleanupAppDbEntries()` を呼び (`natorch.cpp:4474-4478`)、全 NAT エントリを APPL_DB から削除するとともに `removeNatEntry()` → `deleteNatCounters()` で COUNTERS_DB の `COUNTERS_NAT*` 全エントリを消去する。docker 再起動後は `admin_mode=enabled` の処理で `addAllNatEntries()` が呼ばれるまでカウンタエントリが存在しない状態になる。

> **証跡**: `natorch.cpp:3101-3104` (ヒットビット/カウンタタイマー多重化), `natorch.cpp:3316-3338` (AGEOUT通知送信), `natorch.cpp:4166-4170` (HIT_BIT_COR=1), `natorch.cpp:3107-3111` (1日タイマー分岐), `natorch.cpp:3443-3505` (updateAllConntrackEntries), `natorch.cpp:4063-4075` (deleteNatCounters), `natorch.cpp:4474-4478` (NAT_DB_CLEANUP_NOTIFICATION), `natorch.cpp:2457-2532` (cleanupAppDbEntries), `natorch.cpp:4569-4589` (updateSnat/DnatCounters).

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム

<!-- evidence: sonic-swss/orchagent/natorch.cpp / sonic-swss/cfgmgr/natmgr.cpp / sonic-swss/orchagent/orchdaemon.cpp -->

`COUNTERS_DB` NAT カウンタテーブル群は `NatOrch` のみが書き手となる特殊なランタイムステータスレジスタである。通常の CONFIG_DB → APPL_DB → [orchagent](../../reference/glossary.md#term-orchagent) パスとは異なり、**SAI タイマーポーリング**と**APPL_DB 非同期通知チャンネル**の 2 つの経路で COUNTERS_DB が更新される。

### 書き込み経路の全体像

```
CONFIG_DB (NAT_GLOBAL / NAT_POOL / NAT_BINDINGS)
  ↓ SubscriberStateTable (keyspace PSUBSCRIBE)
natmgrd (NatMgr::doTask)
  ↓ ProducerStateTable
APPL_DB (APP_NAT_TABLE / APP_NAPT_TABLE / APP_NAT_GLOBAL_TABLE 等)
  ↓ ConsumerStateTable (SUBSCRIBE APP_NAT_TABLE_CHANNEL@0 等)
NatOrch::doTask(Consumer&)
  ↓ sai_nat_api->create_nat_entry() 成功時
  → updateNatCounters(ip, 0, 0)  # COUNTERS_DB エントリを 0 で初期化
  ↓
SelectableTimer (5 秒周期)
  → queryCounters() → getNatCounters() → SAI get_nat_entry_attribute
  → updateNatCounters(ip, pkts, bytes)  # COUNTERS_DB に実測値を書き込み
```

### 層 1: CONFIG_DB → natmgrd (SubscriberStateTable)

`natmgrd` は起動時に以下の CONFIG_DB テーブルを `SubscriberStateTable` (keyspace PSUBSCRIBE) で購読する (`natmgrd.cpp:109-121`):

| CONFIG_DB テーブル | 対応 doTask ハンドラ |
|-------------------|---------------------|
| `NAT_GLOBAL` | `doNatGlobalTask` → `m_appNatGlobalTableProducer.set(...)` |
| `NAT_POOL` | `doNatPoolTask` → `m_appNatDnatPoolProducer.set(...)` |
| `NAT_BINDINGS` | `doNatBindingTask` → `m_appNatTableProducer.set(...)` 等 |
| `STATIC_NAT` / `STATIC_NAPT` | `doStaticNatTask` / `doStaticNaptTask` |
| `INTERFACE` / `LAG_INTERFACE` / `VLAN_INTERFACE` 等 | `doNatIpInterfaceTask` |
| `ACL_TABLE` / `ACL_RULE` | `doNatAclTableTask` / `doNatAclRuleTask` |

keyspace 購読パターン (CONFIG_DB db_id=4 の場合):

```
PSUBSCRIBE __keyspace@4__:NAT_GLOBAL|*
PSUBSCRIBE __keyspace@4__:NAT_POOL|*
PSUBSCRIBE __keyspace@4__:NAT_BINDINGS|*
```

`SubscriberStateTable` は PSUBSCRIBE 後に既存 key を全件スナップショットとして再生するため、`natmgrd` 再起動後も全 NAT エントリが再処理される。

### 層 2: APPL_DB → NatOrch (ConsumerStateTable)

`orchdaemon.cpp:457-462` で `NatOrch` を生成し、APPL_DB 上の以下のテーブルを **[ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable)** で購読する:

| APPL_DB テーブル | 優先度 | COUNTERS_DB への影響 |
|-----------------|--------|----------------------|
| `APP_NAT_DNAT_POOL_TABLE` | 55 (最高) | DNAT プール IP 登録 → SAI DNAT エントリ作成 → `COUNTERS_NAT` キー生成 |
| `APP_NAT_TABLE` | 54 | SNAT / DNAT エントリ → `updateNatCounters(0,0)` |
| `APP_NAPT_TABLE` | 53 | NAPT エントリ → `updateNaptCounters(0,0)` |
| `APP_NAT_TWICE_TABLE` | 52 | Twice NAT エントリ → `updateTwiceNatCounters(0,0)` |
| `APP_NAPT_TWICE_TABLE` | 51 | Twice NAPT エントリ → `updateTwiceNaptCounters(0,0)` |
| `APP_NAT_GLOBAL_TABLE` | 50 (最低) | `admin_mode=enabled` → `enableNatFeature()` → タイマー起動 |

`ConsumerStateTable` は `SUBSCRIBE APP_NAT_TABLE_CHANNEL@0` 形式のチャンネルを購読し、`ProducerStateTable::set()` が Lua スクリプトで PUBLISH したメッセージを受信する。

### 層 3: SAI タイマーポーリング → COUNTERS_DB

COUNTERS_DB への実測値書き込みは `SelectableTimer` 経由で行われる。これは通常の [Redis](../../reference/glossary.md#term-redis) pub/sub ではなく、`swss::Select` の fd ポーリング機構を使う:

```
orchagent メインループ (Select::select)
  → m_natQueryTimer の fd が ready
  → NatOrch::doTask(SelectableTimer&)
  → queryHitBits() [30 秒に 1 回]  +  queryCounters() [5 秒ごと]
  → getNatCounters() / getNaptCounters() / getTwiceNatCounters()
  → SAI: sai_nat_api->get_nat_entry_attribute(SAI_NAT_ENTRY_ATTR_BYTE_COUNT / PACKET_COUNT)
  → updateNatCounters(ip, pkts, bytes)
  → m_countersNatTable.set(key, {NAT_TRANSLATIONS_PKTS, NAT_TRANSLATIONS_BYTES})
```

### 非同期通知チャンネル

NAT データパスには `NotificationConsumer / NotificationProducer` による 4 本の非同期チャンネルが存在する:

| チャンネル名 | DB | 方向 | 送信者 | 受信者 | COUNTERS_DB への影響 |
|---|---|---|---|---|---|
| `SETTIMEOUTNAT` | APPL_DB | NatOrch → [natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) | `NatOrch::setTimeoutNotifier` (`natorch.cpp:137`) | `natmgrd.cpp:149` `timeoutNotificationsConsumer` | 直接影響なし (conntrack タイムアウトのみ) |
| `FLUSHNATENTRIES` | APPL_DB | CLI → [natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) | `sonic-clear nat translations` | `natmgrd.cpp:152` `flushNotificationsConsumer` | [natmgrd](../../reference/glossary.md#term-natmgrd-natsyncd) が APPL_DB エントリを削除 → NatOrch が `deleteNatCounters()` を呼ぶ → COUNTERS_DB キー消滅 |
| `FLUSHNATSTATISTICS` | APPL_DB | CLI → NatOrch | `sonic-clear nat statistics` | `natorch.cpp:84-86` `m_flushNotificationsConsumer` | `clearCounters()` → SAI `reset_nat_entry_attribute` → `COUNTERS_NAT*` フィールドを `"0"` にリセット |
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd → NatOrch | natmgrd 停止シグナル時 | `natorch.cpp:89-91` `m_cleanupNotificationConsumer` | `cleanupAppDbEntries()` → 全 NAT エントリ削除 → 全 `COUNTERS_NAT*` キー消滅 |

### COUNTERS_GLOBAL_NAT の書き込みタイミング

`COUNTERS_GLOBAL_NAT|Values` の各フィールドは [Redis](../../reference/glossary.md#term-redis) pub/sub によらず直接 `m_countersGlobalNatTable.set()` で書き込まれる:

| フィールド | 書き込みタイミング | トリガ |
|---|---|---|
| `MAX_NAT_ENTRIES` / `TIMEOUT` / `UDP_TIMEOUT` / `TCP_TIMEOUT` | NatOrch コンストラクタ (1 回のみ) | [orchagent](../../reference/glossary.md#term-orchagent) 起動 |
| `STATIC_NAT_ENTRIES` 等のエントリ数カウンタ | `addHwSnatEntry()` / `removeHwSnatEntry()` 成功時 | APPL_DB [ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) イベント |
| `SNAT_ENTRIES` / `DNAT_ENTRIES` | SAI エントリ追加/削除ごとに即時 | 同上 |

> **Evidence**: `natorch.cpp:84-91` (NotificationConsumer 登録), `natorch.cpp:137` (NotificationProducer), `natorch.cpp:3095-3117` (SelectableTimer doTask), `orchdaemon.cpp:457-462` ([ConsumerStateTable](../../reference/glossary.md#term-consumerstatetable) 優先度), `natmgr.cpp:43-49` ([ProducerStateTable](../../reference/glossary.md#term-producerstatetable) 群), `natmgrd.cpp:109-121` (SubscriberStateTable 購読テーブル一覧), `natorch.cpp:4450-4490` (NotificationConsumer doTask)

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム / SAI Capability 差異

`COUNTERS_DB` NAT カウンタテーブル群の書き込み有無・更新挙動はプラットフォームの NAT ハードウェアサポートと DNAT ネクストホップ追跡能力に強く依存する。

### プラットフォーム別挙動マトリクス

| 条件 | `gIsNatSupported` | `gNhTrackingSupported` | COUNTERS_DB への影響 |
|------|-----------------|----------------------|----------------------|
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY == 0` または取得失敗 | `false` | `false` | `enableNatFeature()` が即 return → `m_natQueryTimer` 未起動 → `COUNTERS_NAT*` のエントリ数カウンタは 0 のまま。エントリ追加時のゼロ初期化 `update*Counters(0,0)` は呼ばれるが、5 秒タイマー更新が来ない |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY > 0` かつ非 Broadcom | `true` | `false` | DNAT エントリは APPL_DB 受信と同時に `addHwDnatEntry()` を即時呼び出し → `COUNTERS_NAT` に即座にキーが生成。5 秒タイマーによるカウンタ更新あり |
| `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY > 0` かつ `broadcom` | `true` | `true` | DNAT エントリは NeighOrch / RouteOrch のネクストホップ解決後に `addHwDnatEntry()` が遅延呼び出しされる。NH 未解決の間は `COUNTERS_NAT` にキーが存在しない |
| [VS](../../reference/glossary.md#term-vs) / テスト環境 (`sw.sonic-test`) | `false` | `false` | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` 未サポート → `gIsNatSupported=false`。NAT 機能全体が無効。CLI は受け付けるが APPL_DB エントリが SAI に降りないため `COUNTERS_NAT*` 実測値は更新されない |

### `gIsNatSupported` の決定経路

`gIsNatSupported` は orchagent 起動時 `main.cpp:936-948` で一度だけ設定され、以後変更されない。

```
main.cpp:936-948
  sai_switch_api->get_switch_attribute(SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY)
  status != SAI_STATUS_SUCCESS → gIsNatSupported 変更なし (false のまま)
  attr.value.u32 == 0         → gIsNatSupported 変更なし (false のまま)
  attr.value.u32 > 0          → gIsNatSupported = true
```

### `gNhTrackingSupported` の決定経路 (Broadcom 限定)

```cpp
// natorch.cpp:144-149
char *platform = getenv("platform");
if (platform && strstr(platform, BRCM_PLATFORM_SUBSTRING))  // "broadcom"
{
    gNhTrackingSupported = true;
}
```

`BRCM_PLATFORM_SUBSTRING = "broadcom"` が `platform` 環境変数に含まれる場合のみ `true`。Mellanox / Marvell / Cisco / Innovium 等は `false`。

### DNAT NH 追跡有無による COUNTERS_NAT キー生成タイミングの差

| `gNhTrackingSupported` | DNAT エントリの `COUNTERS_NAT` キー生成タイミング |
|---|---|
| `false` (非 Broadcom) | `addNatEntry()` → `addHwDnatEntry()` → `updateNatCounters(0,0)` が **即時** 呼ばれる |
| `true` (Broadcom) | `addNatEntry()` → NH 未解決なら `addDnatToCache()` のみ → `COUNTERS_NAT` キー未生成。NH 解決通知後に `addHwDnatEntry()` → `updateNatCounters(0,0)` で初めてキーが生成される |

SNAT / NAPT / Twice NAT エントリおよび `COUNTERS_GLOBAL_NAT` の書き込みは `gNhTrackingSupported` に関わらず共通動作。

> **Evidence**: `natorch.cpp:144-149` (gNhTrackingSupported 設定), `main.cpp:936-948` (gIsNatSupported 設定), `natorch.cpp:2541-2544` (gIsNatSupported ガード), `natorch.cpp:1923,1959` (gNhTrackingSupported 分岐)

<!-- /platform -->

<!-- glossary-links-injected: 9fb3fca99a59 -->
