# pbh — Direction A 書き込み入り口

テーブル: `PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD`

## 調査ファイル

- sonic-utilities/config/plugins/pbh.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config pbh table/rule/hash/hash-field add/del/update ...` — `config/plugins/pbh.py` が `set_entry()` を呼ぶ (sonic-utilities/config/plugins/pbh.py)

### minigraph / sonic-cfggen

minigraph.py に PBH テーブル生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での PBH マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

