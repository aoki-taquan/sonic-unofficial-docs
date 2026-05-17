# chassis-state — 暗黙参照 (cross-table refs) 調査メモ (Phase C)

## 調査対象

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-buildimage/files/scripts/asic_status.py`

## YANG leafref

`CHASSIS_STATE_DB` テーブル群は YANG 定義対象外（CONFIG_DB ではない）。leafref は存在しない。以下はすべて実装レベルの暗黙参照。

---

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB.CHASSIS_MODULE — admin_status 参照

- **参照先テーブル**: `CONFIG_DB.CHASSIS_MODULE`
- **参照方向**: 読み取り（`admin_status` フィールド取得）
- **参照元**: `ModuleUpdater.get_module_admin_status()` (chassisd:354-362)
- **機構**: `module_db_update()` のループ内で各モジュールが ONLINE 状態のとき `get_module_admin_status(key)` を呼び出し、`admin_status == 'down'` なら CHASSIS_STATE_DB の ASIC テーブル書き込みをスキップする。
- **条件**: モジュールの `oper_status == MODULE_STATUS_ONLINE` のとき常時（10 秒ポーリング毎）
- **副作用**: `CONFIG_DB.CHASSIS_MODULE` のエントリが存在しない場合は `'up'` を返し ASIC テーブル書き込みが継続される（chassisd:362）。SmartSwitch の場合は `SmartSwitchModuleUpdater.get_module_admin_status()` が `'Empty'` を返し、`!= 'down'` 条件を満たすため書き込みが継続する（chassisd:756）。

### 2. APPL_DB.PORT_TABLE — DP state 判定

- **参照先テーブル**: `APPL_DB.PORT_TABLE`（`oper_status` フィールド）
- **参照方向**: 読み取り（各ポートの oper_status を全件走査）
- **参照元**: `DpuStateUpdater._get_data_plane_state_common()` (chassisd:1267-1275)
- **機構**: platform API `chassis.get_dataplane_state()` が `NotImplementedError` の場合に使用されるフォールバック実装。`CONFIG_DB.PORT` テーブルの全ポート名に対して `APPL_DB.PORT_TABLE.oper_status` を確認し、1 つでも `'up'` でないポートがあれば `False`（DP state = down）を返す。
- **条件**: SmartSwitch DPU 上の `DpuStateUpdater` が DP state を更新するたびに実行
- **副作用**: `CONFIG_DB.PORT` が空テーブルの場合（設定なし）は `for port in ...` ループが 0 回実行され `True`（DP up）を返す（chassisd:1270）。全ポートが `'up'` の場合のみ DP state = `'up'`。

### 3. STATE_DB.SYSTEM_READY — CP state 判定

- **参照先テーブル**: `STATE_DB.SYSTEM_READY|SYSTEM_STATE`（`Status` フィールド）
- **参照方向**: 読み取り（システム全体の起動完了フラグ）
- **参照元**: `DpuStateUpdater._get_control_plane_state_common()` (chassisd:1277-1284)
- **機構**: platform API `chassis.get_controlplane_state()` が `NotImplementedError` の場合に使用されるフォールバック実装。`STATUS` フィールドが `'up'` でなければ CP state = `'down'`。
- **条件**: SmartSwitch DPU 上の `DpuStateUpdater` が CP state を更新するたびに実行
- **副作用**: `SYSTEM_READY|SYSTEM_STATE` エントリが存在しない場合 `status=False` → `False`（CP down）。`hget` の返り値 `(False, '')` は `not status` で検知される（chassisd:1280-1282）。

### 4. CHASSIS_APP_DB — モジュール down 後のクリーンアップ対象

- **参照先**: `CHASSIS_APP_DB`（DB ID=12 の `SYSTEM_NEIGH*`, `SYSTEM_INTERFACE*`, `SYSTEM_LAG*`, `SYSTEM_LAG_ID_TABLE` 等）
- **参照方向**: 書き込み削除（Lua スクリプト経由の一括 del）
- **参照元**: `ModuleUpdater._cleanup_chassis_app_db()` (chassisd:593-658)、`module_down_chassis_db_cleanup()` (chassisd:660-682)
- **機構**: モジュール down が `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30 分` 継続した場合、supervisor が `redis_chassis.server:6380` の CHASSIS_APP_DB に対して Lua スクリプトを実行し、該当ラインカードのすべてのシステムテーブルエントリを削除する。
- **条件**: supervisor のみ（`_is_supervisor() == True`）、かつ down モジュールが supervisor 自身でない場合
- **副作用**: 削除は不可逆。ラインカードが復旧してから 30 分以内に再 up した場合は CHASSIS_APP_DB は触られない。

### 5. CHASSIS_STATE_DB.DPU_STATE — DpuStateManagerTask の自己購読

- **参照先テーブル**: `CHASSIS_STATE_DB.DPU_STATE`（自テーブル）
- **参照方向**: 読み取り（SubscriberStateTable で変化検知）
- **参照元**: `DpuStateManagerTask.task_worker()` (chassisd:1477-1533)
- **機構**: `DpuStateManagerTask` は `APPL_DB.PORT_TABLE`・`STATE_DB.SYSTEM_READY`・`CHASSIS_STATE_DB.DPU_STATE` の 3 テーブルを `swsscommon.Select` で同時購読する。DPU_STATE 変化イベント（midplane 状態変化）は `dpu_state_updater.update_state()` の追加呼び出しトリガーになる（chassisd:1506-1521）。
- **条件**: SmartSwitch DPU 上でのみ使用

---

## 参照関係サマリ

```
CHASSIS_STATE_DB テーブル群（書き込み主体: chassisd）
  ├─ [読み取り] CONFIG_DB.CHASSIS_MODULE.admin_status
  │              → module_db_update() の ASIC テーブル書き込みゲート
  ├─ [読み取り] APPL_DB.PORT_TABLE.oper_status (SmartSwitch DPU)
  │              → DpuStateUpdater が DP state を決定するフォールバック
  ├─ [読み取り] STATE_DB.SYSTEM_READY|SYSTEM_STATE.Status (SmartSwitch DPU)
  │              → DpuStateUpdater が CP state を決定するフォールバック
  ├─ [書き込み削除] CHASSIS_APP_DB (SYSTEM_NEIGH / SYSTEM_INTERFACE / SYSTEM_LAG)
  │              → モジュール down 30 分経過後に Lua スクリプトで一括削除
  └─ [自己購読] CHASSIS_STATE_DB.DPU_STATE (SmartSwitch DPU)
                 → DpuStateManagerTask が midplane 状態変化を検知して DP/CP 再評価
```

---

## Evidence

- `chassisd:354-362` — `get_module_admin_status()`: CONFIG_DB.CHASSIS_MODULE 参照
- `chassisd:444-457` — `module_db_update()`: admin_status gate for ASIC table write
- `chassisd:593-682` — `_cleanup_chassis_app_db()` / `module_down_chassis_db_cleanup()`: CHASSIS_APP_DB 削除
- `chassisd:1241-1243` — `DpuStateUpdater.__init__`: APPL_DB / STATE_DB / CHASSIS_STATE_DB 接続
- `chassisd:1267-1284` — `_get_data_plane_state_common()` / `_get_control_plane_state_common()`
- `chassisd:1477-1533` — `DpuStateManagerTask.task_worker()`: 3 テーブル同時購読
