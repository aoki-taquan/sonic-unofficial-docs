# prefix-list — Direction A 書き込み入り口

テーブル: `PREFIX_LIST`

## 調査ファイル

- sonic-utilities/config/bgp_cli.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PREFIX_LIST テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config bgp prefix-list ...` — `config/bgp_cli.py` が PREFIX_LIST テーブルを書き込む (sonic-utilities/config/bgp_cli.py)

### minigraph / sonic-cfggen

minigraph.py に PREFIX_LIST 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PREFIX_LIST マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**sonic-bgpcfgd** `managers_prefix_list.py` が PREFIX_LIST テーブルを監視し FRR bgpd に反映 (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py)

### 死活・デッドコード

なし
<!-- /entry-points -->

