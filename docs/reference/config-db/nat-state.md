---
title: NAT_RESTORE_TABLE / COUNTERS_NAT テーブル
description: "NAT_RESTORE_TABLE / COUNTERS_NAT テーブル — NAT warm reboot 復元フラグを保持する STATE_DB テーブルと、NAT エントリのパケット・バイト数カウンタを管理する COUNTERS_DB テーブル群の定義。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: natsyncd/natsync.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/natorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-nat/restore_nat_entries.py
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - NAT_GLOBAL
    - NAT_POOL
    - NAT_BINDINGS
  cli:
    - show nat
  yang:
    - sonic-nat
---

# NAT_RESTORE_TABLE / COUNTERS_NAT テーブル

## 概要

[NAT](../../reference/glossary.md#term-nat) 機能が管理する実行時データベースには 2 種類のテーブル群が存在する。

1. **`STATE_DB:NAT_RESTORE_TABLE`** — [NAT](../../reference/glossary.md#term-nat) docker の warm reboot 復元スクリプト (`restore_nat_entries.py`) が conntrack エントリを kernel に書き戻した後にセットするフラグ。`natsyncd` がこのフラグを確認してから reconciliation を開始する[^1]。
2. **`COUNTERS_DB:COUNTERS_NAT*`** — `orchagent/NatOrch` が [SAI](../../reference/glossary.md#term-sai) から定期取得するパケット・バイト数カウンタ、およびエントリ数・タイムアウトなどのグローバル統計[^2]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>NAT_GLOBAL")]
  DM["natmgrd"]
  CDB --> DM
  APPDB[("APP_DB<br/>NAT_TABLE")]
  DM --> APPDB
  ORCH["orchagent / NatOrch"]
  APPDB --> ORCH
  SAI["SAI<br/>sai_nat_api"]
  ORCH --> SAI
  STATEDB[("STATE_DB<br/>NAT_RESTORE_TABLE")]
  RESTORE["restore_nat_entries.py"] --> STATEDB
  NATSYNC["natsyncd"] -- "hget Flags.restored" --> STATEDB
  COUNTERS[("COUNTERS_DB<br/>COUNTERS_NAT*")]
  ORCH -- "5s poll" --> SAI
  SAI -- "hit/bytes" --> ORCH
  ORCH --> COUNTERS
```

!!! note "凡例"
    STATE_DB/COUNTERS_DB の書き込み経路を追加した図。通常の CONFIG → SAI パスは左側を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
STATE_DB:NAT_RESTORE_TABLE|Flags

COUNTERS_DB:COUNTERS_NAT|<external_ip>
COUNTERS_DB:COUNTERS_NAPT|<proto>:<ip>:<port>
COUNTERS_DB:COUNTERS_TWICE_NAT|<src_ip>:<dst_ip>
COUNTERS_DB:COUNTERS_TWICE_NAPT|<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>
COUNTERS_DB:COUNTERS_GLOBAL_NAT|Values
```

## 主要フィールド

### STATE_DB:NAT_RESTORE_TABLE

| フィールド | 型 | 値 | 書き込みタイミング |
|-----------|-----|-----|-------------------|
| `restored` | 文字列 | `"true"` | warm reboot 後、`restore_nat_entries.py` が conntrack 復元完了時 |

warm reboot なし (通常起動) では `NAT_RESTORE_TABLE|Flags` は**書き込まれない**。`natsyncd` は `hget("Flags", "restored", value)` が空文字列を返す場合に reconciliation なしで進む。

### COUNTERS_DB:COUNTERS_NAT

| キー形式 | フィールド | 型 | 初期値 | 説明 |
|---------|-----------|-----|--------|------|
| `<external_ip>` | `NAT_TRANSLATIONS_PKTS` | uint64 (文字列) | `"0"` | SAI から取得したパケット数 |
| `<external_ip>` | `NAT_TRANSLATIONS_BYTES` | uint64 (文字列) | `"0"` | SAI から取得したバイト数 |

初期値 `"0"` は SNAT/DNAT エントリが SAI に登録された直後に `updateNatCounters(ipAddr, 0, 0)` で書き込まれる (`natorch.cpp:789`)。

### COUNTERS_DB:COUNTERS_NAPT

| キー形式 | フィールド | 型 | 初期値 |
|---------|-----------|-----|--------|
| `<proto>:<ip>:<port>` (例: `TCP:10.0.0.1:1024`) | `NAT_TRANSLATIONS_PKTS` | uint64 (文字列) | `"0"` |
| 同上 | `NAT_TRANSLATIONS_BYTES` | uint64 (文字列) | `"0"` |

### COUNTERS_DB:COUNTERS_TWICE_NAT

| キー形式 | フィールド | 型 | 説明 |
|---------|-----------|-----|------|
| `<src_ip>:<dst_ip>` | `NAT_TRANSLATIONS_PKTS` | uint64 (文字列) | Twice NAT ペアのパケット数 |
| 同上 | `NAT_TRANSLATIONS_BYTES` | uint64 (文字列) | Twice NAT ペアのバイト数 |

### COUNTERS_DB:COUNTERS_TWICE_NAPT

| キー形式 | フィールド | 型 | 説明 |
|---------|-----------|-----|------|
| `<proto>:<src_ip>:<src_port>:<dst_ip>:<dst_port>` | `NAT_TRANSLATIONS_PKTS` | uint64 (文字列) | Twice NAPT のパケット数 |
| 同上 | `NAT_TRANSLATIONS_BYTES` | uint64 (文字列) | Twice NAPT のバイト数 |

### COUNTERS_DB:COUNTERS_GLOBAL_NAT

キー: `"Values"` (固定)

| フィールド | 型 | 初期値 | 更新タイミング | 説明 |
|-----------|-----|--------|---------------|------|
| `MAX_NAT_ENTRIES` | uint32 (文字列) | SAI query 値 (非対応時 `"0"`) | NatOrch 起動時のみ | プラットフォームが許容する最大 SNAT エントリ数 |
| `TIMEOUT` | uint32 (文字列) | `"600"` | NatOrch 起動時のみ | 非 TCP/UDP NAT タイムアウト秒 |
| `UDP_TIMEOUT` | uint32 (文字列) | `"300"` | NatOrch 起動時のみ | UDP NAT タイムアウト秒 |
| `TCP_TIMEOUT` | uint32 (文字列) | `"86400"` | NatOrch 起動時のみ | TCP NAT タイムアウト秒 |
| `SNAT_ENTRIES` | int (文字列) | `"0"` | SNAT エントリ追加/削除時 | 現在の SNAT エントリ総数 |
| `DNAT_ENTRIES` | int (文字列) | `"0"` | DNAT エントリ追加/削除時 | 現在の DNAT エントリ総数 |

## 制約

- `NAT_RESTORE_TABLE` は warm reboot / NAT warm restart が有効な場合のみ使用される。通常起動では存在しない。
- `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES` = 0 の場合、`gIsNatSupported=false` となり NAT 機能が完全に無効化される。
- COUNTERS テーブルは `NAT_HITBIT_N_CNTRS_QUERY_PERIOD=5` 秒周期で更新される。リアルタイム値ではない。

## 購読者

- `natsyncd`: `STATE_DB:NAT_RESTORE_TABLE|Flags.restored` を warm start 中に参照し、`"true"` になってから [APPL_DB](../../reference/glossary.md#term-appl_db) との reconciliation を開始する。
- `orchagent / NatOrch`: SAI NAT カウンタを 5 秒周期でポーリングし `COUNTERS_DB:COUNTERS_NAT*` を更新する。`show nat statistics` はこのデータを表示する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `NAT_GLOBAL`、`NAT_POOL`、`NAT_BINDINGS`
- 関連 CLI: `show nat statistics`、`show nat translations`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-nat`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`NAT_GLOBAL / NAT_POOL`](nat.md)
- CONFIG_DB: [`NAT_BINDINGS`](nat-bindings.md)
- CLI: [`config nat`](../cli/config-nat.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: warm reboot 復元フラグ: `restore_nat_entries.py`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-nat/restore_nat_entries.py>
[^2]: NAT カウンタ実装: `natorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/natorch.cpp>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: NAT / DHCP Relay / Time-DNS Services](../../topics/16-nat-dhcp-dns/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 確認コマンド

```bash
# NAT カウンタ統計
show nat statistics

# COUNTERS_DB を直接参照
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_GLOBAL_NAT|Values'
sonic-db-cli COUNTERS_DB hgetall 'COUNTERS_NAT|<external_ip>'

# warm reboot 復元フラグ確認
sonic-db-cli STATE_DB hgetall 'NAT_RESTORE_TABLE|Flags'
```

### warm reboot 時の動作

1. `restore_nat_entries.py` が `/var/warmboot/nat/nat_entries.dump` を読み込み kernel conntrack に復元
2. 復元完了後、`STATE_DB:NAT_RESTORE_TABLE|Flags.restored = "true"` をセット
3. `natsyncd` がフラグを確認し、APPL_DB と conntrack の差分 reconciliation を実行

### よくある誤操作

- `MAX_NAT_ENTRIES=0` の場合は NAT が機能しない。`gIsNatSupported` フラグが false になっておりプラットフォームが NAT をサポートしていない。
<!-- /ops-hint -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: sonic-swss/orchagent/natorch.cpp NatOrch::NatOrch() / natsync.cpp -->

- **`MAX_NAT_ENTRIES=0` → NAT 無効化**: NatOrch コンストラクタで `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` の取得に失敗または 0 を返すと `gIsNatSupported=false` が設定される。`enableNatFeature()` 冒頭で `gIsNatSupported==false` → `SWSS_LOG_NOTICE + return` となり CONFIG_DB の `admin_mode=enabled` が無視される (`natorch.cpp:100-122, 2541-2544`)。
- **カウンタ更新タイミングの非同期性**: COUNTERS_NAT の値は最大 5 秒遅延する。`show nat statistics` の値はリアルタイムではない。
- **Static エントリのカウンタ**: `entry_type="static"` かつ `addedToHw=true` の場合、hit bit が定期的に SAI から取得され COUNTERS_NAT に反映される。ただし Static エントリはエージアウト対象外 (`checkIfNatEntryIsActive` は static を常に `active=1` として扱う, `natorch.cpp:4160-4163`)。
- **NAT_RESTORE_TABLE の不在が正常**: 通常起動では `NAT_RESTORE_TABLE|Flags` は存在しない。`natsyncd` の `hget` は空文字列を返し、reconciliation なしで通常動作に移行する。

<!-- /cdb-exceptions -->

<!-- value-behavior -->
## 値依存挙動マトリクス

<!-- evidence: sonic-swss/orchagent/natorch.cpp updateSnatCounters / updateDnatCounters / NatOrch constructor -->

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `STATE_DB:NAT_RESTORE_TABLE\|Flags.restored` | (存在しない) | natsyncd が reconciliation なしで通常動作 |
| `STATE_DB:NAT_RESTORE_TABLE\|Flags.restored` | `"true"` | natsyncd が APPL_DB ↔ conntrack の差分 reconciliation を実行 |
| `COUNTERS_GLOBAL_NAT\|Values.MAX_NAT_ENTRIES` | `"0"` | NAT 機能が gIsNatSupported=false により無効化される |
| `COUNTERS_GLOBAL_NAT\|Values.MAX_NAT_ENTRIES` | `"N"` (N>0) | NAT エントリが最大 N 件まで SAI に登録可能 |
| `COUNTERS_GLOBAL_NAT\|Values.SNAT_ENTRIES` | `"N"` | 現在アクティブな SNAT エントリ数 (SAI 登録済み) |
| `COUNTERS_GLOBAL_NAT\|Values.DNAT_ENTRIES` | `"N"` | 現在アクティブな DNAT エントリ数 (SAI 登録済み) |

<!-- /value-behavior -->

<!-- ordering -->
## 書込み順依存 (Phase B)

`NAT_RESTORE_TABLE` と `COUNTERS_DB:COUNTERS_NAT*` は互いに独立した書き手（`restore_nat_entries.py` / `NatOrch`）が管理する。ただし warm reboot 時は `restored` フラグの到達タイミングが `natsyncd` の reconciliation 開始を決定するため、フラグ書き込みの順序が重要になる。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `restore_nat_entries.py` が conntrack 復元完了 → `NAT_RESTORE_TABLE\|Flags.restored = "true"` 書込み → `natsyncd` が reconciliation 開始 | **強制先行**（フラグなしでは natsyncd は reconciliation をスキップ） | 通常起動ではフラグが存在しないため reconciliation そのものが発生しない |
| 2 | `NatOrch` コンストラクタ完了 → `COUNTERS_GLOBAL_NAT\|Values` 書込み | 1 回限り（起動時に即時書き込み） | orchestrator 起動前は `COUNTERS_GLOBAL_NAT` エントリが存在しない |
| 3 | SAI エントリ登録成功 → `COUNTERS_NAT\|<ip>` / `COUNTERS_NAPT\|<proto:ip:port>` 初期値 `"0"` 書込み | SAI 登録直後（`updateNatCounters(..., 0, 0)`） | `admin_mode = "disabled"` の間は SAI 登録が起きないためカウンタエントリも存在しない |
| 4 | `NAT_GLOBAL_TABLE.admin_mode = "enabled"` → `m_natQueryTimer` 起動 → 5 秒周期カウンタポーリング開始 | enable 後に初回ポーリング | disable 中はタイマーが停止しカウンタは更新されない |
| 5 | warm reboot で `natsyncd` が reconciliation 完了 → APPL_DB と conntrack の差分更新 → SAI エントリ登録 → `COUNTERS_NAT*` 書込み | reconciliation 完了後に逐次書込み | 通常起動では reconciliation がないため APPL_DB 受信の都度即時 |
| 6 | `COUNTERS_GLOBAL_NAT\|Values.MAX_NAT_ENTRIES` = 0 → `gIsNatSupported = false` → `enableNatFeature()` が即時 return | NatOrch コンストラクタ時の SAI クエリ結果で固定 | カウンタキーは書かれるが NAT エントリは SAI に降りない |

### 主要な制約詳細

**warm reboot 時のフラグ先行要件 (依存 #1)**: `natsyncd` は起動後 `isNatRestoreDone()` (`natsync.cpp:96-108`) を周期的に呼び、`STATE_DB:NAT_RESTORE_TABLE|Flags.restored == "true"` を確認してから reconciliation を開始する。`restore_nat_entries.py` は `/var/warmboot/nat/nat_entries.dump` から conntrack を復元した後にこのフラグをセットする。フラグがセットされる前に `natsyncd` が APPL_DB を更新しても reconciliation 処理に乗らないため、データの整合性がとれない可能性がある。通常起動（warm start 無効）では `hget` が空文字列を返し、`isNatRestoreDone()` は `false` を返すが、natsyncd は warm start フラグを確認したうえで reconciliation をスキップして通常動作に移行する（evidence: `natsync.cpp:96-108`）。

**COUNTERS_GLOBAL_NAT の起動時 1 回書込み (依存 #2)**: `NatOrch::NatOrch()` コンストラクタは `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` をクエリして `MAX_NAT_ENTRIES` を決定し、`COUNTERS_GLOBAL_NAT|Values` に `MAX_NAT_ENTRIES` / `TIMEOUT` / `UDP_TIMEOUT` / `TCP_TIMEOUT` の 4 フィールドを 1 度だけ書き込む（evidence: `natorch.cpp:108-134`）。その後 CONFIG_DB の `NAT_GLOBAL.nat_timeout` が変更されても `COUNTERS_GLOBAL_NAT` の TIMEOUT フィールドは更新されない。このためタイムアウト表示の出所は起動時の固定値となる。

**カウンタポーリングと enable 状態の依存 (依存 #4)**: `m_natQueryTimer` は `enableNatFeature()` (`natorch.cpp:2565`) で開始され、`disableNatFeature()` (`natorch.cpp:2602`) で停止する。タイマー発火ごとに `queryCounters()` が `m_natEntries` / `m_naptEntries` を走査して SAI から hit count を取得し `COUNTERS_NAT*` を更新する（evidence: `natorch.cpp:3099-3115`）。`admin_mode = "disabled"` の間は timer が停止しているため、`COUNTERS_NAT*` の値は最後の disable 時点で固定される。

<!-- /ordering -->

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

YANG 定義外の実行時テーブルのためコード hardcode 値のみ。

| フィールド | テーブル | 初期値 | ソース |
|-----------|---------|--------|--------|
| `NAT_TRANSLATIONS_PKTS` | `COUNTERS_NAT` / `COUNTERS_NAPT` 各エントリ | `"0"` | `natorch.cpp:789` (`updateNatCounters(ipAddr, 0, 0)`) |
| `NAT_TRANSLATIONS_BYTES` | `COUNTERS_NAT` / `COUNTERS_NAPT` 各エントリ | `"0"` | `natorch.cpp:789` |
| `MAX_NAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | SAI 問い合わせ値 (失敗時 `"0"`) | `natorch.cpp:127` |
| `TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"600"` | `natorch.cpp:128` (= `NAT_TIMEOUT_DEFAULT`) |
| `UDP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"300"` | `natorch.cpp:129` (= `NAT_UDP_TIMEOUT_DEFAULT`) |
| `TCP_TIMEOUT` | `COUNTERS_GLOBAL_NAT\|Values` | `"86400"` | `natorch.cpp:130` (= `NAT_TCP_TIMEOUT_DEFAULT`) |
| `SNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:76,4574` (`totalSnatEntries=0` 初期化) |
| `DNAT_ENTRIES` | `COUNTERS_GLOBAL_NAT\|Values` | `"0"` | `natorch.cpp:76,4585` (`totalDnatEntries=0` 初期化) |
| `restored` | `STATE_DB:NAT_RESTORE_TABLE\|Flags` | (warm reboot 時のみ書き込まれる; 通常起動では存在しない) | `restore_nat_entries.py:51` |

### COUNTERS_GLOBAL_NAT の TIMEOUT フィールドと CONFIG_DB の乖離

`COUNTERS_GLOBAL_NAT|Values` の `TIMEOUT`/`TCP_TIMEOUT`/`UDP_TIMEOUT` フィールドは NatOrch 起動時に一度だけ書き込まれ、その後 CONFIG_DB の `NAT_GLOBAL.nat_timeout` が変更されても**更新されない**。`show nat statistics` の timeout 表示は起動時の初期値を反映したものになる可能性がある。実際のタイムアウト値は `show nat config globalvalues` で確認すること。

<!-- /defaults -->
