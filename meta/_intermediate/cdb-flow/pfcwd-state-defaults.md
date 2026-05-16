# pfcwd-state-defaults — Phase A コード由来暗黙デフォルト調査

対象: `docs/reference/config-db/pfcwd-state.md`
調査日: 2026-05-15
調査者: agent (worktree q67)

## 対象テーブル

PFC Watchdog の runtime state / counter は **COUNTERS_DB** の `COUNTERS:<queue_oid>` ハッシュに書き込まれる（STATE_DB ではない）。
書き込み主体は `sonic-swss/orchagent/pfcactionhandler.cpp` と `pfcwdorch.cpp`。

---

## フィールド列挙と初期化ソース

| フィールド名 | 書込元ファイル | 初期化タイミング |
|---|---|---|
| `PFC_WD_STATUS` | `pfcactionhandler.cpp:192` (initWdCounters) | PFC WD 登録時 (`initWdCounters`) |
| `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` | `pfcactionhandler.cpp:190` | initWdCounters / storm 検知時 |
| `PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED` | `pfcactionhandler.cpp:191` | initWdCounters / storm 復旧時 |
| `PFC_WD_QUEUE_STATS_TX_PACKETS` | `pfcactionhandler.cpp:206` | storm 発生中/復旧時の `updateWdCounters` |
| `PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS` | `pfcactionhandler.cpp:207` | 同上 |
| `PFC_WD_QUEUE_STATS_RX_PACKETS` | `pfcactionhandler.cpp:208` | 同上 |
| `PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS` | `pfcactionhandler.cpp:209` | 同上 |
| `PFC_WD_QUEUE_STATS_TX_PACKETS_LAST` | `pfcactionhandler.cpp:211` | 同上 |
| `PFC_WD_QUEUE_STATS_TX_DROPPED_PACKETS_LAST` | `pfcactionhandler.cpp:212` | 同上 |
| `PFC_WD_QUEUE_STATS_RX_PACKETS_LAST` | `pfcactionhandler.cpp:213` | 同上 |
| `PFC_WD_QUEUE_STATS_RX_DROPPED_PACKETS_LAST` | `pfcactionhandler.cpp:214` | 同上 |
| `PFC_WD_DETECTION_TIME` | `pfcwdorch.cpp:570` | registerInWdDb() — CONFIG_DB の `detection_time` × 1000 (μs 変換) |
| `PFC_WD_RESTORATION_TIME` | `pfcwdorch.cpp:572-575` | registerInWdDb() — `restorationTime==0` なら `""` (無限) |
| `PFC_WD_ACTION` | `pfcwdorch.cpp:576` | registerInWdDb() |
| `PFC_STAT_HISTORY` | `pfcwdorch.cpp:577` | registerInWdDb() |

---

## コード由来の暗黙デフォルト

### 1. `PFC_WD_STATUS` — 初期値 `"operational"`

**ソース**: `pfcactionhandler.cpp:192`
```cpp
resultFvValues.emplace_back(PFC_WD_QUEUE_STATUS, PFC_WD_QUEUE_STATUS_OPERATIONAL);
```
`initWdCounters()` が PFC WD 有効化直後に書き込む。
storm 検知時 (`initCounters()`) に `false` (= `"stormed"`) にセット。
storm 復旧時 (`commitCounters(periodic=false)`) に `true` (= `"operational"`) に戻す。

定数定義:
```cpp
#define PFC_WD_QUEUE_STATUS_OPERATIONAL "operational"
#define PFC_WD_QUEUE_STATUS_STORMED     "stormed"
```
(pfcactionhandler.cpp:10-11)

---

### 2. `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` / `_RESTORED` — 初期値 `0`

**ソース**: `pfcactionhandler.cpp:119`
```cpp
memset(&stats, 0, sizeof(PfcWdQueueStats));
stats.operational = true;
```
`getQueueStats()` でゼロ初期化。新規キューの場合はすべてカウンタ 0 から始まる。
`initWdCounters()` は既存値を読み出してそのまま書き戻すため、再起動後もカウンタが保持される。
warm-reboot 後に storm が再通知されたとき `detectCount > restoreCount` なら `detectCount` を増やさない（`pfcactionhandler.cpp:66-69`）。

---

### 3. `PFC_WD_DETECTION_TIME` — μs 換算値

**ソース**: `pfcwdorch.cpp:570`
```cpp
countersFieldValues.emplace_back("PFC_WD_DETECTION_TIME", to_string(detectionTime * 1000));
```
CONFIG_DB `PFC_WD|<port>.detection_time` (単位 ms) を 1000 倍して μs 単位でCOUNTERS_DBに書き込む。
Lua プラグインがこの値を読んで storm 検知判定に使う。

---

### 4. `PFC_WD_RESTORATION_TIME` — `restorationTime==0` で空文字列

**ソース**: `pfcwdorch.cpp:572-575`
```cpp
countersFieldValues.emplace_back("PFC_WD_RESTORATION_TIME",
        restorationTime == 0 ?
        "" :
        to_string(restorationTime * 1000));
```
`restoration_time` が CONFIG_DB に書かれていない場合、orchagent の `createEntry()` では初期値 `restorationTime=0` のまま `startWdOnPort` に渡され、COUNTERS_DB に空文字列 `""` が書かれる (無限待機)。

---

### 5. `PFC_WD_ACTION` — デフォルト `"drop"`

**ソース**: `pfcwdorch.cpp:576` + `190`
```cpp
PfcWdAction action = PfcWdAction::PFC_WD_ACTION_DROP;  // L190 初期値
// ...
countersFieldValues.emplace_back("PFC_WD_ACTION", this->serializeAction(action));
```
CONFIG_DB に `action` フィールドが存在しない場合、`PFC_WD_ACTION_DROP` が使われ、`"drop"` が COUNTERS_DB に書かれる。

---

### 6. `PFC_STAT_HISTORY` — デフォルト `"disable"`

**ソース**: `pfcwdorch.cpp:191`
```cpp
string pfcStatHistory = "disable";
```
CONFIG_DB に `pfc_stat_history` が存在しない場合、`"disable"` が COUNTERS_DB に書かれる。

---

### 7. パケットカウンタ — storm 初回時にリセット

**ソース**: `pfcactionhandler.cpp:70-74`
```cpp
wdQueueStats.txPktLast = 0;
wdQueueStats.txDropPktLast = 0;
wdQueueStats.rxPktLast = 0;
wdQueueStats.rxDropPktLast = 0;
```
`initCounters()` (storm 検知) 時に `*_LAST` カウンタがゼロリセットされる。
累積カウンタ (`TX_PACKETS` 等) はリセットされず、storm 中の差分のみが加算される。

---

## 削除タイミング

`pfcwdorch.cpp:669`:
```cpp
this->getCountersDb()->hdel(countersKey, {"PFC_WD_DETECTION_TIME", "PFC_WD_RESTORATION_TIME", "PFC_WD_ACTION", "PFC_WD_STATUS"});
```
`stopWdOnPort()` 時に設定系フィールド 4 個が削除される。カウンタ系は残留する。

---

## 検出サマリ

| フィールド | 初期値 | ソース |
|---|---|---|
| `PFC_WD_STATUS` | `"operational"` | `pfcactionhandler.cpp:192` |
| `PFC_WD_QUEUE_STATS_DEADLOCK_DETECTED` | `0` (既存値継続) | `pfcactionhandler.cpp:119,190` |
| `PFC_WD_QUEUE_STATS_DEADLOCK_RESTORED` | `0` (既存値継続) | `pfcactionhandler.cpp:119,191` |
| パケットカウンタ各種 | `0` (新規) / 差分累積 | `pfcactionhandler.cpp:100-107` |
| `*_LAST` カウンタ | storm 検知時 `0` リセット | `pfcactionhandler.cpp:70-74` |
| `PFC_WD_DETECTION_TIME` | `detection_time × 1000` μs | `pfcwdorch.cpp:570` |
| `PFC_WD_RESTORATION_TIME` | `restoration_time × 1000` μs / `""` (未設定時) | `pfcwdorch.cpp:572-575` |
| `PFC_WD_ACTION` | `"drop"` (action 未設定時) | `pfcwdorch.cpp:576,190` |
| `PFC_STAT_HISTORY` | `"disable"` (未設定時) | `pfcwdorch.cpp:577,191` |
