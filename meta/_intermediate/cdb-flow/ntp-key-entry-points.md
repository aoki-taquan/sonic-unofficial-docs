# ntp-key — Direction A 書き込み入り口

テーブル: `NTP_KEY`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

NTP_KEY テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config ntp authentication-key add/del ...` — `config/main.py` が NTP_KEY を書き込む (sonic-utilities/config/main.py)

### minigraph / sonic-cfggen

minigraph.py に NTP_KEY 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での NTP_KEY マイグレーションなし

### ビルド時デフォルト (build-time default)

`files/image_config/chrony/chrony.keys.j2` が NTP_KEY を参照して chrony.keys を生成するが、逆方向の DB 書き込みではない

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

