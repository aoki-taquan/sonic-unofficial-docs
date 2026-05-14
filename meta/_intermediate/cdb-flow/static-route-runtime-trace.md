# static-route — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`STATIC_ROUTE`

## 段階 1: Consumer 登録

- **orchagent / StaticRouteOrch** または **bgpcfgd**: `STATIC_ROUTE` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- orchagent が APP_DB `ROUTE_TABLE` / `INTF_TABLE` を更新してルートを RouteOrch に渡す。

## 段階 3: APPL → SAI

- RouteOrch が `sai_route_api->create_route_entry()` でスタティックルートをハードウェアに書き込む。
- nexthop の ARP 解決が必要な場合は NeighOrch と連携。

## 段階 4: タイミング + 副作用

- nexthop が到達可能であれば数十 ms 以内に SAI に反映。
- 副作用: `blackhole` nexthop 設定時はパケットが静かに DROP される。
