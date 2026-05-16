# CHASSIS_MODULE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-chassis-module)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-platform-daemons/sonic-chassisd/scripts/chassisd`

### カード切断 (offline 遷移) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| モジュールの `oper_status` が `Online` → 非 `Online` に遷移 | `ModuleUpdater.module_db_update()` L420-434 | `down_modules` dict に登録 (`down_time` / `cleaned=False` / `slot` 記録)、ASIC テーブル更新をスキップ (`continue`) | LOG_WARNING ("Module {} (Slot {}) went off-line!") | `chassisd:420-435` |
| `notOnlineModules` リストに入ったモジュールの ASIC エントリ | `module_db_update()` L471-478 | `CHASSIS_ASIC_TABLE` から当該モジュールの全 ASIC エントリを削除 | なし | `chassisd:471-478` |
| モジュールが `CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD` (30分) 以上 down のまま | `module_down_chassis_db_cleanup()` | chassis app DB エントリをクリーンアップ。失敗時 `log_error` を出力し次周期に継続 | LOG_ERROR ("Failed to clean up chassis app db entries for {}") | `chassisd:663-664` |
| `platform API` が `NotImplementedError` を返す (`get_oper_status` 等) | `try_get()` L125-141 | fallback 値を返す: `oper_status='Offline'`, `slot=-1`, `asics=[]`, `midplane_ip='0.0.0.0'` — ASIC テーブル更新がスキップ | なし (silent fallback) | `chassisd:125-141, 488-496` |
| midplane 初期化失敗 (`init_midplane_switch()` が `False`) | `ModuleUpdater.__init__()` L309-311 | `self.midplane_initialized = False` — 処理は継続するが midplane 依存機能が無効化 | LOG_ERROR ("Chassisd midplane intialization failed") | `chassisd:309-311` |
| `get_num_modules()` が 0 を返す | `modules_num_update()` L338-341 | STATE_DB への `chassis_num_cards` 書き込みをスキップ | LOG_ERROR ("Chassisd has no modules available") | `chassisd:338-341` |

### admin_status 不正値における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `admin_state` が `MODULE_ADMIN_DOWN(0)` でも `MODULE_ADMIN_UP(1)` でもない (SmartSwitch) | `SmartSwitchModuleConfigUpdater.module_config_update()` L252-253 | `set_admin_state_gracefully()` を呼ばず、スレッド起動もしない。silent drop | LOG_WARNING ("Invalid admin_state value: {}") | `chassisd:252-253` |
| `key` が `LINE-CARD` / `FABRIC-CARD` / `SUPERVISOR` のいずれでもない (非 SmartSwitch) | `ModuleConfigUpdater.module_config_update()` L192-200 | platform API 呼び出しをスキップして `return` | LOG_ERROR ("Incorrect module-name {}. Should start with {} or {} or {}") | `chassisd:192-200` |
| `key` が `DPU` で始まらない (SmartSwitch) | `SmartSwitchModuleConfigUpdater.module_config_update()` L236-239 | platform API 呼び出しをスキップして `return` | LOG_ERROR ("Incorrect module-name {}. Should start with {}") | `chassisd:236-239` |
| `chassis.get_module_index(key)` が `INVALID_MODULE_INDEX(-1)` を返す | `module_config_update()` L202-207 (非 SS) / L241-245 (SS) | `set_admin_state()` 呼び出しをスキップして `return` | LOG_ERROR ("Unable to get module-index for key {} to set admin-state {}") | `chassisd:202-207, 241-245` |
| YANG バリデーション外の `admin_status` 値 (例: `"enabled"`) が CONFIG_DB に書き込まれた場合 | `get_module_admin_status()` L354-362 | `fvs[CHASSIS_MODULE_ADMIN_STATUS]` を文字列として返す。`module_cfg_status != 'down'` 条件を満たすため ASIC テーブル更新が継続 (意図せず up 扱い) | なし | `chassisd:354-362, 447` |

### systemd 起動失敗に関連する挙動

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| chassisd 起動時に `sonic_platform.platform.Platform()` のインポート/初期化が例外 | `get_chassis()` L143-149 | `sys.exit(CHASSIS_LOAD_ERROR=1)` — supervisord が再起動を試みる | LOG_ERROR ("Failed to load chassis due to {}") | `chassisd:143-149` |
| 非 SmartSwitch で `my_slot` または `supervisor_slot` が `INVALID_SLOT(-1)` | `ChassisD.run()` L1424-1427 | `sys.exit(CHASSIS_NOT_SUPPORTED=2)` — supervisord は再起動しない (exit 2 は non-restartable) | LOG_ERROR ("Chassisd not supported for this platform") | `chassisd:1424-1427` |
| SIGTERM 受信 (graceful shutdown) | `signal_handler()` L1351 | `exit_code = 128 + sig`、`self.stop.set()` でメインループ終了 — supervisord が非ゼロ exit code を受け取り再起動可否を判定 | なし (ログなし) | `chassisd:1351-1353` |
| FABRIC-CARD shutdown 時に chassisd が起動していない | `config/chassis_modules.py:check_config_module_state_with_timeout()` | 最大 `TIMEOUT_SECS=10` 秒待機後に `systemctl stop swss@<asic>.service` を強制実行 | なし | `config/chassis_modules.py:12` |
| main loop 内で予期しない例外が発生 (SmartSwitch DpuStateManagerTask) | `DpuStateManagerTask.task_worker()` L1400-1401 | `log_error` を出力して継続 (ループ継続、クラッシュしない) | LOG_ERROR ("Error in run: {}") | `chassisd:1400-1401` |

### SmartSwitch DPU 固有の失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `previous-reboot-cause.json` の読み込み失敗 | `retrieve_dpu_reboot_info()` L773-774 | `(None, None)` を返す — reboot cause は記録されず、DPU 状態追跡に影響なし | LOG_ERROR ("{module}: Failed to read previous-reboot-cause.json: {e}") | `chassisd:773-774` |
| `platform.json` の JSON パースエラー (`dpu_reboot_timeout` 読み込み時) | `SmartSwitchModuleUpdater.__init__()` L728-729 | `self.dpu_reboot_timeout` は `DEFAULT_DPU_REBOOT_TIMEOUT=360` 秒のまま | LOG_ERROR ("Error parsing {}: {}") | `chassisd:728-729` |
| `module_db_update()` 内で key が `DPU` 始まりでない | `SmartSwitchModuleUpdater.module_db_update()` L783-786 | `continue` でスキップ | LOG_ERROR ("Incorrect module-name {}. Should start with {}") | `chassisd:783-786` |

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `log_error` (chassisd) | 14 | `chassisd:148,196,206,237,245,311,340,430,664,719,729,731,784,1344,1401,1426` |
| `log_warning` | 2 | `chassisd:430 (went off-line!), 253 (Invalid admin_state)` |
| `sys.exit(CHASSIS_LOAD_ERROR)` | 1 | `chassisd:149` |
| `sys.exit(CHASSIS_NOT_SUPPORTED)` | 1 | `chassisd:1427` |
| `try_get` fallback (silent) | 多数 | `chassisd:202,241,309,717,1418,1419` |
| ASIC テーブル削除 (`_del`) | 1 | `chassisd:478` |

<!-- /failure -->
