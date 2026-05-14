# tunnel — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`TUNNEL`

## 段階 1: Consumer 登録

- **orchagent / TunnelOrch** または **VxlanOrch**: `TUNNEL` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- TunnelOrch / VxlanOrch がトンネルパラメータを解析し APP_DB へ書き込む。

## 段階 3: APPL → SAI

- orchagent が `sai_tunnel_api->create_tunnel()` でトンネルオブジェクトを作成。
- VxLAN の場合は `sai_tunnel_api->create_tunnel_map()` も呼び出す。

## 段階 4: タイミング + 副作用

- 設定反映は orchagent 処理後数 ms 以内。
- 副作用: アンダーレイルートが存在しないと ECMP nexthop 解決ができずトンネルが inactive。
