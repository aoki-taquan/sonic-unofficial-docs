# DPU_STATE 書込み順依存 (Phase B) — 調査メモ

slug: dpu-state
phase: B (ordering)
source: sonic-platform-daemons/sonic-chassisd/scripts/chassisd

## 調査対象コード

- `SmartSwitchModuleUpdater.update_dpu_state()` chassisd:864-891
- `DpuStateUpdater.update_state()` chassisd:1303-1316
- `DpuStateUpdater.deinit()` chassisd:1318-1320
- `DpuStateManagerTask.task_worker()` chassisd:1464-1529
- `DpuChassisdDaemon.run()` chassisd:1537-1559
- `set_initial_dpu_admin_state()` chassisd:1364-1405

## 書込み順依存まとめ

### 依存 1: 起動時初期化 → ポーリング開始 (必須先行)

set_initial_dpu_admin_state() が DPU_STATE テーブルを初期化してからポーリングループに入る。
未初期化状態での hget は None を返すため状態評価が誤動作する。

### 依存 2: midplane up → CP/DP 評価 (推奨順序)

update_dpu_state(key, 'up') は midplane のみ更新。
CP/DP は DpuStateUpdater.update_state() が別途 platform API / fallback で評価して書き込む。
midplane up 前に CP/DP 評価すると NotImplementedError → fallback ロジックに切り替わる可能性。
自動回復: 次ポーリングで正しい状態に収束。

### 依存 3: 'down' 書込み時の CP/DP 同時リセット (上書き禁止)

update_dpu_state(key, 'down') は CP/DP を同時に 'down' に設定 (chassisd:882-884)。
直後に DpuStateUpdater が 'up' を書き込むと状態不整合。
DpuStateManagerTask は前回値同一の場合スキップ (chassisd:1523-1525)。

### 依存 4: 終了順序 (推奨)

DpuStateUpdater.deinit() (CP/DP → 'down') が先行推奨。
逆順でも機能障害は発生しないが show dpu が瞬間的に Partial Online 表示する可能性。

## 結論

DPU_STATE は push 型 STATE テーブルのため CONFIG_DB 書込み順とは別軸。
主な制約は「初期化の先行」と「midplane 'down' SET が CP/DP を巻き込む」点。
