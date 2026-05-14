# route-map — Direction A 書き込み入り口

テーブル: `ROUTE_MAP`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

ROUTE_MAP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし — `sonic-cfggen` または `config load` 経由

### minigraph / sonic-cfggen

minigraph.py に ROUTE_MAP 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での ROUTE_MAP マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**sonic-bgpcfgd** `managers_rm.py` が ROUTE_MAP テーブルを監視し FRR bgpd に反映 (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py); **frrcfgd** `frrcfgd.py` も ROUTE_MAP を監視

### 死活・デッドコード

なし
<!-- /entry-points -->

