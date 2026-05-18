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

`pfcwdorch` が `pfcwd start <port>` を処理して COUNTERS_DB へフィールドを書き込む際、内部で複数ステップに分かれており、consumer が中間状態を観測しうる。

<!-- evidence: meta/_intermediate/cdb-flow/pfcwd-state-ordering.md -->

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PortsOrch による PFC マスク解決 → `registerInWdDb()` 実行 | **強制先行** | PFC マスク未解決または lossless TC 空のポートはフィールド書込みが一切行われない |
| 2 | config フィールド書込み (`DETECTION_TIME` 等) → `initWdCounters()` (`PFC_WD_STATUS`) | 先行（同一関数内） | 2 ステップ間の中間観測で `PFC_WD_STATUS` が未存在の状態が生じうる |
| 3 | `pfcwd stop` での status フィールド DEL → カウンタフィールド残留 | 非対称（status のみ削除） | `pfcwd start` 再実行後は旧カウンタ値を引き継いで継続カウント |
| 4 | storm 検知 → `PFC_WD_STATUS=stormed` + `DEADLOCK_DETECTED++` → storm 解消 → `PFC_WD_STATUS=operational` + `DEADLOCK_RESTORED++` | 2 段階遷移 | 遷移中間で `stormed` と古いカウンタが共存する一時状態あり |

### 主要な制約詳細

**PFC マスク前提 (依存 #1)**: `registerInWdDb()` (`pfcwdorch.cpp:536-553`) は冒頭で `gPortsOrch->getPortPfcWatchdogStatus()` を呼び出し、PFC が有効な lossless TC 集合を構築する。この集合が空の場合（ポートに lossless TC が未設定）は即座に `return false` となり、COUNTERS_DB への書き込みはスキップされる。`pfcwd start` コマンドが成功しても COUNTERS_DB エントリが存在しない場合はこの条件を確認すること。

**config フィールド先行書込み (依存 #2)**: per-queue ループ内で `countersTable->set(queueIdStr, {DETECTION_TIME, RESTORATION_TIME, ACTION, STAT_HISTORY})` を実行してから、続いて `PfcWdActionHandler::initWdCounters()` が `{DEADLOCK_DETECTED, DEADLOCK_RESTORED, PFC_WD_STATUS}` を書き込む（`pfcwdorch.cpp:569-601`）。両 `set()` 呼び出しの間に consumer が読み出すと、Lua プラグインが参照する config フィールドは存在するが `PFC_WD_STATUS` がまだない状態となる。

**非対称削除 (依存 #3)**: `stopWdOnPort()` (`pfcwdorch.cpp:669`) が `hdel` で削除するのは `{PFC_WD_DETECTION_TIME, PFC_WD_RESTORATION_TIME, PFC_WD_ACTION, PFC_WD_STATUS}` のみ。`DEADLOCK_DETECTED` / `DEADLOCK_RESTORED` / `TX_PACKETS` 等カウンタ系フィールドはハッシュに残留する。次回 `pfcwd start` 時に `getQueueStats()` (`pfcactionhandler.cpp:119`) が既存値を読み出して継続するため、再起動をまたいでもカウンタは蓄積し続ける。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 — `pfcwdorch` が依存する関連テーブル (Phase C)

`COUNTERS:<queue_oid>` ハッシュは YANG 定義を持たないため leafref による明示的 cross-table 参照はゼロ件。
代わりに `pfcwdorch.cpp` / `pfcactionhandler.cpp` / Lua プラグイン群から抽出した **4 系統の暗黙依存** が実装レベルの cross-table 参照となる。

<!-- evidence: meta/_intermediate/cdb-flow/pfcwd-state-cross-refs.md -->

### 主要テーブル / コンポーネント参照

| 参照先 (テーブル / コンポーネント) | フィールド / 条件 | 参照方向 | evidence |
|---|---|---|---|
| `CONFIG_DB:PFC_WD\|<port>` | `detection_time`, `restoration_time`, `action`, `pfc_stat_history` | 読み取り（設定値を COUNTERS_DB へ変換・書込み） | `pfcwdorch.cpp:212-233` `createEntry()` |
| `APPL_DB:PFC_WD_INSTORM` | `<port>: { <queue_index>: "storm" }` | 書き込み（storm 検知時） / 削除（storm 復旧時） / 再読み込み（warm-reboot） | `pfcwdorch.cpp:999,1016,1033,1057,1108` |
| `pfc_detect_*.lua` (全プラットフォーム Lua プラグイン) | `PFC_WD_STATUS`, `PFC_WD_ACTION`, `PFC_WD_DETECTION_TIME`, `PFC_WD_DETECTION_TIME_LEFT`, `PFC_STAT_HISTORY` | 読み取り（FlexCounter 経由で storm 検知判定に使用） | `pfc_detect_broadcom.lua:75-82`, 他各 lua |
| `pfc_restore*.lua` (restore Lua プラグイン) | `PFC_WD_STATUS` | 読み取り（storm 復旧判定） | `pfc_restore.lua:20` |
| `sonic-utilities/pfcwd/main.py` | `PFC_WD_STATUS`, `PFC_WD_QUEUE_STATS_DEADLOCK_*`, `PFC_WD_QUEUE_STATS_TX/RX_*` | 読み取り（`show pfcwd stats` 表示） | `pfcwd/main.py:45-49,147-162` |

### 初期化ガード順序

1. `gPortsOrch->getPortPfcWatchdogStatus()` で PFC マスク取得 → lossless TC 集合が空なら COUNTERS_DB への書き込み全スキップ（`pfcwdorch.cpp:535-553`）。
2. `registerInWdDb()` 内 per-queue ループで config フィールドを先行書き込み → `initWdCounters()` がステータス・カウンタを後続書き込み（`pfcwdorch.cpp:579-601`）。
3. storm 検知時に COUNTERS_DB (`PFC_WD_STATUS=stormed`) と APPL_DB (`PFC_WD_INSTORM`) の両方へ同時書き込み。
4. warm-reboot 時は `refillToSync()` が APPL_DB `PFC_WD_INSTORM` を再読み込みして storm 状態を COUNTERS_DB に反映（`pfcwdorch.cpp:1108`）。

### 範囲外

- `COUNTERS_QUEUE_NAME_MAP` — OID 解決のための読み取り専用マップ。`pfcwdorch` は書き込まない。
- `FLEX_COUNTER_TABLE` — `pfcwdorch` は `PFC_WD` グループに counter ID リストを設定するが、`COUNTERS:<queue_oid>` フィールドへの直接参照はない。

詳細スキャン手順と行番号一覧は `meta/_intermediate/cdb-flow/pfcwd-state-cross-refs.md` を参照。
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

`pfcwdorch` の `doTask()` はタスクステータスを `task_success` / `task_need_retry` / `task_invalid_entry` の 3 値で管理し、失敗時の挙動が種別ごとに異なる。

<!-- evidence: sonic-swss/orchagent/pfcwdorch.cpp -->

### タスク処理ステータスと対応挙動

| ステータス | 発生条件 | doTask の動作 | retry |
|-----------|---------|--------------|-------|
| `task_success` | `startWdOnPort()` / `stopWdOnPort()` 成功 | `consumer.m_toSync.erase(it++)` でキューから除去 | なし |
| `task_need_retry` | `startWdOnPort()` が `false` を返した（FlexCounter グループ未初期化等） | `++it` でキューに残留（次回 `doTask()` で再試行） | あり（自動） |
| `task_invalid_entry` | 下記バリデーション失敗 | `consumer.m_toSync.erase(it++)` でキューから除去 | なし（永久破棄） |
| `task_failed` | `stopWdOnPort()` が `false` を返した（DEL 操作のみ） | `consumer.m_toSync.erase(it++)` でキューから除去 | なし |

### `task_invalid_entry` を返す失敗パス (`createEntry()`)

| # | 条件 | ログ | 行番号 |
|---|------|------|--------|
| 1 | `gPortsOrch->getPort()` が失敗（存在しないポート名） | `SWSS_LOG_ERROR("Invalid port interface %s")` | `pfcwdorch.cpp:195-196` |
| 2 | ポートが物理ポートでない（LAG / VLAN 等） | `SWSS_LOG_ERROR("Interface %s is not physical port")` | `pfcwdorch.cpp:201-202` |
| 3 | `action` フィールドが `drop` / `forward` / `alert` 以外 | `SWSS_LOG_ERROR("Invalid PFC Watchdog action %s")` | `pfcwdorch.cpp:230-231` |
| 4 | Cisco 8000 プラットフォームで `forward` アクションを指定 | `SWSS_LOG_ERROR("Unsupported action %s for platform %s")` | `pfcwdorch.cpp:234-235` |
| 5 | Broadcom プラットフォームで DLR INIT 有効かつ既存ポートと `action` が不一致 | `SWSS_LOG_ERROR("Invalid PFC Watchdog action %s as switch level action %s is set")` | `pfcwdorch.cpp:260-262` |
| 6 | Broadcom + DLR + `set_switch_attribute` が SAI エラーを返した | `SWSS_LOG_ERROR("Failed to set switch level PFC DLR packet action rv : %d")` | `pfcwdorch.cpp:250-251` |
| 7 | 不明なフィールド名が CONFIG_DB に含まれる | `SWSS_LOG_ERROR("Failed to parse PFC Watchdog %s configuration. Unknown attribute %s.")` | `pfcwdorch.cpp:273-277` |
| 8 | フィールド値パース時に例外発生（範囲外整数等） | `SWSS_LOG_ERROR("Failed to parse PFC Watchdog %s attribute %s error: %s.")` | `pfcwdorch.cpp:282-287` |
| 9 | `detection_time` フィールドが存在しない（`detectionTime == 0`） | `SWSS_LOG_ERROR("%s missing")` | `pfcwdorch.cpp:302-303` |
| 10 | `pfc_stat_history` が `enable` / `disable` 以外 | `SWSS_LOG_ERROR("%s is invalid value for %s")` | `pfcwdorch.cpp:307-308` |

### `task_need_retry` を返す失敗パス

`startWdOnPort()` が `false` を返した場合（`pfcwdorch.cpp:313-314`）:

- `startWdOnPort()` は内部で `registerInWdDb()` を呼び出し、PFC マスク未取得など一時的な条件が揃っていない場合に `false` を返す。
- この場合、エントリはキューに残留して次回 `doTask()` で自動再試行される。
- `allPortsReady()` が `false` の場合は `doTask()` 全体が即時 return されるため、ポート初期化完了まで処理が延期される（`pfcwdorch.cpp:66-69`）。

### `task_failed` を返す失敗パス (`deleteEntry()`)

`stopWdOnPort()` が `false` を返した場合（`pfcwdorch.cpp:332-333`）:

- `stopWdOnPort()` が SAI 操作でエラーを返した場合に発生する。
- `task_failed` はキューから除去されるため再試行は行われない。
- COUNTERS_DB の残留フィールドはそのままになる（クリーンアップ不完全の可能性あり）。

### STATE_DB / ERROR_TABLE へのフィードバックなし

`pfcwdorch` は失敗を `syslog` に記録するのみで、STATE_DB / ERROR_TABLE への書き込みを行わない。失敗確認は以下のログで行う:

```bash
journalctl -u swss | grep -i "pfc watchdog\|pfcwd"
# または
sudo grep -i "pfc watchdog\|pfcwd" /var/log/syslog
```

<!-- /failure -->

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
