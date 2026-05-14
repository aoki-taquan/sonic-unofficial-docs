# vnet — Direction A 書き込み入り口

テーブル: `VNET`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VNET テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `config load` または REST API 経由

### minigraph / sonic-cfggen

minigraph.py に VNET 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし (VNET は手動 JSON 投入が主経路)

### db_migrator

db_migrator.py での VNET マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

