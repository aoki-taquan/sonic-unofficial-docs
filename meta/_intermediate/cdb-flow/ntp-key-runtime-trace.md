# ntp-key — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`NTP_KEY`

## 段階 1: Consumer 登録

- **hostcfgd**: `NTP_KEY` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が `/etc/ntp.keys` を更新し、ntpd に SIGHUP または再起動を発行。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。ntpd が認証付き NTP パケット処理に鍵を使用。

## 段階 4: タイミング + 副作用

- 鍵更新後 ntpd 再起動まで数秒。鍵ロールオーバー中は NTP 認証が一時的に失敗する可能性。
