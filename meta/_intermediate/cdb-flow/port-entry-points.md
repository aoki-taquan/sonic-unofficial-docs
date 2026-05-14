# port — Direction A 書き込み入り口

テーブル: `PORT`

## 調査ファイル

- sonic-utilities/config/main.py
- sonic-utilities/config/switchport.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

PORT テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface ...` — `config/main.py` が PORT テーブルを更新 (speed/mtu/fec/autoneg など); `config/switchport.py` が `set_entry('PORT', port, data)` を呼ぶ (sonic-utilities/config/switchport.py:69)

### minigraph / sonic-cfggen

**minigraph.py** が `results['PORT']` にポート一覧 (alias / speed / lanes / description) を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2515)

### REST / gNMI

REST/gNMI 書き込み経路なし (PORT はプラットフォーム初期化で確定)

### db_migrator

**db_migrator.py** が PORT テーブルのマイグレーション処理を実装 (sonic-utilities/scripts/db_migrator.py:224)

### ビルド時デフォルト (build-time default)

各プラットフォームの `port_config.ini` が `sonic-cfggen` によって PORT テーブルに変換されビルド時デフォルトとなる

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

