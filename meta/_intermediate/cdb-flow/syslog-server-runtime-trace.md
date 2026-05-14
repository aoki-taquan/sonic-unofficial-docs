# syslog-server — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SYSLOG_SERVER`

## 段階 1: Consumer 登録

- **hostcfgd**: `SYSLOG_SERVER` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd の `syslogHandler` がリモート syslog サーバ宛の転送設定を `/etc/rsyslog.d/` に書き込み rsyslog 再起動。

## 段階 3: APPL → SAI

- SAI 経由なし。rsyslog が UDP/TCP 514 番でリモートサーバへ転送。

## 段階 4: タイミング + 副作用

- rsyslog 再起動まで数秒。VRF を使用する場合は rsyslog の VRF バインド設定が必要。
