# static-route — Direction A 書き込み入り口

テーブル: `STATIC_ROUTE`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

STATIC_ROUTE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config route add/del ...` — `config/main.py` が `set_entry('STATIC_ROUTE', key, route)` を呼ぶ (sonic-utilities/config/main.py:7886–7973)

### minigraph / sonic-cfggen

minigraph.py に STATIC_ROUTE 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での STATIC_ROUTE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

**sonic-bgpcfgd** `static_rt_timer.py` が STATIC_ROUTE を監視し staticd に広告 (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/static_rt_timer.py); **frrcfgd** も STATIC_ROUTE を監視

### 死活・デッドコード

なし
<!-- /entry-points -->

