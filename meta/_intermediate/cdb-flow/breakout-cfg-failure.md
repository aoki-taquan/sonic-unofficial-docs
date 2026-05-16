# BREAKOUT_CFG — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-breakout-cfg)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-utilities/config/main.py`, `sonic-utilities/config/config_mgmt.py`

### CLI 前処理フェーズの失敗経路 (main.py)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `platform.json` が存在しない、または拡張子が `.json` でない (`port_config.ini` 環境) | `breakout()` L5469–5471 | `[ERROR] Breakout feature is not available without platform.json file` → `click.Abort()` | 赤文字 stderr | `config/main.py:5469-5471` |
| CONFIG_DB に `BREAKOUT_CFG` テーブルが存在しない | `breakout()` L5481–5483 | `[ERROR] BREAKOUT_CFG table is NOT present in CONFIG DB` → `click.Abort()` | 赤文字 stderr | `config/main.py:5481-5483` |
| 対象 `interface_name` が `BREAKOUT_CFG` テーブルに未登録 | `breakout()` L5485–5487 | `[ERROR] {interface_name} interface is NOT present in BREAKOUT_CFG table of CONFIG DB` → `click.Abort()` | 赤文字 stderr | `config/main.py:5485-5487` |
| `target_brkout_mode` が `platform.json` の `breakout_modes` に未定義 | `_validate_interface_mode()` L199–214 | バリデーション失敗 → `return False` → `click.Abort()` | `[ERROR] ... is not a Parent port` または mode 不一致 stderr | `config/main.py:5491` |
| `del_intf_dict` が空（削除対象子ポートなし） | `breakout()` L5504–5506 | `[ERROR] del_intf_dict is None! No interfaces are there to be deleted` → `click.Abort()` | 赤文字 stderr | `config/main.py:5504-5506` |
| `add_intf_dict` が空（追加対象子ポートなし） | `breakout()` L5515–5517 | `[ERROR] port_dict is None!` → `click.Abort()` | 赤文字 stderr | `config/main.py:5515-5517` |
| 削除予定ポート名が CONFIG_DB に未登録 (`interface_name_is_valid()` 失敗) | `breakout()` L5519–5521 | `[ERROR] Interface name {intf} is invalid` → `click.Abort()` | stderr | `config/main.py:5519-5521` |

### DPB 実行フェーズの失敗経路 (config_mgmt.py)

#### _deletePorts 失敗

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| 依存テーブル (VLAN_MEMBER 等) が存在し `force=False` | `_deletePorts()` L501–503 | `deps` リストを返して `ret=False` → `breakOutPort()` が `deps, False` を返す | `config_mgmt.py:501-503` |
| YANG バリデーション (`validateConfigData()`) 失敗 | `_deletePorts()` L516 | `configToLoad=None, deps=None, ret=False` を返す | `config_mgmt.py:516` |
| ノード削除中に予期しない例外 | `_deletePorts()` except L525–528 | `LOG_ERR "Port Deletion Failed"` → `ret=False` | `config_mgmt.py:525-528` |

#### _addPorts 失敗

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `loadDefConfig=True` かつ `/etc/sonic/port_breakout_config_db.json` が欠落 | `_getDefaultConfig()` L745 → `readJsonFile()` 例外 | `LOG_ERR "getDefaultConfig Failed, Error: {}"` → 例外伝播 → `breakOutPort()` が `None, False` を返す | `config_mgmt.py:748-751` |
| YANG バリデーション (`validateConfigData()`) 失敗 (追加後) | `_addPorts()` L572 | `configToLoad=None, ret=False` を返す | `config_mgmt.py:572` |
| ポート追加中に予期しない例外 | `_addPorts()` except L583–586 | `LOG_ERR "Port Addition Failed"` → `ret=False` | `config_mgmt.py:583-586` |

#### ASIC DB ポーリングタイムアウト

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `MAX_WAIT=60` 秒以内に削除対象ポートが ASIC DB から消えない | `_verifyAsicDB()` L403–406 | `LOG_CRIT "!!! Critical Failure, Ports are not Deleted from ASIC DB, Bail Out !!!"` → `raise Exception("Ports are present in ASIC DB after {timeout} secs")` | `config_mgmt.py:403-406` |
| `_verifyAsicDB()` が例外を raise | `breakOutPort()` except L462–464 | `LOG_ERR {e}` → `return None, False` (BREAKOUT_CFG は**旧値のまま**) | `config_mgmt.py:462-464` |

#### breakOutPort / CLI 後処理の失敗

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `breakOutPort()` が `ret=False` を返す (`force=False` かつ deps あり) | `breakout_Ports()` L266–270 | `"Dependencies Exist. No further action will be taken"` → `sys.exit(1)` | `config/main.py:267-270` |
| `breakOutPort()` が `ret=False` を返す (その他失敗) | `breakout_Ports()` L271–274 | `"[ERROR] Port breakout Failed!!! Opting Out"` → `click.Abort()` | `config/main.py:271-274` |
| `breakout_Ports()` 成功後、`interface_name` が BREAKOUT_CFG から消えている | `breakout()` L5550–5553 | `[ERROR] {interface_name} is not present in 'BREAKOUT_CFG' Table!` → `click.Abort()` (稀な race condition) | `config/main.py:5550-5553` |
| `config_db.set_entry("BREAKOUT_CFG", ...)` で `ValueError` | `breakout()` L5554–5556 | `ctx.fail("Invalid ConfigDB. Error: {e}")` | `config/main.py:5554-5556` |
| 上記以外の例外 (例: DB 接続断) | `breakout()` except L5558–5559 | `"Failed to break out Port. Error: {e}"` (マゼンタ) → `sys.exit(1)` | `config/main.py:5558-5559` |

### retry・ロールバック挙動

- **retry なし**: DPB はいずれの失敗ステップでも自動 retry を行わない。全フェーズ単発実行のみ。
- **ロールバック挙動**: `_deletePorts()` 失敗時はまだ CONFIG_DB 変更が起きていないためロールバック不要。`writeConfigDB(delConfigToLoad)` 後に `_verifyAsicDB()` タイムアウトが発生した場合、PORT テーブルは削除済みだが新ポートは未追加の状態でハングし `BREAKOUT_CFG` は**旧値のまま**となる。手動での `config reload` が必要。
- **Yang モデルなしテーブルの警告**: `breakout_warnUser_extraTables()` は依存がある場合に `LOG_ERR` を syslog 出力し、ユーザー確認を要求 (`confirm=True`)。失敗時は `raise Exception("Failed in breakout_warnUser_extraTables. Error: {}")` を送出し CLI が `sys.exit(1)` する。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `click.Abort()` (前処理チェック) | 7 | `config/main.py:5471,5483,5487,5492,5505,5517,5521,5553` |
| `sys.exit(1)` (DPB 失敗) | 2 | `config/main.py:5270,5559` |
| `ctx.fail()` (ValueError) | 1 | `config/main.py:5556` |
| `LOG_ERR` (config_mgmt) | 3 | `config_mgmt.py:527,585,750` |
| `LOG_CRIT` (ASIC DB timeout) | 1 | `config_mgmt.py:404` |
| `raise Exception` (timeout) | 1 | `config_mgmt.py:406` |
| ASIC DB ポーリング (60 秒) | 1 | `config_mgmt.py:393-406` |

<!-- /failure -->
