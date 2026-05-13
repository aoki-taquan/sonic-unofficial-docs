# CONFIG_DB 例外条件分析: BMP

## Consumer

- `bmpcfgd` (`sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`)
- テーブル名: `BMP` (key: `table`)

## 例外条件

### 1. 不明なフィールド → デフォルト false で初期化 (無視)
- `load()` メソッド: `common_config.get('bgp_neighbor_table', 'false')` 等で存在しないキーは `'false'` にデフォルト補完。
- スキーマ外フィールドは silently ignored。
- ソース: `bmpcfgd.py` L41-43

### 2. 設定変更のたびに openbmpd を stop → state DB クリア → start
- 設定変更時は必ず `stop_bmp()` → `reset_bmp_table()` → `start_bmp()` の順序。
- `supervisorctl stop/start openbmpd` が失敗しても例外は catch されず、bmpcfgd プロセス全体がクラッシュする可能性。
- ソース: `bmpcfgd.py` L46-49

### 3. is_true() による型強制
- `bgp_neighbor_table` / `bgp_rib_in_table` / `bgp_rib_out_table` はすべて `str(val).lower() == 'true'` で評価。
- `"True"` / `"TRUE"` / `"1"` は `false` として扱われる (`'true'` のみ有効)。

### 4. CONFIG_DB 接続失敗時: retry_on=True で無限リトライ
- `config_db.connect(wait_for_init=True, retry_on=True)` — CONFIG_DB が起動するまで無限待機。
- ソース: `bmpcfgd.py` L78
