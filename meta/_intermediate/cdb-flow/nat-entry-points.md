# nat — Direction A 書き込み入り口

テーブル: `NAT_GLOBAL / NAT_POOL / NAT_BINDINGS / NAT_STATIC`

## 調査ファイル

- sonic-utilities/config/nat.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

NAT_GLOBAL / NAT_POOL / NAT_BINDINGS / NAT_STATIC テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config nat add/del ...` — `config/nat.py` が `set_entry()` で各 NAT サブテーブルを書き込む (sonic-utilities/config/nat.py)

### minigraph / sonic-cfggen

minigraph.py に NAT テーブル生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での NAT マイグレーションなし

### ビルド時デフォルト (build-time default)

`init_cfg.json.j2` にエントリなし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

