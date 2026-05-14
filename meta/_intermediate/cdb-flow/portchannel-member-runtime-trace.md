# portchannel-member — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PORTCHANNEL_MEMBER`

## 段階 1: Consumer 登録

- **orchagent / PortsOrch**: `PORTCHANNEL_MEMBER` テーブルを `SubscriberStateTable` で購読。
- **teammgrd** (`sonic-swss/cfgmgr/teammgr.cpp`): LAG メンバの追加・削除を `teamd` に伝達。

## 段階 2: CFG → APPL 翻訳

- teammgrd が `teamd` プロセスにポートの追加/削除を UNIX ソケット経由で通知。
- APP_DB `LAG_MEMBER_TABLE` に書き込み。

## 段階 3: APPL → SAI

- PortsOrch が APP_DB を読み `sai_lag_api->create_lag_member()` / `remove_lag_member()` を呼び出し。
- LACP が有効な場合は teamd がネゴシエーションを担う。

## 段階 4: タイミング + 副作用

- メンバ追加後 LACP ネゴシエーションが完了するまで数秒 (設定依存)。
- 副作用: メンバ削除時にそのポートのトラフィックは他メンバにハッシュ再分散される。
