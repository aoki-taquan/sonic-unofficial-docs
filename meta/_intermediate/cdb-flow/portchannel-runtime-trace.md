# portchannel — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PORTCHANNEL`

## 段階 1: Consumer 登録

- **orchagent / PortsOrch**: `PORTCHANNEL` テーブルを `SubscriberStateTable` で購読。
- **teammgrd**: `PORTCHANNEL` テーブルを購読して `teamd` プロセスを管理。

## 段階 2: CFG → APPL 翻訳

- teammgrd が `teamd` を起動しチームデバイスを作成。APP_DB `LAG_TABLE` に書き込み。

## 段階 3: APPL → SAI

- PortsOrch が APP_DB `LAG_TABLE` を読み `sai_lag_api->create_lag()` で SAI LAG オブジェクトを作成。
- min_links / LACP タイマ設定を SAI 属性に反映。

## 段階 4: タイミング + 副作用

- teamd 起動に数秒要する。SAI LAG 作成は teamd が APP_DB に書いた後。
- 副作用: PORTCHANNEL 削除時はメンバポートを先に削除しないと `non-empty LAG` エラー。
