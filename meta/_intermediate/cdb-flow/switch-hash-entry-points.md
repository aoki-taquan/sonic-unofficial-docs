# switch-hash — Direction A 書き込み入り口

テーブル: `SWITCH_HASH`

## 調査ファイル

- sonic-utilities/config/plugins/sonic-hash.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SWITCH_HASH テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config switch-hash global ecmp/lag ...` — `config/plugins/sonic-hash.py` が `set_entry('SWITCH_HASH', ...)` を呼ぶ (sonic-utilities/config/plugins/sonic-hash.py)

### minigraph / sonic-cfggen

minigraph.py に SWITCH_HASH 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SWITCH_HASH マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

