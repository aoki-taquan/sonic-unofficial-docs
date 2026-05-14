# prefix-set — Direction A 書き込み入り口

テーブル: `PREFIX_SET`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PREFIX_SET テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `sonic-cfggen` または手動 `config load` 経由

### minigraph / sonic-cfggen

minigraph.py に PREFIX_SET 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PREFIX_SET マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**frrcfgd** `frrcfgd.py` が PREFIX_SET テーブルを監視し FRR 設定に反映 (sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:83, 2228)

### 死活・デッドコード

なし
<!-- /entry-points -->

