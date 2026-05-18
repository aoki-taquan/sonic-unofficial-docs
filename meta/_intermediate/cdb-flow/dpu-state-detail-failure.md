# dpu-state-detail — Phase D 失敗挙動 調査メモ

slug: dpu-state-detail
phase: D (failure)
source: sonic-platform-daemons/sonic-chassisd/scripts/chassisd

## 調査対象クラス

- `SmartSwitchModuleUpdater.update_dpu_state()` (chassisd:864-891)
- `SmartSwitchModuleUpdater.get_dpu_midplane_state()` (chassisd:895-906)
- `SmartSwitchModuleUpdater.__init__()` (chassisd:688-731) — midplane_initialized フラグ
- `DpuStateUpdater.update_state()` (chassisd:1300-1316)
- `DpuStateManagerTask.task_worker()` (chassisd:1477-1524)

## 主要な失敗パターン

1. **CHASSIS_STATE_DB 接続失敗**: `update_dpu_state()` は `except Exception` でキャッチして `log_error`、
   書き込みをスキップ。次サイクルで再接続。

2. **hset 途中失敗 → 部分書き込み**: `for field, value in updates.items(): chassis_state_db.hset(...)` のループ中に
   例外発生した場合、先行フィールドのみ書き込み済みで残りはスキップされる。
   midplane down パスでは midplane 3 フィールド → CP_STATE → DP_STATE の順なので、
   DP_STATE だけ古い値が残る中間状態が可能。

3. **midplane 初期化失敗**: `try_get(chassis.init_midplane_switch, default=False)` が False を返すと
   `log_error("Chassisd midplane intialization failed")` を出力して処理継続するが、
   `check_midplane_reachability()` は空振りで DPU_STATE の midplane フィールドが更新されない。

4. **platform API NotImplementedError**: `try_get` により安全側デフォルト (False) にフォールバック。
   `is_midplane_reachable()` → False → midplane down → CP/DP も down。

5. **DpuStateUpdater 内の例外**: `update_state()` はキャッチなし。例外発生時はタスクスレッドに伝播。
   ポーリングモード (`DpuChassisdDaemon` + `poll_dpu_state=True`) では main loop がクラッシュしない限り
   次サイクルで再試行。イベントモード (`DpuStateManagerTask`) では task_worker がクラッシュすると
   以後のイベント受信が停止する。

## 障害通知手段

- syslog のみ (`log_error` / `log_warning`)
- ERROR_DB への書き込みなし
- STATE_DB への障害フラグなし

## 確認コマンド

```bash
journalctl -u sonic-chassisd --no-pager -n 50
sonic-db-cli CHASSIS_STATE_DB hgetall 'DPU_STATE|DPU0'
```
