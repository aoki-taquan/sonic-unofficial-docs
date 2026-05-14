# ntp-server — Direction A 書き込み入り口

テーブル: `NTP_SERVER`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

NTP_SERVER テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config ntp add/del <ip>` — `config/main.py` が `set_entry('NTP_SERVER', ntp_ip_address, ...)` を呼ぶ (sonic-utilities/config/main.py:9008, 9027)

### minigraph / sonic-cfggen

**minigraph.py** が `results['NTP_SERVER']` に iburst=on でサーバ一覧を投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2646)

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での NTP_SERVER マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

