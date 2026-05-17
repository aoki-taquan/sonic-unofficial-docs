# CHASSIS_STATE_DB テーブル群 — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-chassis-state2-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-platform-daemons/sonic-chassisd/scripts/chassisd`

### platform API 失敗時の DB 書き込み経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `get_oper_status()` が `NotImplementedError` | `try_get()` L125-141 | fallback `'Offline'` を返す → ASIC テーブル更新スキップ | なし | `chassisd:125-141,490` |
| `get_slot()` が `NotImplementedError` | `try_get()` L125-141 | fallback `-1` (INVALID_SLOT) → STATE_DB に `slot=-1` 書き込み | なし | `chassisd:125-141,488` |
| `get_all_asics()` が `NotImplementedError` | `try_get()` L125-141 | fallback `[]` → ASIC テーブル書き込みをスキップ | なし | `chassisd:125-141,491` |
| `get_name()` が `NotImplementedError` | `try_get()` L125-141 | fallback `'N/A'` を key として STATE_DB に書き込み | なし | `chassisd:486` |
| `get_midplane_ip()` が `NotImplementedError` | `try_get()` L125-141 | fallback `'0.0.0.0'` (INVALID_IP) → CHASSIS_MIDPLANE_INFO_TABLE に書き込み | なし | `chassisd:563` |
| `is_midplane_reachable()` が `NotImplementedError` | `try_get()` L125-141 | fallback `False` → midplane down 扱い | なし | `chassisd:564` |
| `init_midplane_switch()` が `NotImplementedError` または例外 | `try_get()` L125-141 | fallback `False` → `midplane_initialized=False`、以降 `check_midplane_reachability()` 全スキップ | `LOG_ERROR "Chassisd midplane intialization failed"` | `chassisd:309-311` |
| `get_module_index()` が `NotImplementedError` | `try_get()` L202 | fallback `-1` → `module_config_update()` が早期 return | `LOG_ERROR "Unable to get module-index for key..."` | `chassisd:202-206` |
| `set_admin_state()` が `NotImplementedError` | `try_get()` L212 | fallback `False` → platform への状態変更不実施 (silent) | なし | `chassisd:212` |

### platform.json / platform_env.conf パース失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `platform.json` が `json.JSONDecodeError` | `SmartSwitchModuleUpdater.__init__` L728 | `dpu_reboot_timeout` がデフォルト 360 秒のまま | `LOG_ERROR "Error parsing {PLATFORM_JSON_FILE}: ..."` | `chassisd:728-729` |
| `platform.json` のパース中に予期しない例外 | `SmartSwitchModuleUpdater.__init__` L730 | 同上 | `LOG_ERROR "Unexpected error: ..."` | `chassisd:730-731` |
| `platform_env.conf` が存在しない | `ModuleUpdater.__init__` L302 | `linecard_reboot_timeout` がデフォルト 180 秒のまま (silent) | なし | `chassisd:302-307` |

### REBOOT_CAUSE ファイル処理の失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `json.load()` が `json.JSONDecodeError` | `update_dpu_reboot_cause_to_db()` L1069 | 該当ファイルをスキップ; 他のファイルは継続処理 | `LOG_WARNING "Failed to decode JSON from file: ..."` | `chassisd:1069-1070` |
| ファイル処理中に `Exception` | `update_dpu_reboot_cause_to_db()` L1071 | 該当ファイルをスキップ; 他のファイルは継続処理 | `LOG_WARNING "Error processing file ..."` | `chassisd:1071-1072` |
| 対象モジュールのヒストリファイルが 0 件 | `update_dpu_reboot_cause_to_db()` L1046 | DB 書き込みなしで早期 return | `LOG_WARNING "No reboot cause history files found for module: ..."` | `chassisd:1046-1048` |
| `previous-reboot-cause.json` が存在しない | `retrieve_dpu_reboot_info()` L764 | `(None, None)` を返す; reboot 判定が `is_reboot=False` で進む | `LOG_DEBUG "{module}: previous-reboot-cause.json not found"` | `chassisd:772-773` |
| `previous-reboot-cause.json` のパースに失敗 | `retrieve_dpu_reboot_info()` L773 | `(None, None)` を返す | `LOG_ERROR "{module}: Failed to read previous-reboot-cause.json: ..."` | `chassisd:773-774` |
| `_rotate_files()` 中に `history/` ディレクトリが `FileNotFoundError` | `_rotate_files()` L1018 | `return` してローテーションを中断 (silent) | なし | `chassisd:1018-1019` |

### DPU_STATE 書き込み失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `chassis_state_db.hset()` または `db_connect()` が例外 | `update_dpu_state()` L890 | DB 書き込み不実施; `DPU_STATE` が古い値のまま | `LOG_ERROR "Unexpected error: ..."` | `chassisd:890-891` |
| `get_dpu_midplane_state()` 中に `db_connect()` / `hget()` が例外 | `get_dpu_midplane_state()` L905 | `None` を返す → `dpu_mp_state != 'up'` 判定 → `update_dpu_state()` 呼び出し | `LOG_ERROR "Unexpected error: ..."` | `chassisd:905-906` |
| `set_initial_dpu_admin_state()` 内で例外 | `ChassisdDaemon.set_initial_dpu_admin_state()` L1400 | ログ出力後に継続（当該 DPU の初期化のみスキップ） | `LOG_ERROR "Error in run: ..."` | `chassisd:1400-1401` |

### ConfigManagerTask の異常系

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sel.select()` が `swsscommon.Select.OBJECT` 以外 | `ConfigManagerTask.task_worker()` L1159 | `log_warning` 後に次のループへ続行 | `LOG_WARNING "sel.select() did not return swsscommon.Select.OBJECT"` | `chassisd:1159-1160` |
| キー名が `LINE-CARD`/`FABRIC-CARD`/`SUPERVISOR` のいずれでも始まらない | `ModuleConfigUpdater.module_config_update()` L193-199 | early return; platform API 呼び出しなし | `LOG_ERROR "Incorrect module-name ..."` | `chassisd:193-199` |
| SmartSwitch で `admin_status` が `'up'`/`'down'` 以外の値 | `SmartSwitchModuleConfigUpdater.module_config_update()` L252 | `log_warning` 後に early return | `LOG_WARNING "Invalid admin_state value: ..."` | `chassisd:252-253` |

### 検出パターン補足

- **`try_get()` はすべての `NotImplementedError` を吸収するが、それ以外の例外（`AttributeError` 等）は伝播する**。platform API の実装バグで `AttributeError` が発生した場合、`module_db_update()` ループ全体が中断される。
- **`get_name()` fallback `'N/A'` のキー衝突**: 複数モジュールで `get_name()` が失敗した場合、すべてが `'N/A'` キーで STATE_DB に上書きされる。最後に処理されたモジュールのデータだけが残る。
- **Lua クリーンアップスクリプトのエラー**: `_cleanup_chassis_app_db()` の `subprocess.Popen` が `Exception` を発生させた場合、`LOG_ERROR` 後に処理継続するが、CHASSIS_APP_DB の該当エントリが残存する（chassisd:658-664）。
- **`DpuStateUpdater.deinit()` の強制 down**: `chassisd` が SIGTERM を受信して終了する際、`deinit()` が `dpu_data_plane_state` / `dpu_control_plane_state` を `'down'` に強制設定する。この書き込み自体が失敗した場合のエラーハンドリングはなく、例外が伝播する（chassisd:1318-1320）。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERROR` (chassisd 内) | 11 | L148,206,237,244,311,719,729,731,784,891,906 |
| `LOG_WARNING` (chassisd 内) | 6 | L160,253,431,776,1047,1071 |
| `try_get()` 呼び出し | 20+ | L202,212,320-325,337,341,344,486-495,563-564,740,808,815,847-854,1082-1084 |
| 例外 catch + ログのみ (no-rethrow) | 6 | L728-731,773-774,833-834,890-891,905-906,1069-1072 |

<!-- /failure -->
