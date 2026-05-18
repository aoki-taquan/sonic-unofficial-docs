# DPU_STATE — Phase F 副次 DB 書込スキャンノート

対象テーブル: `CHASSIS_STATE_DB DPU_STATE|DPU<N>`
Producer: `chassisd` (`sonic-platform-daemons/sonic-chassisd/scripts/chassisd`)
スキャン範囲: `DpuStateUpdater` / `DpuStateManagerTask.task_worker()` / `SmartSwitchModuleUpdater.module_down_chassis_db_cleanup()` / `DpuChassisdDaemon.run()` の全行精読

---

## 検出した副次書き込み

### 1. DpuStateManagerTask — DPU_STATE 変化が自己フィードバックループをトリガー

`DpuStateManagerTask.task_worker()` (`chassisd:1484-1530`) は `SubscriberStateTable` で以下の 3 テーブルを購読する:

- `APPL_DB:PORT_TABLE`
- `STATE_DB:SYSTEM_READY`
- `CHASSIS_STATE_DB:DPU_STATE`

**DPU_STATE 自身の変化**もトリガーになる。`dpu_midplane_link_state` の変化通知を受けると `dpu_state_updater.update_state()` が呼ばれ、CP/DP state を再評価して DPU_STATE を**再書き込み**する可能性がある。

| 副次 DB | テーブル / キー | 書込条件 | 根拠 |
|---------|---------------|---------|------|
| `CHASSIS_STATE_DB` | `DPU_STATE\|DPU<N>` | DPU_STATE 変化通知受信後、CP/DP state が変化した場合のみ上書き | `chassisd:1506-1526` |

これは **再帰的フィードバック** ではなく、`update_state()` が前回値と比較して変化がなければ書き込みを行わないため無限ループは発生しない（`chassisd:1303-1316`）。

### 2. CHASSIS_STATE_DB のその他テーブルは変化なし

`update_dpu_state()` (`chassisd:864-891`) および `DpuStateUpdater._update_dp_dpu_state()` / `_update_cp_dpu_state()` (`chassisd:1289-1296`) が書き込むのは `DPU_STATE` テーブルのみ。

`CONFIG_DB`, `APPL_DB`, `STATE_DB`, `COUNTERS_DB`, `FLEX_COUNTER_DB` への書き込みは一切発生しない。

### 3. 副次書き込みが発生しないケース

| ケース | 理由 |
|--------|------|
| `poll_dpu_state = True` の場合 | `DpuStateManagerTask` は起動されず (`chassisd:1540-1546`)、DPU_STATE 変化によるフィードバックループなし |
| CP/DP state が変化しない場合 | `update_state()` は前回値と同一の場合は書き込みをスキップ (`chassisd:1303-1316`) |
| `module_down_chassis_db_cleanup()` 実行時 | DPU_STATE と REBOOT_CAUSE キーは**削除対象外** (`chassisd:1124`)。他の CHASSIS_STATE_DB エントリのみ削除 |

---

## 副次書き込みサマリ

| # | 副次先 DB | テーブル | 発生条件 | 根拠 |
|---|-----------|---------|---------|------|
| 1 | `CHASSIS_STATE_DB` | `DPU_STATE\|DPU<N>` | DPU_STATE 変化 → CP/DP state 再評価 → 変化があれば上書き | `chassisd:1506-1526`, `chassisd:1303-1316` |

CONFIG_DB / APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への副次書き込みは存在しない。
