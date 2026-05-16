# BMP — Phase A: コード由来の暗黙デフォルト調査

調査日: 2026-05-14
対象: `docs/reference/config-db/bmp.md`

## 1. フィールド一覧

| フィールド | YANG default | コード実行時 fallback | 乖離 |
|---|---|---|---|
| `bgp_neighbor_table` | `"true"` | `'false'` (bmpcfgd.py L41) | **あり** |
| `bgp_rib_in_table` | `"false"` | `'false'` (bmpcfgd.py L42) | なし |
| `bgp_rib_out_table` | `"false"` | `'false'` (bmpcfgd.py L43) | なし |

## 2. 乖離詳細

### `bgp_neighbor_table` — YANG vs 実装 discrepancy

- **YANG**: `sonic-bmp.yang` L33: `default "true"`
- **実装**: `bmpcfgd.py` L41: `common_config.get('bgp_neighbor_table', 'false')`
- **意味**: CONFIG_DB に `BMP|table` エントリが存在しない場合（初期状態 / エントリ削除後）、
  - YANG スキーマ上は neighbor table dump は有効 (`true`) のはず
  - しかし `bmpcfgd` は `false` として扱い、openbmpd は neighbor dump を送らない
- **判定**: `discrepancy-found` 相当。書き込み経路依存乖離（CLI 書き込み前は false、YANG は true）

### Python-level 初期化デフォルト

`BMPCfg.__init__()` (L33-35):
```python
self.bgp_neighbor_table  = False
self.bgp_rib_in_table  = False
self.bgp_rib_out_table  = False
```
全フィールドが `False` 初期化。`load()` 呼び出し前の瞬間的な状態だが、
YANG の `bgp_neighbor_table=true` と一貫しない。

## 3. is_true() の挙動

```python
def is_true(val):
    return str(val).lower() == 'true'
```

- `"true"` → True (唯一有効)
- `"True"`, `"TRUE"`, `"1"`, `"yes"`, `"on"` → すべて False
- YANG `stypes:boolean_type` は `"true"` / `"false"` のみ許容する enum → 実装と一致
- ただし `"True"` (大文字 T) を書いた場合、YANG バリデーションは通過せず、
  実装でも `false` 扱いになるためユーザーへの誤りが露出しにくい

## 4. CLI 書き込み時の partial-write 問題

`config/main.py` `update_bmp_table()` (L4832-4837):
```python
bmp_table = db.cfgdb.get_table('BMP')
if not bmp_table:
    bmp_table = {'table': {table_name: value}}
else:
    bmp_table['table'][table_name] = value
db.cfgdb.mod_entry('BMP', 'table', bmp_table['table'])
```

- BMP テーブルが存在しない状態で `config bmp enable bgp-neighbor-table` を実行すると、
  `bgp_rib_in_table` / `bgp_rib_out_table` は DB に存在しない状態で書き込まれる
- その後 `bmpcfgd` が `get('bgp_rib_in_table', 'false')` → `false` として扱う
- YANG default の `bgp_rib_in_table=false` / `bgp_rib_out_table=false` とは一致するが、
  `bgp_neighbor_table` を単独で enable すると他の 2 フィールドは `false` として確定する

## 5. dead field / ハードコード固定値

- なし（全フィールドは書き込み可能）

## 6. 複合必須制約

- なし（3 フィールドはすべて独立。相互排他・相互依存なし）

## 7. `bmp_handler` の全テーブル再読み込み

`BMPCfgDaemon.bmp_handler()` (L81-83):
```python
def bmp_handler(self, key, data):
    data = self.config_db.get_table(BMP_TABLE)
    self.bmpcfg.cfg_handler(data)
```
subscribe コールバックで受け取った `data` を捨てて、毎回 `get_table()` で全件再読み込み。
個別フィールドの変更でも常に 3 フィールド全部を再評価 → openbmpd 再起動が発生する。

## 8. 結論

| 種別 | フィールド | 内容 |
|---|---|---|
| YANG vs 実装 discrepancy | `bgp_neighbor_table` | YANG default=true、実装 fallback=false |
| ハードコード fallback | 全 3 フィールド | `get(..., 'false')` で YANG 非経由 false |
| is_true() 制約 | 全 3 フィールド | lowercase `'true'` のみ有効 |
| partial-write | CLI 経由書き込み | 単独フィールド更新で他フィールドが DB に未設定のまま残る可能性 |
