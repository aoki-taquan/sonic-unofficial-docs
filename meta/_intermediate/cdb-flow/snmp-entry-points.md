# snmp — Direction A 書き込み入り口

テーブル: `SNMP`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SNMP テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config snmp contact add/del/modify ...` — `config/main.py` が `set_entry('SNMP', 'CONTACT', ...)` を呼ぶ (sonic-utilities/config/main.py:4483–4560)
  - `config snmp location add/del/modify ...` — `config/main.py` が `set_entry('SNMP', 'LOCATION', ...)` を呼ぶ (sonic-utilities/config/main.py:4600–4667)

### minigraph / sonic-cfggen

minigraph.py に SNMP 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SNMP マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

