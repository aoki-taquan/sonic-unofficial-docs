# VNET_ROUTE / VNET_ROUTE_TUNNEL — 書込み順依存調査メモ (Phase B)

## 調査対象

- `sonic-net/sonic-swss` `orchagent/vnetorch.cpp`

## 検出された順序依存

1. **VXLAN_TUNNEL → VNET → VNET_ROUTE***: `VNetOrch::addOperation()` が `isTunnelExists(tunnel)` でチェック (vnetorch.cpp:497-503)
2. **VNET → VNET_ROUTE / VNET_ROUTE_TUNNEL**: `doRouteTask()` が `isVnetExists(vnet)` でチェック (vnetorch.cpp:1158-1163, 1492-1497)
3. **peer VNET 全件 → 経路処理**: `isVnetExists(peer)` が全 peer で真でないと `return false` (vnetorch.cpp:1175-1183, 1508-1516)
4. **CONFIG_DB → APPL_DB**: passthrough は即時・依存チェックなし (vnetorch.cpp:3613-3661)
