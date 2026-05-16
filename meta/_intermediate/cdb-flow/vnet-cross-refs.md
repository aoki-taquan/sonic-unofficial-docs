# VNET cross-refs — Phase C 調査メモ

調査対象: `sonic-swss/orchagent/vnetorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`,
`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang`

## CONFIG_DB 側 leafref / 依存テーブル

| このテーブル | 参照先 | 参照フィールド | YANG leafref |
|-------------|--------|---------------|--------------|
| `VNET` | `VXLAN_TUNNEL` | `vxlan_tunnel` | `/svxlan:sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/name` |
| `VNET_ROUTE` | `VNET` | `vnet_name` (key) | `/svnet:sonic-vnet/VNET/VNET_LIST/name` |
| `VNET_ROUTE_TUNNEL` | `VNET` | `vnet_name` (key) | 同上 |

## APPL_DB 投影テーブル (write-through)

- `APP_VNET_TABLE` (`VNET_TABLE`) — VNetOrch が消費 (`orchdaemon.cpp:276`)
- `APP_VNET_RT_TABLE_NAME` — VNetRouteOrch が消費 (`orchdaemon.cpp:265-266`)
- `APP_VNET_RT_TUNNEL_TABLE_NAME` — VNetRouteOrch が消費 (`orchdaemon.cpp:265-267`)
- `APP_VNET_MONITOR_TABLE_NAME` — monitor_session_producer_ で書き込み (`vnetorch.cpp:747`)

## STATE_DB 参照

- `STATE_VRF_TABLE` (`STATE_VRF_OBJECT_TABLE_NAME`) — `isVrfStateOk()` が参照 (`vxlanmgr.cpp:738`)
- `STATE_VNET_RT_TUNNEL_TABLE_NAME` — VNetRouteOrch が endpoint monitor 結果を読み取り (`vnetorch.cpp:745`)
- `STATE_VNET_MONITOR_TABLE_NAME` — MonitorOrch が購読 (`orchdaemon.cpp:285`)

## 関連 CONFIG_DB テーブル（コード解析）

- `DEVICE_METADATA|localhost` — `mac` フィールドを `getVxlanRouterMacAddress()` が参照 (`vxlanmgr.cpp:784`)
- `VXLAN_TUNNEL` — `vxlan_orch->isTunnelExists(tunnel)` で存在確認 (`vnetorch.cpp:499`)
- `INTERFACE` / `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` — `setIntf()`/`delIntf()` 経由で `gIntfsOrch` と連携 (`vnetorch.cpp:392-428`)

## オーケストレータ連鎖

```
VNetCfgRouteOrch  (CONFIG_DB: VNET_ROUTE, VNET_ROUTE_TUNNEL)
  → APPL_DB: APP_VNET_RT_TABLE / APP_VNET_RT_TUNNEL_TABLE
    → VNetRouteOrch (APPL_DB 消費)
      → SAI: route / nexthop

VNetOrch (APPL_DB: APP_VNET_TABLE)
  → VxlanTunnelOrch (isTunnelExists チェック)
  → SAI: sai_virtual_router_api->create_virtual_router()
  → IntfsOrch (setIntf/delIntf)

VxlanMgr (CONFIG_DB: VNET → APPL_DB: APP_VNET_TABLE 前段処理)
  → STATE_VRF_TABLE 参照
  → DEVICE_METADATA mac 参照
```

## スキャン証跡

- `orchdaemon.cpp` L265-285, L350-358
- `vnetorch.cpp` L40 (extern), L392-428, L497-503, L606-630, L738-748
- `vxlanmgr.cpp` L183-213, L738-752, L784-806
- `sonic-vnet.yang` L57-58, L120-121, L156-157
