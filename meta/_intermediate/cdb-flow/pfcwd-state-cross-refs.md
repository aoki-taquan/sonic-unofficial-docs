# pfcwd-state cross-refs スキャンメモ (Phase C)

## 対象ファイル

- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/pfcactionhandler.cpp`
- `sonic-swss/orchagent/pfc_detect_*.lua` (各プラットフォーム)
- `sonic-swss/orchagent/pfc_restore*.lua`
- `sonic-utilities/pfcwd/main.py`

## COUNTERS_DB への書き込み元

| ファイル | 行 | 操作 | フィールド |
|---|---|---|---|
| `pfcwdorch.cpp:579` | `Table::set()` | `DETECTION_TIME`, `RESTORATION_TIME`, `ACTION`, `STAT_HISTORY` | `registerInWdDb()` 内 per-queue ループ |
| `pfcactionhandler.cpp:192` | `Table::set()` | `PFC_WD_STATUS=operational`, カウンタ 0 初期化 | `initWdCounters()` |
| `pfcwdorch.cpp:996-1033` | `hset()` to APPL_DB | storm 検知時 APPL_DB `PFC_WD_INSTORM` へ side-write | storm handler 生成時 |
| `pfcactionhandler.cpp:70-74` | `Table::set()` | `*_LAST カウンタ = 0` | `initCounters()` storm 検知時 |
| `pfcactionhandler.cpp` (commitCounters) | `Table::set()` | `DEADLOCK_RESTORED++`, `STATUS=operational` | storm 復旧時 |

## COUNTERS_DB からの読み取り元

| ファイル / コンポーネント | 読み取り対象フィールド | 用途 |
|---|---|---|
| `pfc_detect_*.lua` (全プラットフォーム) | `PFC_WD_STATUS`, `PFC_WD_ACTION`, `PFC_WD_DETECTION_TIME`, `PFC_WD_DETECTION_TIME_LEFT`, `PFC_STAT_HISTORY` | storm 検知判定・Lua 内状態管理 |
| `pfc_restore*.lua` | `PFC_WD_STATUS` | storm 復旧判定 |
| `pfcwdorch.cpp:1076-1093` | `COUNTERS_QUEUE_NAME_MAP` + per-queue ハッシュ | `initializePfcWdCountersTable()` でカウンタ引き継ぎ |
| `sonic-utilities/pfcwd/main.py:147-162` | `PFC_WD_STATUS`, `PFC_WD_QUEUE_STATS_*` | `show pfcwd stats` 表示 |

## APPL_DB 相互参照

`pfcwdorch.cpp:688` で `m_applTable = Table(APPL_DB, "PFC_WD_INSTORM")` を保持。
storm 検知時に `m_applDb->hset(key, queue_index, "storm")` を書き込み、storm 復旧時に `hdel` で削除。
warm-reboot 時に `consumer->refillToSync(m_applTable.get())` (`pfcwdorch.cpp:1108`) で APPL_DB から再読み込みし、storm 状態を復元する。

## CONFIG_DB 参照

`pfcwdorch.cpp:73` で CONFIG_DB `PFC_WD` テーブルを subscribe。
`createEntry()` が `detection_time`, `restoration_time`, `action`, `pfc_stat_history` を読み出して COUNTERS_DB へ変換・書き込む。

## YANG 参照なし

`COUNTERS:<queue_oid>` ハッシュは YANG 定義を持たないため leafref による明示的 cross-table 参照はゼロ件。
