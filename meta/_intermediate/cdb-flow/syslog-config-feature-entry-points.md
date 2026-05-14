# syslog-config-feature — Direction A 書き込み入り口

テーブル: `SYSLOG_CONFIG_FEATURE`

## 調査ファイル

- sonic-utilities/config/syslog.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SYSLOG_CONFIG_FEATURE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config syslog rate-limit-feature ...` — `config/syslog.py` が SYSLOG_CONFIG_FEATURE を書き込む (sonic-utilities/config/syslog.py)

### minigraph / sonic-cfggen

minigraph.py に SYSLOG_CONFIG_FEATURE 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SYSLOG_CONFIG_FEATURE マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

