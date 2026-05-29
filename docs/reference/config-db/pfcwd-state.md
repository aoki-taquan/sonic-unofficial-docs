---
title: PFC_WD 状態フィールド (COUNTERS_DB)
description: "PFC Watchdog の runtime 状態・カウンタフィールド。COUNTERS_DB の COUNTERS:<queue_oid> ハッシュに書き込まれ、storm 検知カウント・パケット統計・queue ステータスを保持する。"
area: reference
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

[PFC Watchdog](../../reference/glossary.md#term-pfc-watchdog) の runtime 状態・カウンタは **[COUNTERS_DB](../../reference/glossary.md#term-counters_db)** の `COUNTERS:<queue_oid>` ハッシュに書き込まれる（[STATE_DB](../../reference/glossary.md#term-state_db) ではない）。`pfcwdorch` が [CONFIG_DB](../../reference/glossary.md#term-config_db) `PFC_WD|<port>` を読み込んで [PFC](../../reference/glossary.md#term-pfc) WD を有効化した際に初期フィールドが書き込まれ、以降は storm 検知・復旧のたびに更新される。[^1]

## key 構造

```text
COUNTERS:<queue_oid>   # per-queue PFC WD カウンタ
```

`<queue_oid>` は `COUNTERS_QUEUE_NAME_MAP` で `<port>:<queue_index>` に対応する [SAI](../../reference/glossary.md#term-sai) オブジェクト ID。

## 主要フィールド

### ステータスフィールド

| フィールド | 値 | 説明 |
|---|---|---|
| `PFC_WD_STATUS` | `operational` / `stormed` | queue の現在状態。[PFC](../../reference/glossary.md#term-pfc) WD 有効化直後は `operational` |
| `PFC_WD_DETECTION_TIME` | uint (μs) | [CONFIG_DB](../../reference/glossary.md#term-config_db) `detection_time` (ms) × 1000 変換値。Lua プラグインが storm 検知判定に使用 |
| `PFC_WD_RESTORATION_TIME` | uint (μs) / `""` | [CONFIG_DB](../../reference/glossary.md#term-config_db) `restoration_time` (ms) × 1000 変換値。未設定時は `""` (無限待機) |
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

### `PFC_WD_STATUS` — 初期値 `"operational"`

`initWdCounters()` (`pfcactionhandler.cpp:192`) が [PFC](../../reference/glossary.md#term-pfc) WD 有効化直後に `PFC_WD_QUEUE_STATUS_OPERATIONAL = "operational"` を書き込む。storm 検知時に `"stormed"` へ、storm 復旧時に `"operational"` へ遷移する。

### `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` / `_RESTORED` — 初期値 `0`

`getQueueStats()` (`pfcactionhandler.cpp:119`) で `memset(&stats, 0, ...)` によりゼロ初期化。既存エントリが [COUNTERS_DB](../../reference/glossary.md#term-counters_db) にある場合はその値を読み出して継続（再起動後もカウンタ保持）。warm-reboot 後に storm が再通知されたとき `detectCount > restoreCount` なら `detectCount` を増やさない（`pfcactionhandler.cpp:66-69`）。

### `PFC_WD_DETECTION_TIME` — `detection_time × 1000` μs

`registerInWdDb()` (`pfcwdorch.cpp:570`) が CONFIG_DB の `detection_time` (ms) を 1000 倍した値を μs 単位で書き込む。Lua プラグインがこの値を storm 検知閾値として参照する。

### `PFC_WD_RESTORATION_TIME` — 未設定時は空文字列

`pfcwdorch.cpp:572-575`: `restorationTime == 0` なら `""` を書き込む（無限待機相当）。CONFIG_DB に `restoration_time` が存在しない場合、[orchagent](../../reference/glossary.md#term-orchagent) の初期値 `restorationTime=0` がそのまま使われる。

### `PFC_WD_ACTION` — デフォルト `"drop"`

`createEntry()` (`pfcwdorch.cpp:190`) で `PfcWdAction::PFC_WD_ACTION_DROP` に初期化。CONFIG_DB に `action` フィールドが存在しない場合も `"drop"` が [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に書かれる。

### `PFC_STAT_HISTORY` — デフォルト `"disable"`

`createEntry()` (`pfcwdorch.cpp:191`) で `string pfcStatHistory = "disable"` に初期化。CONFIG_DB に `pfc_stat_history` が存在しない場合も `"disable"` が書かれる。

### `*_LAST` カウンタ — storm 検知ごとにゼロリセット

`initCounters()` (`pfcactionhandler.cpp:70-74`) が storm 検知直後に `txPktLast`、`txDropPktLast`、`rxPktLast`、`rxDropPktLast` を `0` にリセット。直近 storm 期間中の差分のみが加算される。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存

`pfcwdorch` が `pfcwd start <port>` を処理して COUNTERS_DB へフィールドを書き込む際、内部で複数ステップに分かれており、consumer が中間状態を観測しうる。

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
## 暗黙参照 — `pfcwdorch` が依存する関連テーブル

`COUNTERS:<queue_oid>` ハッシュは [YANG](../../reference/glossary.md#term-yang) 定義を持たないため leafref による明示的 cross-table 参照はゼロ件。
代わりに `pfcwdorch.cpp` / `pfcactionhandler.cpp` / Lua プラグイン群から抽出した **4 系統の暗黙依存** が実装レベルの cross-table 参照となる。

### 主要テーブル / コンポーネント参照

| 参照先 (テーブル / コンポーネント) | フィールド / 条件 | 参照方向 | evidence |
|---|---|---|---|
| `CONFIG_DB:PFC_WD\|<port>` | `detection_time`, `restoration_time`, `action`, `pfc_stat_history` | 読み取り（設定値を COUNTERS_DB へ変換・書込み） | `pfcwdorch.cpp:212-233` `createEntry()` |
| `APPL_DB:PFC_WD_INSTORM` | `<port>: { <queue_index>: "storm" }` | 書き込み（storm 検知時） / 削除（storm 復旧時） / 再読み込み（warm-reboot） | `pfcwdorch.cpp:999,1016,1033,1057,1108` |
| `pfc_detect_*.lua` (全プラットフォーム Lua プラグイン) | `PFC_WD_STATUS`, `PFC_WD_ACTION`, `PFC_WD_DETECTION_TIME`, `PFC_WD_DETECTION_TIME_LEFT`, `PFC_STAT_HISTORY` | 読み取り（[FlexCounter](../../reference/glossary.md#term-flexcounter) 経由で storm 検知判定に使用） | `pfc_detect_broadcom.lua:75-82`, 他各 lua |
| `pfc_restore*.lua` (restore Lua プラグイン) | `PFC_WD_STATUS` | 読み取り（storm 復旧判定） | `pfc_restore.lua:20` |
| `sonic-utilities/pfcwd/main.py` | `PFC_WD_STATUS`, `PFC_WD_QUEUE_STATS_DEADLOCK_*`, `PFC_WD_QUEUE_STATS_TX/RX_*` | 読み取り（`show pfcwd stats` 表示） | `pfcwd/main.py:45-49,147-162` |

### 初期化ガード順序

1. `gPortsOrch->getPortPfcWatchdogStatus()` で PFC マスク取得 → lossless TC 集合が空なら COUNTERS_DB への書き込み全スキップ（`pfcwdorch.cpp:535-553`）。
2. `registerInWdDb()` 内 per-queue ループで config フィールドを先行書き込み → `initWdCounters()` がステータス・カウンタを後続書き込み（`pfcwdorch.cpp:579-601`）。
3. storm 検知時に COUNTERS_DB (`PFC_WD_STATUS=stormed`) と [APPL_DB](../../reference/glossary.md#term-appl_db) (`PFC_WD_INSTORM`) の両方へ同時書き込み。
4. warm-reboot 時は `refillToSync()` が [APPL_DB](../../reference/glossary.md#term-appl_db) `PFC_WD_INSTORM` を再読み込みして storm 状態を COUNTERS_DB に反映（`pfcwdorch.cpp:1108`）。

### 範囲外

- `COUNTERS_QUEUE_NAME_MAP` — OID 解決のための読み取り専用マップ。`pfcwdorch` は書き込まない。
- `FLEX_COUNTER_TABLE` — `pfcwdorch` は `PFC_WD` グループに counter ID リストを設定するが、`COUNTERS:<queue_oid>` フィールドへの直接参照はない。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動

`pfcwdorch` の `doTask()` はタスクステータスを `task_success` / `task_need_retry` / `task_invalid_entry` の 3 値で管理し、失敗時の挙動が種別ごとに異なる。

<!-- evidence: sonic-swss/orchagent/pfcwdorch.cpp -->

### タスク処理ステータスと対応挙動

| ステータス | 発生条件 | doTask の動作 | retry |
|-----------|---------|--------------|-------|
| `task_success` | `startWdOnPort()` / `stopWdOnPort()` 成功 | `consumer.m_toSync.erase(it++)` でキューから除去 | なし |
| `task_need_retry` | `startWdOnPort()` が `false` を返した（[FlexCounter](../../reference/glossary.md#term-flexcounter) グループ未初期化等） | `++it` でキューに残留（次回 `doTask()` で再試行） | あり（自動） |
| `task_invalid_entry` | 下記バリデーション失敗 | `consumer.m_toSync.erase(it++)` でキューから除去 | なし（永久破棄） |
| `task_failed` | `stopWdOnPort()` が `false` を返した（DEL 操作のみ） | `consumer.m_toSync.erase(it++)` でキューから除去 | なし |

### `task_invalid_entry` を返す失敗パス (`createEntry()`)

| # | 条件 | ログ | 行番号 |
|---|------|------|--------|
| 1 | `gPortsOrch->getPort()` が失敗（存在しないポート名） | `SWSS_LOG_ERROR("Invalid port interface %s")` | `pfcwdorch.cpp:195-196` |
| 2 | ポートが物理ポートでない（[LAG](../../reference/glossary.md#term-lag) / [VLAN](../../reference/glossary.md#term-vlan) 等） | `SWSS_LOG_ERROR("Interface %s is not physical port")` | `pfcwdorch.cpp:201-202` |
| 3 | `action` フィールドが `drop` / `forward` / `alert` 以外 | `SWSS_LOG_ERROR("Invalid PFC Watchdog action %s")` | `pfcwdorch.cpp:230-231` |
| 4 | Cisco 8000 プラットフォームで `forward` アクションを指定 | `SWSS_LOG_ERROR("Unsupported action %s for platform %s")` | `pfcwdorch.cpp:234-235` |
| 5 | Broadcom プラットフォームで DLR INIT 有効かつ既存ポートと `action` が不一致 | `SWSS_LOG_ERROR("Invalid PFC Watchdog action %s as switch level action %s is set")` | `pfcwdorch.cpp:260-262` |
| 6 | Broadcom + DLR + `set_switch_attribute` が [SAI](../../reference/glossary.md#term-sai) エラーを返した | `SWSS_LOG_ERROR("Failed to set switch level PFC DLR packet action rv : %d")` | `pfcwdorch.cpp:250-251` |
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

- `stopWdOnPort()` が [SAI](../../reference/glossary.md#term-sai) 操作でエラーを返した場合に発生する。
- `task_failed` はキューから除去されるため再試行は行われない。
- COUNTERS_DB の残留フィールドはそのままになる（クリーンアップ不完全の可能性あり）。

### STATE_DB / ERROR_TABLE へのフィードバックなし

`pfcwdorch` は失敗を `syslog` に記録するのみで、[STATE_DB](../../reference/glossary.md#term-state_db) / ERROR_TABLE への書き込みを行わない。失敗確認は以下のログで行う:

```bash
journalctl -u swss | grep -i "pfc watchdog\|pfcwd"
# または
sudo grep -i "pfc watchdog\|pfcwd" /var/log/syslog
```

<!-- /failure -->

<!-- constants -->
## ハードコード定数

<!-- source: sonic-swss/orchagent/pfcwdorch.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d) -->
<!-- source: sonic-swss/orchagent/pfcactionhandler.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d) -->

`pfcwdorch` / `pfcactionhandler` が COUNTERS_DB を書き込む際に利用するハードコード定数。いずれも CONFIG_DB / [YANG](../../reference/glossary.md#term-yang) では設定不可。

| 定数 | 値 | 定義箇所 | 用途 |
|------|----|---------|------|
| `PFC_WD_TC_MAX` | `8` | `pfcwdorch.cpp:28` | lossless TC スキャン上限（queue index 0–7）。PFC 未有効 TC はスキップされ COUNTERS_DB エントリが作成されない |
| `PFC_WD_DETECTION_TIME_MIN` | `100` ms | `pfcwdorch.cpp:23` | `detection_time` の下限。範囲外は `task_invalid_entry` となり書き込み不実行 |
| `PFC_WD_DETECTION_TIME_MAX` | `5000` ms | `pfcwdorch.cpp:22` | `detection_time` の上限（5 秒） |
| `PFC_WD_RESTORATION_TIME_MIN` | `100` ms | `pfcwdorch.cpp:25` | `restoration_time` の下限。同様に範囲外は書き込み不実行 |
| `PFC_WD_RESTORATION_TIME_MAX` | `60000` ms | `pfcwdorch.cpp:24` | `restoration_time` の上限（60 秒） |
| `PFC_WD_QUEUE_STATUS` | `"PFC_WD_STATUS"` | `pfcactionhandler.cpp:9` | COUNTERS_DB フィールド名リテラル。[YANG](../../reference/glossary.md#term-yang) 定義外 |
| `PFC_WD_QUEUE_STATUS_OPERATIONAL` | `"operational"` | `pfcactionhandler.cpp:10` | `PFC_WD_STATUS` の stable 状態値 |
| `PFC_WD_QUEUE_STATUS_STORMED` | `"stormed"` | `pfcactionhandler.cpp:11` | `PFC_WD_STATUS` の storm 検知状態値 |

### 定数の影響詳細

**`PFC_WD_TC_MAX = 8` による登録エントリ数制限**: `registerInWdDb()` (`pfcwdorch.cpp:542-603`) は `for (uint8_t i = 0; i < PFC_WD_TC_MAX; i++)` でポートの queue index 0–7 をスキャンする。`pfcMask` でビットが立っていない TC（PFC 未有効）はスキップされるため、COUNTERS_DB に書き込まれる `COUNTERS:<queue_oid>` エントリは実際に PFC が有効な TC 数に限定される。ポートの PFC 設定を変えずに `pfcwd start` を再実行しても、既存エントリに上書きするだけで数は変化しない。

**`detection_time` / `restoration_time` の範囲制約**: `createEntry()` (`pfcwdorch.cpp:214-223`) で `to_uint<uint32_t>(value, MIN, MAX)` を呼び出す。範囲外の値は `std::out_of_range` / 検証失敗で `task_invalid_entry` を返し、`startWdOnPort()` は呼ばれない。COUNTERS_DB には一切書き込まれない。

**フィールド名のリテラル固定**: `PFC_WD_STATUS`、`PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` 等のフィールド名はすべて C++ マクロとして `pfcactionhandler.cpp` の先頭に定義されており、YANG モデルや CONFIG_DB スキーマによる検証外に置かれている。Lua プラグインおよび `show pfcwd stats` が同じ文字列リテラルを参照することで整合性が保たれている。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込

`pfcwdorch` / `pfcactionhandler` は CONFIG_DB `PFC_WD` の SET/DEL 処理と storm イベント処理の結果として、COUNTERS_DB 以外の複数の場所へ書き込む。

### APPL_DB — `PFC_WD_INSTORM|<port>` (storm 状態の永続化)

| トリガ | 操作 | フィールド | 値 | evidence |
|--------|------|-----------|-----|----------|
| storm 検知 (`action=drop/alert/forward`) | `hset` | `<queue_index>` | `"storm"` | `pfcwdorch.cpp:998,1017,1034` |
| storm 復旧 | `hdel` | `<queue_index>` | — | `pfcwdorch.cpp:1056-1058` |

warm-reboot 後に `bake()` が `APPL_DB:PFC_WD_INSTORM` を再読み込みして storm 状態を COUNTERS_DB に反映する (`pfcwdorch.cpp:1108`)。この書き込みがない状態で warm-reboot を行うと、storm が解消されたものとして扱われる。

### SAI 経由のポート PFC マスク変更 (LossyHandler)

`action=drop` または `action=alert` 時、storm 検知で `PfcWdLossyHandler` コンストラクタ (`pfcactionhandler.cpp:541-568`) が実行される:

1. `gPortsOrch->getPortPfc(port, &pfcMask)` で現在の PFC マスクを取得
2. `pfcMask &= ~(1 << queueId)` でストームキューの PFC ビットをクリア
3. `gPortsOrch->setPortPfc(port, pfcMask)` → SAI `set_port_attribute()` でハードウェアに反映（PFC 一時無効化）

storm 復旧時 (`~PfcWdLossyHandler()`) は逆順に `pfcMask |= (1 << queueId)` で PFC を再有効化する。

!!! note "プラットフォーム例外"
    Cisco 8000 および Broadcom + DLR INIT 有効環境ではこのマスク変更をスキップ (`pfcactionhandler.cpp:549-552`)。

### SAI 経由の `SAI_QUEUE_ATTR_PFC_DLR_INIT` 設定 (DLR ハンドラ)

Broadcom プラットフォームで DLR が有効な場合、`PfcWdDlrHandler` / `PfcWdSaiDlrInitHandler` が使用される:

| タイミング | SAI 操作 | 値 | evidence |
|-----------|----------|-----|----------|
| storm 検知 (コンストラクタ) | `sai_queue_api->set_queue_attribute(queue, SAI_QUEUE_ATTR_PFC_DLR_INIT)` | `true` | `pfcactionhandler.cpp:234,277` |
| storm 復旧 (デストラクタ) | `sai_queue_api->set_queue_attribute(queue, SAI_QUEUE_ATTR_PFC_DLR_INIT)` | `false` | `pfcactionhandler.cpp:257,300` |

### SAI スイッチレベル属性設定 (Broadcom + DLR 初回登録時のみ)

Broadcom + PFC DLR INIT 有効環境で最初のポートを `pfcwd start` する際 (`pfcwdorch.cpp:244-251`):

```
sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION=<action>)
```

スイッチ全体のDLR パケットアクションを設定する。2 ポート目以降は新しい `action` が最初のポートと一致しない場合に `task_invalid_entry` を返すのみで SAI への書き込みは行わない。

### FLEX_COUNTER_DB — `PFC_WD` グループへの counter ID 登録

`registerInWdDb()` (`pfcwdorch.cpp:558-595`) が `FlexCounterTaggedCachedManager` 経由で書き込む:

| 操作 | 対象 | 内容 | evidence |
|------|------|------|----------|
| SET (pfcwd start) | port OID | `PFC_WD` グループの PORT stat ID リスト | `pfcwdorch.cpp:560` |
| SET (pfcwd start) | queue OID | `PFC_WD` グループの QUEUE stat / attr ID リスト | `pfcwdorch.cpp:587,593` |
| DEL (pfcwd stop) | port / queue OID | counter ID リストを削除 (`clearCounterIdList`) | `pfcwdorch.cpp:652,657` |

`syncd` はこの登録に従って PFC 統計を COUNTERS_DB へ書き込む。登録削除後は Lua プラグインによる storm 検知が機能しなくなる。

### SONiC events framework — `pfc-storm` イベント発行

storm 検知時に `report_pfc_storm()` (`pfcwdorch.cpp:965`) が [SONiC](../../reference/glossary.md#term-sonic) events framework 経由でイベントを発行する:

```cpp
event_publish(g_events_handle, "pfc-storm", &params);
// params: port-id, queue-index, additional_info
```

[gNMI](../../reference/glossary.md#term-gnmi) / event-driven telemetry 向けのサイドチャンネルであり、COUNTERS_DB / [APPL_DB](../../reference/glossary.md#term-appl_db) へは書き込まない。

### 副次書込なし

- **[STATE_DB](../../reference/glossary.md#term-state_db)**: `pfcwdorch` / `pfcactionhandler` は STATE_DB に書き込まない。
- **ERROR_TABLE**: 失敗時もエラーフィードバックテーブルへの書込なし。syslog のみ。
- **[ASIC_DB](../../reference/glossary.md#term-asic_db)**: SAI 経由で `syncd` が書き込む（[orchagent](../../reference/glossary.md#term-orchagent) の直接書込なし）。

<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

### Redis 購読方式

`pfcwdorch` は **2 系統の異なる通知方式**で COUNTERS_DB の `COUNTERS:<queue_oid>` フィールドへの書き込みをトリガーされる。

| 購読者 | 購読方式 | チャンネル / テーブル | 発行元 | 目的 |
|--------|---------|----------------------|--------|------|
| `pfcwdorch` (`PfcWdSwOrch`) | `NotificationConsumer` ([Redis](../../reference/glossary.md#term-redis) SUBSCRIBE) | `PFC_WD_ACTION` (COUNTERS_DB) | Lua プラグイン (`pfc_detect_<platform>.lua`) | storm 検知 / restore 通知を受信して COUNTERS_DB フィールドを更新 |
| `pfcwdorch` (`PfcWdSwOrch`) | `SubscriberStateTable` (swsscommon) | `APPL_DB:PFC_WD` | 外部コントローラ / warm-reboot refill | APPL_DB 経由の storm 状態変化を受信 |
| `pfcwdorch` (`PfcWdOrch`) | `ConsumerStateTable` (swsscommon) | `CONFIG_DB:PFC_WD` | `pfcwd` CLI / config load | CONFIG_DB の SET/DEL 変化を受信し COUNTERS_DB 初期書き込みを実行 |

### Lua プラグイン → `PFC_WD_ACTION` チャンネル → orchagent の流れ

[FlexCounter](../../reference/glossary.md#term-flexcounter) グループ `PFC_WD` の poll サイクル（デフォルト `m_pollInterval` ms）ごとに `syncd` が Lua スクリプト (`pfc_detect_<platform>.lua` / `pfc_restore.lua`) を COUNTERS_DB 上で実行する。

```
syncd FlexCounter poll (PFC_WD グループ)
  ↓ Lua: HGET COUNTERS:<queueOid> PFC_WD_STATUS / PFC_WD_DETECTION_TIME 等を参照
Lua storm 判定成功
  ↓ redis.call('PUBLISH', 'PFC_WD_ACTION', '["<queueOid>","storm"]')
  ↓ redis.call('PUBLISH', 'PFC_WD_ACTION', '["<queueOid>","restore"]')  # 復旧時
orchagent NotificationConsumer::pop() で受信
  ↓ pfcwdorch::doTask(NotificationConsumer&) → startWdActionOnQueue(event, queueId)
  ↓ PfcWdActionHandler::initCounters() / commitCounters() が COUNTERS_DB フィールドを更新
```

- `PFC_WD_ACTION` は COUNTERS_DB (`dbId=2`) 上の [Redis](../../reference/glossary.md#term-redis) Pub/Sub チャンネル名（テーブルではない）。
- ペイロードは JSON 配列 `["<queueOid>","storm"]` / `["<queueOid>","restore"]` の 2 種類（`pfcwdorch.cpp:724-728`、`pfc_detect_broadcom.lua:130,138`）。
- `NotificationConsumer::pop()` は `event` 文字列と `values` ベクターを返す。`event` が `"storm"` か `"restore"` かで `startWdActionOnQueue()` 内の分岐が決まる。

### Lua プラグインが COUNTERS_DB フィールドを直接参照する箇所

Lua スクリプトは `redis.call('HGET', 'COUNTERS:<queueOid>', ...)` で以下のフィールドを直接読み出す（write はしない）:

| フィールド | 用途 | Lua スクリプト |
|-----------|------|--------------|
| `PFC_WD_STATUS` | 現在状態確認（`operational` なら storm 検知判定を実行） | `pfc_detect_broadcom.lua:75` |
| `PFC_WD_ACTION` | storm 時のアクション取得 | `pfc_detect_broadcom.lua:76` |
| `PFC_WD_DETECTION_TIME` | storm 検知閾値 (μs) | `pfc_detect_broadcom.lua:79` |
| `PFC_WD_DETECTION_TIME_LEFT` | 残余検知時間カウントダウン | `pfc_detect_broadcom.lua:82` |
| `BIG_RED_SWITCH_MODE` | BRS（Big Red Switch）モード確認 | `pfc_detect_broadcom.lua:77` |
| `PFC_STAT_HISTORY` | storm 期間中の統計履歴有効フラグ | `pfc_detect_broadcom.lua:100` |

### warm-reboot 時の再同期

warm-reboot 後は `refillToSync()` (`pfcwdorch.cpp:1108`) が `APPL_DB:PFC_WD_INSTORM` を直接スキャンして storm 状態を復元する。通常の Pub/Sub フローを経由せず、APPL_DB のスナップショットから COUNTERS_DB フィールドを再書き込みする。

<!-- evidence: sonic-swss/orchagent/pfcwdorch.cpp:724-728 (NotificationConsumer 登録), sonic-swss/orchagent/pfc_detect_broadcom.lua:75-77,79,82,130,138 (Lua HGET/PUBLISH), sonic-swss/orchagent/pfcwdorch.cpp:890-916 (doTask NotificationConsumer 処理) -->
<!-- /pubsub -->

<!-- platform -->
## プラットフォーム / SAI Capability 差異

`pfcwdorch` はプラットフォーム (`getenv("platform")`) に応じて Lua プラグインの選択・storm ハンドラ・SAI 操作が分岐し、COUNTERS_DB への書き込みの有無や動作が変わる。

### Lua プラグイン選択 (プラットフォーム別 detect スクリプト)

`PfcWdSwOrch` コンストラクタ (`pfcwdorch.cpp:693-700`) で `pfc_detect_<platform>.lua` を動的に選択する。

| プラットフォーム値 | detect Lua | restore Lua |
|----------------|-----------|------------|
| `broadcom` | `pfc_detect_broadcom.lua` | `pfc_restore.lua` |
| `cisco-8000` | `pfc_detect_cisco-8000.lua` | `pfc_restore_cisco-8000.lua` |
| `mellanox` | `pfc_detect_mellanox.lua` | `pfc_restore.lua` |
| `barefoot` | `pfc_detect_barefoot.lua` | `pfc_restore.lua` |
| `marvell-prestera` | `pfc_detect_marvell-prestera.lua` | `pfc_restore.lua` |
| `marvell-teralynx` | `pfc_detect_marvell-teralynx.lua` | `pfc_restore.lua` |
| `clounix` | `pfc_detect_clounix.lua` | `pfc_restore.lua` |
| `nephos` | `pfc_detect_nephos.lua` | `pfc_restore.lua` |
| `vs` | `pfc_detect_vs.lua` | `pfc_restore.lua` |

Cisco 8000 のみ restore スクリプトが専用ファイルに分離されている。`platform` 環境変数が未定義の場合は `SWSS_LOG_ERROR` を出力して初期化失敗となり、COUNTERS_DB への書き込みは一切行われない。

### Cisco 8000 固有制約

| 制約 | コード | COUNTERS_DB への影響 |
|------|--------|---------------------|
| `action=forward` は拒否 | `pfcwdorch.cpp:233-235` | `task_invalid_entry` → 書き込みなし |
| storm 検知時に PFC マスク変更をスキップ | `pfcactionhandler.cpp:548-552` | `PFC_WD_STATUS=stormed` は書かれるが ハードウェア PFC ビットは変更されない |
| 専用 restore スクリプト使用 | `pfcwdorch.cpp:697-698` | restore 判定ロジックが他プラットフォームと異なる |

### Broadcom + PFC DLR INIT 有効環境

`gSwitchOrch->checkPfcDlrInitEnable()` が `true` の場合に以下の動作が変わる。

**スイッチレベル action の強制統一**: 最初の `pfcwd start` 時に `SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION` をスイッチ全体に設定する (`pfcwdorch.cpp:244-252`)。2 ポート目以降で異なる `action` を指定すると `task_invalid_entry` となり、COUNTERS_DB への書き込みが行われない (`pfcwdorch.cpp:257-262`)。

**PFC マスク変更スキップ**: DLR INIT 有効時は `PfcWdLossyHandler` が storm 検知時の `getPortPfc` / `setPortPfc` をスキップする (`pfcactionhandler.cpp:548-552`)。代わりに `SAI_QUEUE_ATTR_PFC_DLR_INIT` を `true` / `false` で切り替える DLR ハンドラを使用する (`pfcactionhandler.cpp:230, 253, 273, 296`)。

**Broadcom DLR なし** (通常構成): `PfcWdLossyHandler` が storm 検知時にハードウェア PFC マスクを変更する標準パスを使用する。

### プラットフォーム別 COUNTERS_DB 書き込みまとめ

| 条件 | COUNTERS_DB への影響 |
|------|---------------------|
| `platform` 未定義 | 初期化失敗 → 書き込みなし |
| Cisco 8000 + `action=forward` | `task_invalid_entry` → 書き込みなし |
| Broadcom + DLR + 複数ポートで `action` 不一致 | `task_invalid_entry` → 書き込みなし |
| PFC lossless TC が未設定 (全プラットフォーム) | `registerInWdDb()` が空集合で return → 書き込みなし |
| [VS](../../reference/glossary.md#term-vs) (仮想スイッチ) | 正常書き込みだが storm 検知は模擬実装 |
| その他プラットフォーム | 標準フロー通りに書き込み |

<!-- /platform -->

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

<!-- glossary-links-injected: 9fb3fca99a59 -->
