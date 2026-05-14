# port-storm-control — Direction A 書き込み入り口

テーブル: `PORT_STORM_CONTROL`

## 調査ファイル

- sonic-utilities/config/main.py
- sonic-utilities/scripts/storm_control.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORT_STORM_CONTROL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config storm-control ...` — `config/main.py` と `scripts/storm_control.py` が `set_entry()` を呼ぶ (sonic-utilities/config/main.py, scripts/storm_control.py)

### minigraph / sonic-cfggen

minigraph.py に PORT_STORM_CONTROL 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PORT_STORM_CONTROL マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

