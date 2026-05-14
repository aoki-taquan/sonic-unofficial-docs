# syslog-config — Direction A 書き込み入り口

テーブル: `SYSLOG_CONFIG`

## 調査ファイル

- sonic-utilities/config/syslog.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

SYSLOG_CONFIG テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config syslog rate-limit ...` / `config syslog format ...` — `config/syslog.py` が SYSLOG_CONFIG を書き込む (sonic-utilities/config/syslog.py)

### minigraph / sonic-cfggen

minigraph.py に SYSLOG_CONFIG 生成なし

### REST / gNMI

REST/gNMI 書き込み経路なし

### db_migrator

db_migrator.py での SYSLOG_CONFIG マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

