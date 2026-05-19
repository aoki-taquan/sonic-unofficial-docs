# VNET_ROUTE / VNET_ROUTE_TUNNEL — 失敗挙動調査メモ (Phase D)

## 調査対象

- `sonic-net/sonic-swss` `orchagent/vnetorch.cpp`

## 調査手順

`vnetorch.cpp` の `VNetCfgRouteOrch::doTask()`, `doVnetRouteTask()`, `doVnetTunnelRouteTask()`, `VNetRouteOrch::doRouteTask<VNetVrfObject>()`, `handleTunnel()`, `handleRoutes()` を精読。

## 発見した失敗パス

### CFG 層 (`VNetCfgRouteOrch`)

`doTask()` は `doVnetRouteTask()` / `doVnetTunnelRouteTask()` の戻り値を `task_result` として受け取り、`false` ならエントリをキューに残す（`++it`）、`true` なら erase する（vnetorch.cpp:3599-3608）。

- 不明コマンド（SET/DEL 以外）: `SWSS_LOG_ERROR("Unknown command : %s")` を出力し `return false`（vnetorch.cpp:3630, 3662）。エントリは `m_toSync` に残り次回再試行されるが、コマンドが変わらない限り永続的に再試行ループに入る。

### APPL 層 — VNET_ROUTE（underlay, `handleRoutes`/`doRouteTask<VNetVrfObject>`）

1. **VNET 未存在**: `isVnetExists()` が偽 → SET は `return false`（retry）、DEL は `return true`（スキップ）（vnetorch.cpp:1494-1497, 1684-1688）。
2. **peer VNET 未存在**: peer 全件 `isVnetExists()` 確認で 1 件でも偽 → `return false`（retry）（vnetorch.cpp:1514, 1738）。
3. **Port/RIF 未存在（subnet 経路）**: `gPortsOrch->getPort(nh.ifname, port)` が偽または `m_rif_id == SAI_NULL_OBJECT_ID` → `SWSS_LOG_WARN("Port/RIF %s doesn't exist")` + `return false`（retry）（vnetorch.cpp:1700-1703）。
4. **SAI route add/del 失敗**: `add_route()` / `del_route()` が `false` → `SWSS_LOG_ERROR` + `return false`（vnetorch.cpp:1534-1535, 1554-1555）。
5. **RouteOrch route add/remove Post 失敗**: `addRoutePost()` / `removeRoutePost()` が偽 → `SWSS_LOG_ERROR` + `return false`（vnetorch.cpp:1635-1636, 1658-1659）。

### APPL 層 — VNET_ROUTE_TUNNEL（tunnel 経路, `handleTunnel`/`doRouteTask<VNetVrfObject>` tunnel）

1. **`vni` リスト件数不一致**: `vni_list.size() != ip_list.size()` → `SWSS_LOG_ERROR("VNI size of %zu does not match endpoint size of %zu")` + `return false`（vnetorch.cpp:3276-3277）。エントリは保留・再試行されるが件数が一致しない限り永続エラー。
2. **`mac_address` リスト件数不一致**: `mac_list.size() != ip_list.size()` → `SWSS_LOG_ERROR("MAC address size of %zu does not match endpoint size of %zu")` + `return false`（vnetorch.cpp:3282-3283）。
3. **`endpoint_monitor` 件数不一致**: `monitor_list.size() != ip_list.size()` → `SWSS_LOG_ERROR("Peer monitor size of %zu does not match endpoint size of %zu")` + `return false`（vnetorch.cpp:3288-3289）。
4. **`primary` 設定 + `endpoint_monitor` なし**: `SWSS_LOG_ERROR("Primary/backup behaviour cannot function without endpoint monitoring.")` + `return false`（vnetorch.cpp:3293）。
5. **`pinned_state` 件数不一致**: `pinned_state_list.size() != monitor_list.size()` → `SWSS_LOG_ERROR` + `return false`（vnetorch.cpp:3298-3299）。
6. **nexthop グループ上限到達**: `SWSS_LOG_ERROR("Reached maximum number of next hop groups.")` + `return false`（vnetorch.cpp:773-774）。
7. **SAI nexthop group 作成失敗**: `sai_next_hop_group_api->create_next_hop_group()` 失敗 → `SWSS_LOG_ERROR` + `return false`（vnetorch.cpp:815-817）。
8. **SAI nexthop group member 作成失敗**: 失敗時は作成済みメンバーをロールバックせず `return false`（vnetorch.cpp:856-858）。部分的に作成済みのメンバーが孤立する可能性あり。
9. **SAI route add/update/del 失敗 + nhg ロールバック**: `route_status` が `false` → nexthop group を `removeNextHopGroup()` でロールバック試行後 `return false`（vnetorch.cpp:1272-1280）。
10. **VxlanTunnelOrch `createNextHopTunnel()` 失敗**: `SWSS_LOG_ERROR("NH Tunnel create failed")` + `return false`（vnetorch.cpp:321-323）。

## retry vs. 永続エラー

| 失敗 | 再試行 | 備考 |
|------|--------|------|
| VNET 未存在（SET） | あり | VNET 作成後に自動解消 |
| peer VNET 未存在 | あり | peer 全件揃うまで継続 |
| Port/RIF 未存在 | あり | RIF 作成後に自動解消 |
| リスト件数不一致 | あり（永続）| 件数が不一致のままなら解消しない |
| primary + monitor なし | あり（永続）| 設定修正まで解消しない |
| SAI 失敗 | あり | ASIC 状態依存 |
| 不明コマンド | あり（永続）| コマンド変わらず永続ループ |
