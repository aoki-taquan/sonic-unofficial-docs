# portchannel — Direction A 書き込み入り口

テーブル: `PORTCHANNEL`

## 調査ファイル

- sonic-utilities/config/main.py
- sonic-utilities/config/switchport.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORTCHANNEL テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config portchannel add/del ...` — `config/main.py` が `set_entry('PORTCHANNEL', portchannel_name, fvs)` を呼ぶ (sonic-utilities/config/main.py:2865, 2900)
  - `config/switchport.py` が `set_entry('PORTCHANNEL', port, data)` を呼ぶ (sonic-utilities/config/switchport.py:72, 122)

### minigraph / sonic-cfggen

**minigraph.py** が `results['PORTCHANNEL']` にポートチャネル一覧を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2546)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

**db_migrator.py** が PORTCHANNEL のマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py:1157)

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

