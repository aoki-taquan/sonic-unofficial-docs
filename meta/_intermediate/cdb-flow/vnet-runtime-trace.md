# vnet — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`VNET`

## 段階 1: Consumer 登録

- **orchagent / VNetOrch** (`sonic-swss/orchagent/vnetorch.cpp`): `VNET` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- VNetOrch が VNet 設定 (overlay / underlay VRF, VXLAN tunnel 参照) を解析。APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- VNetOrch が `sai_virtual_router_api->create_virtual_router()` で VNet 用 VRF を作成し、VXLAN トンネルと関連付け。

## 段階 4: タイミング + 副作用

- VXLAN_TUNNEL テーブルと VRF テーブルが先に処理されている必要あり。
- 副作用: VNet 削除時は関連するルート・ネクストホップが全て削除される。
