# policer — Direction A 書き込み入り口

テーブル: `POLICER`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

POLICER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `sonic-cfggen` または `acl_loader` 経由

### minigraph / sonic-cfggen

minigraph.py に POLICER 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での POLICER マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

`acl_loader/main.py` が POLICER テーブルを参照する (読み取り専用); 直接 set_entry なし — `sonic load_minigraph` での JSON 投入が主経路
<!-- /entry-points -->

