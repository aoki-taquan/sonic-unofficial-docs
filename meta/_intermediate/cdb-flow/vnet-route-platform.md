# VNET_ROUTE / VNET_ROUTE_TUNNEL — プラットフォーム差異 (Phase H)

## 調査対象

- `sonic-swss/orchagent/vnetorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/vnetorch.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/switchorch.cpp` / `switchorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 主要な分岐: Ordered ECMP

`VNetRouteOrch` が `VNET_ROUTE_TUNNEL` の ECMP Next Hop Group を作成する際、
`gSwitchOrch->checkOrderedEcmpEnable()` 結果で NHG type を決定する。

### 発生箇所

| 箇所 | 用途 |
|------|------|
| `vnetorch.cpp:804` | `create_next_hop_group` 時の `SAI_NEXT_HOP_GROUP_ATTR_TYPE` 設定 |
| `vnetorch.cpp:841` | NHG member 追加時の `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_SEQUENCE_ID` 設定 |
| `vnetorch.cpp:2778` | BFD モニタリング有効時の NHG member 更新 `SEQUENCE_ID` 設定 |

### `checkOrderedEcmpEnable()` の仕組み

`switchorch.cpp:467-501` で `ordered_ecmp=true` が SWITCH_TABLE に書かれたとき、
SAI `sai_query_attribute_enum_values_capability` で `SAI_OBJECT_TYPE_NEXT_HOP_GROUP /
SAI_NEXT_HOP_GROUP_ATTR_TYPE` を照会し、`SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_ORDERED_ECMP`
が含まれる場合のみ `m_orderedEcmpEnable = true` とする（`switchorch.h:68`）。

非対応 ASIC では `sai_query_attribute_enum_values_capability` が失敗するか対応値を返さず、
`m_orderedEcmpEnable = false` となる。

## ベンダー固有コードなし

`vnetorch.cpp` および `vnetorch.h` には `platform` 環境変数 (`getenv("platform")`) の参照、
`broadcom` / `mellanox` 等のベンダー文字列判定が一切存在しない（全行スキャン確認）。

VNET の SAI 操作（`sai_virtual_router_api` / `sai_route_api` / `sai_next_hop_group_api` /
`sai_tunnel_api`）は標準 SAI インタフェース経由で呼ばれ、ASIC 固有最適化は SAI 実装層に
委譲される。

## VNET_EXEC モード固定

`vnetorch.h:63-67` に `VNET_EXEC_VRF` / `VNET_EXEC_BRIDGE` / `VNET_EXEC_INVALID` が
定義されているが、`orchdaemon.cpp:276` では `new VNetOrch(m_applDb, APP_VNET_TABLE_NAME)`
と引数省略で呼ばれるため、デフォルト引数の `VNET_EXEC::VNET_EXEC_VRF` が常に使用される。
コミュニティ SONiC では BRIDGE モードは無効。

## VoQ / Multi-ASIC

`vnetorch.cpp` に VoQ / multi-ASIC 固有分岐は存在しない。VNET は単一 ASIC 構成を前提。
