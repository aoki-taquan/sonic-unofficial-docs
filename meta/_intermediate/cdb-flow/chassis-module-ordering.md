# CHASSIS_MODULE — Phase B 書込み順依存スキャンノート

対象テーブル: `CHASSIS_MODULE`
Consumer: `chassisd` (`ModuleConfigUpdater` / `SmartSwitchModuleConfigUpdater`)
ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
スキャン範囲: `ChassisdDaemon.run()`, `ModuleConfigUpdater.module_config_update()`, `SmartSwitchModuleConfigUpdater.module_config_update()`, `ConfigManagerTask.task_worker()`, `SmartSwitchConfigManagerTask.task_worker()`, `ModuleUpdater.module_db_update()`, `ChassisdDaemon.set_initial_dpu_admin_state()`

---

## 検出した順序依存・タイミング依存

### 1. SmartSwitch: set_initial_dpu_admin_state() — 起動時 CHASSIS_MODULE 先読みが非 SmartSwitch より早い

- `ChassisdDaemon.run()` では `is_smartswitch()` 判定後に分岐する (chassisd:1412-1420)。
- SmartSwitch では `self.set_initial_dpu_admin_state()` (chassisd:1432) を `SmartSwitchConfigManagerTask` 起動より**前**に呼ぶ。
- `set_initial_dpu_admin_state()` は CONFIG_DB の `CHASSIS_MODULE` テーブルを `get_module_admin_status()` (chassisd:1381) 経由で**ポーリング**する。
- **順序依存**: SmartSwitch 環境では chassisd が CONFIG_DB 接続前に `CHASSIS_MODULE` を参照するため、`CHASSIS_MODULE` エントリが startup 時点で CONFIG_DB に**存在しなければ** `MODULE_STATUS_EMPTY` を返し、DPU は `MODULE_ADMIN_DOWN` で起動する (chassisd:1382-1384)。
- 逆に `admin_status: up` エントリが事前に存在する場合、DPU は up 状態のまま `set_admin_state_gracefully()` が呼ばれない。
- **推奨順序**: CONFIG_DB への `CHASSIS_MODULE|DPU*` エントリ書き込みは chassisd 起動前（または`sonic-config-engine` によるテンプレート展開フェーズ）に完了させること。
- evidence: `chassisd:1364-1405, 1412-1437`

### 2. CHASSIS_APP_DB クリーンアップのタイミング依存 — モジュール down から 30 分待機

- `ModuleUpdater.module_down_chassis_db_cleanup()` はモジュールが offline になってから `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD = 30` 分経過後に CHASSIS_APP_DB (redis_chassis.server:6380) のクリーンアップを実行する (chassisd:593-680)。
- クリーンアップ対象: `SYSTEM_NEIGH`, `SYSTEM_INTERFACE`, `SYSTEM_LAG_MEMBER_TABLE`, `SYSTEM_LAG_TABLE` — ライン/ファブリックカードに関連する全 ASIC エントリ。
- **順序依存**: ラインカードを down にした直後に CHASSIS_APP_DB を参照するコンポーネント（`voqutil` 等）は古いエントリが残存する可能性がある。クリーンアップは 30 分後のため、**モジュール再起動シナリオでは旧エントリが約 30 分間 CHASSIS_APP_DB に残る**。
- CHASSIS_APP_DB 接続 (`daemon_base.db_connect("CHASSIS_APP_DB")`) は cleanup 実行時点で初めて確立し、それ以前は接続なし。
- evidence: `chassisd:593-680, 90`

### 3. 非 SmartSwitch: supervisor のみが ConfigManagerTask を持つ

- 標準モジュラーチャシスでは `supervisor_slot == my_slot` の場合のみ `ConfigManagerTask` を起動する (chassisd:1435-1437)。
- ラインカード / ファブリックカード上では `config_manager = None` となる。
- **順序依存なし**: ラインカード上の chassisd は CONFIG_DB の `CHASSIS_MODULE` テーブルを subscribe しない（読み取りのみ）。Supervisor 上の chassisd だけが `admin_status` 変化を platform API に反映する。
- evidence: `chassisd:1435-1439`

### 4. CHASSIS_MODULE 書き込みとプラットフォーム API 反映の非同期性

- `ConfigManagerTask.task_worker()` は `SubscriberStateTable` で `CHASSIS_MODULE` テーブル変更を受け取り、`module_config_update(key, admin_state)` を**同期**呼び出しする (chassisd:1154-1172)。
- SmartSwitch の `SmartSwitchConfigManagerTask` は `module_config_update` 内で `set_admin_state_gracefully()` を**別スレッド**で非同期実行する (chassisd:250-256)。
- **順序依存**: SmartSwitch では CONFIG_DB への `admin_status: up/down` 書き込みと実際の DPU 電源変化の間に不定の非同期遅延が生じる。`DEFAULT_DPU_REBOOT_TIMEOUT = 360` 秒以内に midplane が復旧しない場合は警告ログが発出される。
- STATE_DB の `CHASSIS_MODULE_TABLE` への `oper_status` 反映は 10 秒ポーリング間隔 (`CHASSIS_INFO_UPDATE_PERIOD_SECS=10`) に依存する（CONFIG_DB 書き込みから最大 10 秒遅延）。
- evidence: `chassisd:1165-1172, 248-256, 89`

### 5. DEL 操作 — 非 SmartSwitch では "up" を意味する

- `ConfigManagerTask` は `op == 'DEL'` を `MODULE_ADMIN_UP` として処理する (chassisd:1167-1168)。
- `config chassis_modules startup <name>` は `set_entry('CHASSIS_MODULE', name, None)` でエントリを**削除**する (sonic-utilities/config/chassis_modules.py:210)。
- **順序依存なし**: DEL イベントは即時 `set_admin_state(MODULE_ADMIN_UP)` を呼び出す。待機ループなし。
- SmartSwitch では `op == 'DEL'` も `MODULE_ADMIN_DOWN` として処理される (chassisd:1223-1224)。
- evidence: `chassisd:1165-1172, 1216-1228`

### 6. FABRIC-CARD shutdown の段階的停止 — ASIC サービス依存

- `config chassis_modules shutdown FABRIC-CARD*` (sonic-utilities/config/chassis_modules.py) は:
  1. `CHASSIS_MODULE|FABRIC-CARD*` に `admin_status: down` を書き込み
  2. 最大 `TIMEOUT_SECS=10` 秒待機し chassisd が platform API 呼び出しを完了するのを確認
  3. タイムアウト後に `systemctl stop swss@<asic>.service` を呼び出す
- **順序依存**: `swss@<asic>.service` 停止は chassisd の `ConfigManagerTask` が `set_admin_state(MODULE_ADMIN_DOWN)` を完了するより後（最大 10 秒後）に実行される。chassisd が未起動の場合は 10 秒タイムアウト後に強制停止。
- evidence: `sonic-utilities/config/chassis_modules.py:140-165`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `CHASSIS_MODULE|DPU*` エントリ → chassisd 起動 | SmartSwitch: 起動前に存在必須 | エントリ不在時は DPU がデフォルト down 起動 |
| 2 | ラインカード down → CHASSIS_APP_DB クリーンアップ | 30 分遅延 | 旧エントリが 30 分残存する可能性あり |
| 3 | supervisor 上のみ ConfigManagerTask 動作 | アーキテクチャ固定 | ラインカード上 chassisd は subscribe なし |
| 4 | `admin_status` 書き込み → DPU 電源変化 | SmartSwitch: 非同期スレッド | 360 秒タイムアウト; STATE_DB 反映は最大 10 秒遅延 |
| 5 | DEL → MODULE_ADMIN_UP (非 SmartSwitch) / MODULE_ADMIN_DOWN (SmartSwitch) | 即時 | プラットフォーム依存 |
| 6 | `admin_status: down` 書き込み → swss@<asic>.service 停止 | 最大 10 秒待機後に強制 | chassisd 未起動時は 10 秒後強制停止 |
