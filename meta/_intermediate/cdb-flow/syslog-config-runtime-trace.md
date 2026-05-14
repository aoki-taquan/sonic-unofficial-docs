# syslog-config — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SYSLOG_CONFIG`

## 段階 1: Consumer 登録

- **hostcfgd**: `SYSLOG_CONFIG` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd がグローバル syslog 設定 (リモートサーバ転送等) を rsyslog 設定ファイルに書き込み再起動。

## 段階 3: APPL → SAI

- SAI 経由なし。rsyslog がネットワーク経由でリモート syslog サーバへ転送。

## 段階 4: タイミング + 副作用

- 設定変更後 rsyslog 再起動まで数秒。リモートサーバ到達不能の場合はバッファリングまたはログ欠落。
