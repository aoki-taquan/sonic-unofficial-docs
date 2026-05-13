# VNET / VNET_ROUTE — 値依存挙動メモ

## scope: "default" のみ
- YANG: pattern "default" — それ以外は "Invalid VRF name" エラーで reject
- 実装上 default VRF にスコープが限定される

## advertise_prefix: true / false
- true → VNET ルートプレフィクスを BGP に広告
- false → 広告しない

## vni: 0..16777215
- 必須フィールド (mandatory true)
- 同一デバイス内で重複すると orchagent が後勝ちで上書き（silent エラー）

## VNET_ROUTE.nexthop (ipv4-address-list)
- カンマ区切り複数 IP (stypes:ipv4-address-list)
- 必須

## VNET_ROUTE_TUNNEL.metric: uint8
- YANG コメント: "This field is not used for route selection, but for route classification"
- 実際の経路選択には影響しない

## VNET_ROUTE_TUNNEL.consistent_hashing_buckets: uint16
- consistent hashing バケット数
- 複数 endpoint 時の ECMP 動作に影響

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang
- sonic-swss/cfgmgr/vxlanmgr.cpp
- sonic-swss/orchagent/vnetorch.cpp
