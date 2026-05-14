# pfc-wd — Direction A 書き込み入り口

テーブル: `PFC_WD`

## 調査ファイル

- sonic-utilities/pfcwd/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PFC_WD テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `pfcwd start/stop/interval ...` — `pfcwd/main.py` が `set_entry('PFC_WD', ...)` を呼ぶ (sonic-utilities/pfcwd/main.py)

### minigraph / sonic-cfggen

minigraph.py に PFC_WD 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が PFC_WD に対してマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

