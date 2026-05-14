# vlan-interface — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VLAN_INTERFACE`

## 段階 1: Consumer 登録

- **orchagent / IntfsOrch**: `VLAN_INTERFACE` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- IntfsOrch が VLAN L3 インタフェースの IP プレフィックスを APP_DB `INTF_TABLE` に書き込む。

## 段階 3: APPL → SAI

- IntfsOrch が `sai_router_interface_api->create_router_interface()` で VLAN に対する SAI RIF を作成。
- IP プレフィックスに対して `sai_route_api` でコネクテッドルートを作成。

## 段階 4: タイミング + 副作用

- VLAN テーブルが先に処理されている必要あり。未解決の場合は `task_need_retry`。
- 副作用: IP 削除時は関連 ARP エントリ・ルートが自動削除される。
