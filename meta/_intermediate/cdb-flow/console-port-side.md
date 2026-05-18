# CONSOLE_PORT / CONSOLE_SWITCH — Phase F 副次 DB 書込スキャンノート

対象テーブル: `CONSOLE_PORT`, `CONSOLE_SWITCH`
Consumer: `consutil` (sonic-utilities/consutil/lib.py), `config/console.py`
スキャン範囲: consutil/lib.py DbUtils.update_state(), ConsolePortInfo.refresh(), ConsolePortProvider._init_all()

---

## 検出した副次 DB 書込

### STATE_DB への busy/idle 状態書き込み

- `DbUtils.update_state()` (lib.py:376-385): `CONSOLE_PORT|<line_num>` キーに対して STATE_DB の 3 フィールド (`state`, `pid`, `start_time`) を書き込む。
- `ConsolePortProvider._init_all(refresh=True)` (lib.py:108-121): 起動時に全 CONSOLE_PORT エントリの現在状態を STATE_DB へ書き込む (`BUSY_FLAG` または `IDLE_FLAG`)。
- `ConsolePortInfo.refresh()` (lib.py:245-267): セッション接続/切断時に STATE_DB を更新する。picocom プロセスが存在すれば `busy`、なければ `idle` に設定。
- `ConsolePortInfo.connect()` (lib.py:189-224): `refresh()` を呼ぶことで接続中に STATE_DB を更新する。

### STATE_DB 書込フィールド

| STATE_DB テーブル | key | フィールド | 値 |
|-----------------|-----|---------|-----|
| `CONSOLE_PORT` | `<line_num>` | `state` | `"busy"` / `"idle"` |
| `CONSOLE_PORT` | `<line_num>` | `pid` | picocom プロセスの PID 文字列 / `""` (idle 時) |
| `CONSOLE_PORT` | `<line_num>` | `start_time` | 接続開始日時文字列 / `""` (idle 時) |

### APPL_DB / 他 DB への書込

- なし。config/console.py は CONFIG_DB にのみ書き込む。
- consutil は CONFIG_DB を読み取り、STATE_DB に接続状態を書き込む。APPL_DB / COUNTERS_DB / ASIC_DB 等への書込は 0 件。

---

## スキャン証跡

- `consutil/lib.py:378-380`: `self._state_db.set(self._state_db.STATE_DB, key, STATE_KEY, state)` 等の直接 set 呼び出し
- `consutil/lib.py:116-118`: `_init_all(refresh=True)` での busy/idle 初期書き込み
- `consutil/lib.py:253-267`: `ConsolePortInfo.refresh()` での接続状態更新
- `config/console.py`: APPL_DB / STATE_DB への書込なし (CONFIG_DB 書込のみ)
