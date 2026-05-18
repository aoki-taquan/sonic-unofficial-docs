# warm-restart ordering — Phase B 調査メモ

## 調査対象

- `sonic-swss-common/common/warm_restart.cpp` — WarmStart クラス実装
- `sonic-swss/orchagent/main.cpp` — orchagent warm start 初期化
- `sonic-swss/orchagent/orchdaemon.cpp` — warmRestoreAndSyncUp() 実装
- `sonic-swss/teamsyncd/teamsync.cpp` — teamsyncd_timer 読み取り
- `sonic-swss/fpmsyncd/fpmsyncd.cpp` — eoiu_hold_timer 読み取り
- `sonic-swss/fdbsyncd/fdbsyncd.cpp` — bgp_timer 参照

## 主要知見

1. `WARM_RESTART` テーブルの値は動的購読なし。各プロセス起動時の一回読み。
2. `WarmStart::initialize()` → `checkWarmStart()` → `getWarmStartTimer()` の順序。
3. `checkWarmStart()` は STATE_DB の `WARM_RESTART_ENABLE_TABLE` を参照（CONFIG_DB ではない）。
4. enable=false 時は `getWarmStartTimer()` がスキップされ、CONFIG_DB の timer 値は無効。
5. orchagent の warm restore: bake() × 全 Orch → doTask() × 3 イテレーション → gMirrorOrch は最後。
6. STATE_DB の起動が CONFIG_DB 参照より前提となる。

## evidence 行番号

- warm_restart.cpp L35-172: initialize / checkWarmStart / getWarmStartTimer
- orchagent/main.cpp L433-434: WarmStart::initialize + checkWarmStart
- orchdaemon.cpp L872: isWarmStart() チェック
- orchdaemon.cpp L1092-1170: warmRestoreAndSyncUp() 全体フロー
- teamsync.cpp L32-39: teamsyncd の timer 読み取りとフォールバック
- fpmsyncd.cpp L226: eoiu_hold_timer 読み取り
- fdbsyncd.cpp L115: bgp_timer 参照
