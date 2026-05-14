# ntp-server — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`NTP_SERVER`

## 段階 1: Consumer 登録

- **hostcfgd**: `NTP_SERVER` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd の `ntpHandler` が `ntp.conf` の `server` ディレクティブを更新し ntpd 再起動。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。ntpd が指定サーバへ UDP 123 番で到達可能であることが前提。

## 段階 4: タイミング + 副作用

- サーバ変更後 ntpd 再起動まで数秒。新サーバとの初期同期に数分かかる場合あり。
- 副作用: mgmt VRF を使用する場合は `ip vrf exec mgmt ntpq` で状態確認が必要。
