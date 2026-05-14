# voq-inband-interface — Direction A 書き込み入り口

テーブル: `VOQ_INBAND_INTERFACE`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

VOQ_INBAND_INTERFACE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - 専用 CLI なし

### minigraph / sonic-cfggen

**minigraph.py** が VOQ_INBAND_INTERFACE を生成し投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での VOQ_INBAND_INTERFACE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**sonic-bgpcfgd** `main.py` が VOQ_INBAND_INTERFACE を監視し BGP ルート配布に使用 (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py)

### 死活・デッドコード

なし
<!-- /entry-points -->

