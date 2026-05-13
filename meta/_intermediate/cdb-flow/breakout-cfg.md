# CONFIG_DB 例外条件分析: BREAKOUT_CFG

## Consumer

- `sonic-utilities` `config breakout` コマンド (`config/main.py`)
- `show interfaces breakout` (`show/interfaces/__init__.py`)

## 例外条件

### 1. platform.json 非存在 → Abort
- `breakout_cfg_file` が存在しないか `.json` 拡張子でない場合:
  `[ERROR] Breakout feature is not available without platform.json file` → `click.Abort()`。
- ソース: `config/main.py` L5469-5471

### 2. BREAKOUT_CFG テーブル自体が CONFIG_DB に存在しない → Abort
- `config_db.get_table('BREAKOUT_CFG')` が空 dict を返す場合:
  `[ERROR] BREAKOUT_CFG table is NOT present in CONFIG DB` → Abort。
- ソース: `config/main.py` L5479-5482

### 3. 対象 interface が BREAKOUT_CFG に存在しない → Abort
- インタフェース名が `cur_brkout_dict` のキーに存在しない:
  `[ERROR] {} interface is NOT present in BREAKOUT_CFG table of CONFIG DB` → Abort。
- ソース: `config/main.py` L5484-5486

### 4. ブレイクアウトモード検証失敗 → Abort
- `_validate_interface_mode()`: `platform.json` の interfaces に対象インタフェースが存在しない、
  または target mode がサポートされていない場合 → Abort。

### 5. del_ports が空 → Abort (設定矛盾)
- `del_intf_dict` が空の場合: `[ERROR] del_intf_dict is None! No interfaces are there to be deleted` → Abort。

### 6. Yang モデルなしテーブルへの依存ポート → ユーザー警告
- `breakout_warnUser_extraTables()`: Yang モデルが存在しないテーブルに final_delPorts への参照がある場合、
  ユーザーに警告してインタラクティブ確認を求める (CI 環境で問題になる可能性)。
- ソース: `config/main.py` L239-257

### 7. set_entry の ValueError → ctx.fail
- BREAKOUT_CFG への書き込み時 `ValueError` (スキーマ違反): `Invalid ConfigDB. Error: {}` → `ctx.fail()`。
- ソース: `config/main.py` L5553-5554

### 8. show 時の欠如 → 空表示
- `show interfaces breakout` で対象ポートが BREAKOUT_CFG に存在しない場合は
  `[Interface {}] is not present in 'BREAKOUT_CFG' Table` を表示して skip。
- ソース: `show/interfaces/__init__.py` L228-230, L282-284
