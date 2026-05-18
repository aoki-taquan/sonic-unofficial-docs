# pfcwd-state-ordering — Phase B 書込み順依存調査

対象: `docs/reference/config-db/pfcwd-state.md`
調査日: 2026-05-18
調査者: agent (worktree batch337)

## 対象テーブル

`COUNTERS_DB COUNTERS:<queue_oid>` — PFC Watchdog runtime state / counter ハッシュ。
書き込み主体: `sonic-swss/orchagent/pfcwdorch.cpp`, `pfcactionhandler.cpp`

---

## 検出された順序依存

### 依存 #1: PFC マスク取得 → `registerInWdDb()` 実行

`PfcWdSwOrch::registerInWdDb()` (`pfcwdorch.cpp:528`) は冒頭で
`gPortsOrch->getPortPfcWatchdogStatus(port.m_port_id, &pfcMask)` を呼び出す。
この取得が失敗した場合、または `losslessTc` が空の場合は即 `return false` となり、
COUNTERS_DB へのフィールド書き込みは一切行われない。
つまり **PortsOrch が PFC マスクを解決済みであること**が、
COUNTERS_DB エントリが存在するための前提条件となる。
(evidence: `pfcwdorch.cpp:536-553`)

### 依存 #2: config フィールド書込み → カウンタ初期化（同一 `registerInWdDb` 内の順序）

`registerInWdDb()` は per-queue ループの中で以下の 2 ステップを順に実行する:

1. `countersTable->set(queueIdStr, countersFieldValues)` — `PFC_WD_DETECTION_TIME` / `PFC_WD_RESTORATION_TIME` / `PFC_WD_ACTION` / `PFC_STAT_HISTORY` の 4 フィールドを先行書込み
2. `PfcWdActionHandler::initWdCounters(countersTable, queueIdStr)` — `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` / `PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED` / `PFC_WD_STATUS` を上書き

consumer が両ステップの中間を観測した場合、config フィールドは存在するが
`PFC_WD_STATUS` はまだ書かれていない一時状態になりうる。
(evidence: `pfcwdorch.cpp:569-601`)

### 依存 #3: `pfcwd stop` — status フィールド削除、カウンタフィールドは残留

`stopWdOnPort()` (`pfcwdorch.cpp:669`) は
`hdel(countersKey, {"PFC_WD_DETECTION_TIME", "PFC_WD_RESTORATION_TIME", "PFC_WD_ACTION", "PFC_WD_STATUS"})` を実行し、
カウンタ系フィールド (`DEADLOCK_DETECTED` 等) は削除しない。
再起動や `pfcwd start` 後に `getQueueStats()` がこれらを読み出して継続カウントする。
(evidence: `pfcwdorch.cpp:669`, `pfcactionhandler.cpp:119-180`)

### 依存 #4: storm 検知時の 2 段書込み（config 複写 → status 遷移）

storm 検知通知 (`PFC_WD_ACTION` Notifier) により `initCounters()` が呼ばれると、
まず `PFC_WD_STATUS=stormed` と `*_LAST` ゼロリセット・`DEADLOCK_DETECTED++` を書き込み、
storm 解消時に `commitCounters(periodic=false)` が `PFC_WD_STATUS=operational`
と `DEADLOCK_RESTORED++` を書き込む。
この 2 フェーズの間 consumer は `PFC_WD_STATUS=stormed` と古いカウンタを同時に観測しうる。
(evidence: `pfcactionhandler.cpp:60-74`, `pfcactionhandler.cpp:196-215`)
