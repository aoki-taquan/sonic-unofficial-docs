# pfc-wd-defaults — Phase A コード由来暗黙デフォルト調査

対象: `docs/reference/config-db/pfc-wd.md`
調査日: 2026-05-14

## フィールド列挙

| フィールド | スコープ | YANG default 宣言 |
|---|---|---|
| `action` | per-port | なし |
| `detection_time` | per-port | なし |
| `restoration_time` | per-port | なし |
| `pfc_stat_history` | per-port | なし |
| `POLL_INTERVAL` | GLOBAL | なし |

YANG (`sonic-pfcwd.yang`) は全フィールドで `default` 文を持たない。

---

## コード由来の暗黙デフォルト

### 1. `action` — ハードコードデフォルト `drop`

**ソース**: `pfcwdorch.cpp:190`
```cpp
// According to requirements, drop action is default
PfcWdAction action = PfcWdAction::PFC_WD_ACTION_DROP;
```
`createEntry()` 冒頭で `action` を `PFC_WD_ACTION_DROP` に初期化。
CONFIG_DB に `action` フィールドが存在しない場合でも `drop` として動作する。
YANG では `default` 文がないため、YANG レイヤーはデフォルトを補完しない。

**`pfcwd` CLI** のデフォルトも整合:
```python
DEFAULT_ACTION = 'drop'  # main.py:41
```
`start_default()` で `action: drop` を明示書込み (`main.py:433`)。

`pfcwd start` で `--action` を省略した場合、`action` キー自体が CONFIG_DB に書き込まれないため、`createEntry()` のハードコード値 `drop` がそのまま使われる (`start_cmd()` L329-330: `if action is not None: pfcwd_info['action'] = action`)。

---

### 2. `restoration_time` — CLI による自動算出デフォルト

**ソース**: `pfcwd/main.py:333-337`
```python
if restoration_time is not None:
    pfcwd_info['restoration_time'] = restoration_time
else:
    pfcwd_info['restoration_time'] = 2 * detection_time
```
`--restoration-time` 省略時は `2 × detection_time` (ms) を自動補完してCONFIG_DBに書き込む。
orchagent 側の `createEntry()` では `restorationTime = 0` 初期化し、`restoration_time` フィールドが存在すれば上書き。`restorationTime == 0` のまま `startWdOnPort` に渡すと、`registerInWdDb()` 内で:
```cpp
countersFieldValues.emplace_back("PFC_WD_RESTORATION_TIME",
        restorationTime == 0 ? "" : to_string(restorationTime * 1000));
```
空文字列を COUNTERS_DB に書き込む（= restoration なし = 無限待機相当）。

**CONFIG_DESCRIPTION** (`main.py:55`) でも `restoration_time` の display fallback を `'infinite'` と定義しており、未設定時の意味合いを "無限" として扱っている。

---

### 3. `pfc_stat_history` — ハードコードデフォルト `disable`

**ソース**: `pfcwdorch.cpp:191`
```cpp
string pfcStatHistory = "disable";
```
`createEntry()` 冒頭で初期化。フィールド不在時は `disable` で動作。

CLI でも:
```python
DEFAULT_PFC_HISTORY_STATUS = "disable"  # main.py:42
```
`start_default()` で明示書込み (`main.py:434`)。
`start_cmd()` では `--pfc-stat-history` フラグ (is_flag) が True の場合のみ `"enable"` を書き込む (`main.py:339-340`)。

---

### 4. `POLL_INTERVAL` — 未設定時のハードコード内部値

**ソース**: `orchdaemon.cpp:24`
```cpp
#define PFC_WD_POLL_MSECS 100
```
`PfcWdSwOrch` コンストラクタへの `pollInterval` 引数として渡される。
CONFIG_DB `PFC_WD|GLOBAL` の `POLL_INTERVAL` が設定されている場合は `m_pfcwdFlexCounterManager->updateGroupPollingInterval(stoi(value))` で上書き (`pfcwdorch.cpp:356`)。
設定がなければ初期値 100 ms のままポーリングする。

CLI デフォルト:
```python
DEFAULT_POLL_INTERVAL = 200  # main.py:39
MAX_POLL_INTERVAL_TIME = 1000  # main.py:36
```
`start_default()` は `DEFAULT_POLL_INTERVAL * multiply` を計算し上限 `MAX_POLL_INTERVAL_TIME (1000)` でクランプ後、`PFC_WD|GLOBAL` に書き込む。

---

### 5. `detection_time` — YANG 必須・ハードコード検証値

YANG: 必須フィールド（`default` なし）。`createEntry()` 冒頭 `detectionTime = 0` で初期化し、フィールド不在を検出:
```cpp
if (detectionTime == 0)
{
    SWSS_LOG_ERROR("%s missing", PFC_WD_DETECTION_TIME);
    return task_process_status::task_invalid_entry;
}
```
`detection_time` なしのエントリは `task_invalid_entry` で reject される（暗黙デフォルトなし）。

---

## BIG_RED_SWITCH — 隠しフィールド

`PFC_WD|GLOBAL` にのみ書ける `BIG_RED_SWITCH` フィールド。YANG に定義なし（スキーマ外フィールド）。値は `enable`/`disable`。
`PfcWdSwOrch::setBigRedSwitchMode()` が処理 (`pfcwdorch.cpp:375-392`)。デフォルトは `m_bigRedSwitchFlag = false` (無効)。

---

## enableBigRedSwitchMode 内の action ハードコード

`enableBigRedSwitchMode()` (`pfcwdorch.cpp:505`) では、BRS モードで全 PFC 対象キューに `PfcWdAction::PFC_WD_ACTION_DROP` を強制適用:
```cpp
auto entry = m_brsEntryMap.emplace(queueId, PfcWdQueueEntry(PfcWdAction::PFC_WD_ACTION_DROP, ...)).first;
```
CONFIG_DB の `action` 設定を無視してハードコード `drop` を使用。

---

## start_default の port_num スケーリング

`main.py:421-434`:
- `port_num = len(CONFIG_DB.PORT)` を基に `multiply = max(1, (port_num-1)//32+1)` 算出
- `detection_time = 200 * multiply`, `restoration_time = 200 * multiply`
- `POLL_INTERVAL = min(200 * multiply, 1000)`

つまり、ポート数 33-64 では `multiply=2` → 400ms/400ms/400ms、65-96 では `multiply=3` → 600ms/600ms/600ms となる。

---

## 経路依存乖離

| 経路 | action デフォルト | restoration_time デフォルト |
|---|---|---|
| `pfcwd start` (--action 省略) | CONFIG_DB に書かれない → orchagent が `drop` を補完 | `2 × detection_time` を書く |
| `pfcwd start_default` | `drop` を明示書込 | `200 * multiply` を明示書込 |
| 直接 redis-cli set (action 省略) | orchagent が `drop` を補完 | `restorationTime=0` → COUNTERS_DB に `""` → 無限待機 |

---

## 検出サマリ

| 種別 | フィールド | 値 | ソース |
|---|---|---|---|
| ハードコードデフォルト | `action` | `drop` | `pfcwdorch.cpp:190` |
| ハードコードデフォルト | `pfc_stat_history` | `disable` | `pfcwdorch.cpp:191` |
| ハードコードデフォルト (初期) | `POLL_INTERVAL` | 100 ms | `orchdaemon.cpp:24` |
| CLI 算出デフォルト | `restoration_time` | `2 × detection_time` | `main.py:334` |
| CLI スケールデフォルト | `detection_time`, `restoration_time` | `200 * multiply` ms | `main.py:431` |
| BRS ハードコード | `action` (BRS 時) | `drop` 強制 | `pfcwdorch.cpp:505` |
| YANG 必須・no default | `detection_time` | なし（必須） | `pfcwdorch.cpp:300-304` |
| YANG スキーマ外フィールド | `BIG_RED_SWITCH` | YANG 外 | `pfcwdorch.cpp:358-391` |
