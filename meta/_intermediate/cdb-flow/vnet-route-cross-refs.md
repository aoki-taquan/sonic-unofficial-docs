# vnet-route — 暗黙参照テーブル (Phase C) 調査ノート

## 調査対象

- sonic-net/sonic-swss: orchagent/vnetorch.cpp (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 参照先テーブル / Orch の一覧

### VNET_ROUTE (underlay) — VNetRouteOrch::handleRoutes()

| 参照先 | 参照種別 | 証跡 |
|--------|---------|------|
| `VNET` (CONFIG_DB) / `VNetOrch` | `isVnetExists(vnet)` で存在確認。falseなら return false (retry) | vnetorch.cpp:1158-1163, 1492-1497 |
| peer `VNET` エントリ群 | `getPeerList()` + `isVnetExists(peer)` で peer 全件確認 | vnetorch.cpp:1166-1183 |
| `NeighOrch` (gNeighOrch) | local endpoint 時は `hasNextHop()` + `getNextHopId()` + refcount inc/dec | vnetorch.cpp:215,239,790,795,950,958-960 |
| SAI `sai_route_api` | `create_route_entry()` / `remove_route_entry()` / `set_route_entry_attribute()` | vnetorch.cpp:651,689,722 |
| CRM (gCrmOrch) | `inc/decCrmResUsedCounter(CRM_IPV4_ROUTE / CRM_IPV6_ROUTE)` | vnetorch.cpp:665,669,698,702 |

### VNET_ROUTE_TUNNEL — VNetRouteOrch::handleTunnel()

| 参照先 | 参照種別 | 証跡 |
|--------|---------|------|
| `VNET` (CONFIG_DB) / `VNetOrch` | `isVnetExists(vnet)` で存在確認 | vnetorch.cpp:1682-1687 |
| peer `VNET` エントリ群 | `getPeerList()` + `isVnetExists(peer)` で peer 全件確認 | vnetorch.cpp:1735 |
| `VxlanTunnelOrch` | `createNextHopTunnel()` / `removeNextHopTunnel()` で tunnel NH OID を解決 | vnetorch.cpp:313-335 |
| `BfdOrch` (gBfdOrch) | `endpoint_monitor` 指定時に `createBfdSession()` 経由で BFD セッション生成 | vnetorch.cpp:46,751,2046,2300 |
| SAI `sai_next_hop_group_api` | nexthop group create/remove/member add | vnetorch.cpp:808,821,849,901,921 |
| SAI `sai_route_api` | `create_route_entry()` / `remove_route_entry()` | vnetorch.cpp:651,689 |
| CRM (gCrmOrch) | `inc/decCrmResUsedCounter(CRM_NEXTHOP_GROUP / CRM_NEXTHOP_GROUP_MEMBER)` | vnetorch.cpp:821,861,917,929,2801,2885 |
| STATE_DB `VNET_RT_TUNNEL_TABLE` | tunnel 経路の active/inactive 状態を書き込む | vnetorch.cpp:745,2572,2614 |
| STATE_DB `ADVERTISE_NETWORK_TABLE` | `advertise_prefix` 設定時の BGP prefix 広告通知 | vnetorch.cpp:746,2645,2651 |

## 特記事項

- CONFIG_DB からの direct passthrough は `VNetCfgRouteOrch` が行い、依存チェックなし。
  cross-refs が発生するのは APPL_DB 購読側の `VNetRouteOrch` での SAI 投入段階。
- `VNET_ROUTE_TUNNEL` で `isLocalEp=true`（ローカルエンドポイント）の場合は
  `gNeighOrch->hasNextHop()` / `getNextHopId()` も参照する（remote tunnel NH とは別経路）。
- CRM カウンタ枯渇でも CREATE 操作は続行するが、SAI エラー返時は task_need_retry に分岐する。
