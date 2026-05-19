---
title: PFC_WD 状態フィールド (COUNTERS_DB)
description: "PFC Watchdog の runtime 状態・カウンタフィールド。COUNTERS_DB の COUNTERS:<queue_oid> ハッシュに書き込まれ、storm 検知カウント・パケット統計・queue ステータスを保持する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/pfcactionhandler.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/pfcwdorch.cpp
    ref: master
related:
  config_db:
    - PFC_WD
    - PORT
    - PORT_QOS_MAP
  cli:
    - pfcwd
  yang:
    - sonic-pfcwd
---

# PFC_WD 状態フィールド (COUNTERS_DB)

## 概要

[PFC Watchdog](../../reference/glossary.md#term-pfc-watchdog) の runtime 状態・カウンタは **COUNTERS_DB** の `COUNTERS:<queue_oid>` ハッシュに書き込まれる（STATE_DB ではない）。`pfcwdorch` が [CONFIG_DB](../../reference/glossary.md#term-config_db) `PFC_WD|<port>` を読み込んで PFC WD を有効化した際に初期フィールドが書き込まれ、以降は storm 検知・復旧のたびに更新される。[^1]

## key 構造

```text
COUNTERS:<queue_oid>   # per-queue PFC WD カウンタ
```

`<queue_oid>` は `COUNTERS_QUEUE_NAME_MAP` で `<port>:<queue_index>` に対応する SAI オブジェクト ID。

## 主要フィールド

### ステータスフィールド

| フィールド | 値 | 説明 |
|---|---|---|
| `PFC_WD_STATUS` | `operational` / `stormed` | queue の現在状態。PFC WD 有効化直後は `operational` |
| `PFC_WD_DETECTION_TIME` | uint (μs) | CONFIG_DB `detection_time` (ms) × 1000 変換値。Lua プラグインが storm 検知判定に使用 |
| `PFC_WD_RESTORATION_TIME` | uint (μs) / `""` | CONFIG_DB `restoration_time` (ms) × 1000 変換値。未設定時は `""` (無限待機) |
| `PFC_WD_ACTION` | `drop` / `forward` / `alert` | CONFIG_DB `action` の複写。未設定時は `drop` |
| `PFC_STAT_HISTORY` | `enable` / `disable` | CONFIG_DB `pfc_stat_history` の複写。未設定時は `disable` |

### カウンタフィールド

| フィールド | 説明 |
|---|---|
| `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` | storm 検知累積回数 |
| `PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED` | storm 復旧累積回数 |
| `PFC_WD_QUEUE_STATS_TX_PACKETS` | storm 期間中の送信パケット累積数 |
| `PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS` | storm 期間中の送信ドロップ累積数 |
| `PFC_WD_QUEUE_STATS_RX_PACKETS` | storm 期間中の受信パケット累積数 |
| `PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS` | storm 期間中の受信ドロップ累積数 |
| `PFC_WD_QUEUE_STATS_TX_PACKETS_LAST` | 直近 storm 期間の送信パケット数 |
| `PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS_LAST` | 直近 storm 期間の送信ドロップ数 |
| `PFC_WD_QUEUE_STATS_RX_PACKETS_LAST` | 直近 storm 期間の受信パケット数 |
| `PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS_LAST` | 直近 storm 期間の受信ドロップ数 |

## ライフサイクル

1. `pfcwd start <port>` → `pfcwdorch::startWdOnPort()` → `registerInWdDb()` がステータス系フィールドを書き込み
2. `initWdCounters()` が `PFC_WD_STATUS=operational`、カウンタ 0 (または既存値) を書き込み
3. Lua プラグインが storm を検知 → `PFC_WD_ACTION` 通知 → `initCounters()` が `PFC_WD_STATUS=stormed`、`DEADLOCK_DETECTED++`、`*_LAST=0` を書き込み
4. storm 解消 → `commitCounters(periodic=false)` が `PFC_WD_STATUS=operational`、`DEADLOCK_RESTORED++` を書き込み
5. `pfcwd stop <port>` → `stopWdOnPort()` → `PFC_WD_DETECTION_TIME`、`PFC_WD_RESTORATION_TIME`、`PFC_WD_ACTION`、`PFC_WD_STATUS` を削除。カウンタ系フィールドは残留

<!-- defaults -->
## コード由来の暗黙デフォルト

<!-- evidence: meta/_intermediate/cdb-flow/pfcwd-state-defaults.md -->

### `PFC_WD_STATUS` — 初期値 `"operational"`

`initWdCounters()` (`pfcactionhandler.cpp:192`) が PFC WD 有効化直後に `PFC_WD_QUEUE_STATUS_OPERATIONAL = "operational"` を書き込む。storm 検知時に `"stormed"` へ、storm 復旧時に `"operational"` へ遷移する。

### `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` / `_RESTORED` — 初期値 `0`

`getQueueStats()` (`pfcactionhandler.cpp:119`) で `memset(&stats, 0, ...)` によりゼロ初期化。既存エントリが COUNTERS_DB にある場合はその値を読み出して継続（再起動後もカウンタ保持）。warm-reboot 後に storm が再通知されたとき `detectCount > restoreCount` なら `detectCount` を増やさない（`pfcactionhandler.cpp:66-69`）。

### `PFC_WD_DETECTION_TIME` — `detection_time × 1000` μs

`registerInWdDb()` (`pfcwdorch.cpp:570`) が CONFIG_DB の `detection_time` (ms) を 1000 倍した値を μs 単位で書き込む。Lua プラグインがこの値を storm 検知閾値として参照する。

### `PFC_WD_RESTORATION_TIME` — 未設定時は空文字列

`pfcwdorch.cpp:572-575`: `restorationTime == 0` なら `""` を書き込む（無限待機相当）。CONFIG_DB に `restoration_time` が存在しない場合、orchagent の初期値 `restorationTime=0` がそのまま使われる。

### `PFC_WD_ACTION` — デフォルト `"drop"`

`createEntry()` (`pfcwdorch.cpp:190`) で `PfcWdAction::PFC_WD_ACTION_DROP` に初期化。CONFIG_DB に `action` フィールドが存在しない場合も `"drop"` が COUNTERS_DB に書かれる。

### `PFC_STAT_HISTORY` — デフォルト `"disable"`

`createEntry()` (`pfcwdorch.cpp:191`) で `string pfcStatHistory = "disable"` に初期化。CONFIG_DB に `pfc_stat_history` が存在しない場合も `"disable"` が書かれる。

### `*_LAST` カウンタ — storm 検知ごとにゼロリセット

`initCounters()` (`pfcactionhandler.cpp:70-74`) が storm 検知直後に `txPktLast`、`txDropPktLast`、`rxPktLast`、`rxDropPktLast` を `0` にリセット。直近 storm 期間中の差分のみが加算される。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/pfcwd-state-ordering.md -->

### 前提条件: allPortsReady() ガード

`pfcwdorch::doTask()` は `gPortsOrch->allPortsReady()` が false の間は即 return する。ポート初期化完了前は `CONFIG_DB PFC_WD` テーブルの処理がすべてブロックされる。CONFIG_DB への書き込み自体は受け付けるが、orchagent が処理するのはポート初期化完了後。[^2]

### PORT が PortsOrch に存在しなければならない

`createEntry()` は `gPortsOrch->getPort(key, port)` でポートを引くが、ポートが未登録の場合は `task_invalid_entry` を返してスキップする。`PFC_WD|<port>` の SET より先に `PORT_TABLE|<port>` が PortsOrch に取り込まれ、`allPortsReady()` が true になっている必要がある。[^3]

### PFC 有効 TC (pfcMask) が確定してから COUNTERS_DB に書き込まれる

`registerInWdDb()` は `getPortPfcWatchdogStatus()` で lossless TC マスクを取得し、有効 TC が 0 個の場合は `false` を返して COUNTERS_DB への書き込みを行わない。`PORT_QOS_MAP` や `QUEUE` テーブルが PortsOrch に反映されて PFC マスクが確定する前に `PFC_WD` が書き込まれても、COUNTERS_DB エントリは作られない。[^4]

### FlexCounter 登録と COUNTERS_DB 書き込みは同一シーケンス内

`registerInWdDb()` は COUNTERS_DB への `PFC_WD_*` フィールド書き込みと FlexCounter の `setCounterIdList()` をシリアルに実行する。COUNTERS_DB エントリが存在するタイミングで FlexCounter ポーリングも開始されるため、書き込みと計測開始の間に隙間はない。[^5]

<!-- /ordering -->

## 確認コマンド

```bash
# queue OID を取得
sonic-db-cli COUNTERS_DB hgetall COUNTERS_QUEUE_NAME_MAP | grep Ethernet0

# PFC WD 状態を確認
sonic-db-cli COUNTERS_DB hgetall COUNTERS:<queue_oid>

# pfcwd CLI
show pfcwd stats
```

## 関連リファレンス

- [CONFIG_DB: PFC_WD テーブル](./pfc-wd.md)
- [YANG: sonic-pfcwd](../yang/sonic-pfcwd.md)
- CLI: `pfcwd stats`

## 引用元

[^1]: `pfcactionhandler.cpp` および `pfcwdorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfcactionhandler.cpp>
[^2]: `pfcwdorch.cpp:64-70` — `doTask()` の `allPortsReady()` ガード. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfcwdorch.cpp>
[^3]: `pfcwdorch.cpp:192-198` — `getPort()` 失敗時の `task_invalid_entry` 返却. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfcwdorch.cpp>
[^4]: `pfcwdorch.cpp:534-555` — `registerInWdDb()` における losslessTc 空チェックと COUNTERS_DB 書き込み. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfcwdorch.cpp>
[^5]: `pfcwdorch.cpp:558-593` — COUNTERS_DB 書き込みと `setCounterIdList()` の直列実行. <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/pfcwdorch.cpp>
