# syslog-config-feature — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SYSLOG_CONFIG_FEATURE`

## 段階 1: Consumer 登録

- **hostcfgd**: `SYSLOG_CONFIG_FEATURE` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd がコンテナ別 syslog 設定 (ログレベル, フィルタ等) を `/etc/rsyslog.d/` に書き込み rsyslog を再起動。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。syslog はコントロールプレーンのロギング機能。

## 段階 4: タイミング + 副作用

- rsyslog 再起動まで数秒。再起動中のログが欠落する可能性。
