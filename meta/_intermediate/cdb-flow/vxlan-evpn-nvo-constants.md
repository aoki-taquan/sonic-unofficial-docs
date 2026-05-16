# VXLAN_EVPN_NVO ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/vxlanorch.cpp`

## 抽出定数一覧

### source_vtep フィールド

| フィールド | 取得方法 | ソース |
|-----------|---------|--------|
| `source_vtep` | `request.getAttrString("source_vtep")` | `vxlanorch.cpp:2780` |

- `EvpnNvoOrch::addOperation()` が `"source_vtep"` キーで属性を読み取る
- 読み取った値は `VxlanTunnelOrch::getVxlanTunnel(vtep_name)` に渡される (`vxlanorch.cpp:2784`)
- CONFIG_DB → orchagent への橋渡しのみで SAI への直接書き込みなし

### MAP_T → SAI_TUNNEL_MAP_TYPE 対応表

EVPN NVO が内部で参照する tunnel_map_type のハードコードマッピング (vxlanorch.cpp:38-46):

| MAP_T enum | SAI_TUNNEL_MAP_TYPE |
|-----------|---------------------|
| `VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID` |
| `VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` |
| `VRID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` |
| `VNI_TO_VRID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID` |
| `BRIDGE_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI` |
| `VNI_TO_BRIDGE` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF` |

```cpp
// vxlanorch.cpp:38-46
const map<MAP_T, uint32_t> vxlanTunnelMap =
{
    { MAP_T::VNI_TO_VLAN_ID, SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID },
    { MAP_T::VLAN_ID_TO_VNI, SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI },
    { MAP_T::VRID_TO_VNI, SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI },
    { MAP_T::VNI_TO_VRID, SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID },
    { MAP_T::BRIDGE_TO_VNI, SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI },
    { MAP_T::VNI_TO_BRIDGE,  SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF},
};
```

- この定数マップは `EvpnNvoOrch` が参照する `VxlanTunnel` オブジェクト経由で間接的に使用される
- EVPN NVO が確立すると、上記マップに基づき encap/decap mapper が SAI に設定される

### EvpnNvoOrch の動作定数

| 状態 | ログメッセージ | ソース |
|------|-------------|--------|
| add 成功 | `"evpnnvo: %s vtep : %s"` (INFO) | `vxlanorch.cpp:2786` |
| del 時 VTEP NULL | `"NVO Delete failed as VTEP Ptr is NULL"` (WARN) | `vxlanorch.cpp:2799` |
| del 時 hw pending | `"NVO not deleted as hw delete is pending"` (WARN) | `vxlanorch.cpp:2805` |
| del 成功 | `"NVO: %s"` (INFO) | `vxlanorch.cpp:2811` |

- `del_tnl_hw_pending` フラグが `true` の場合、NVO 削除は `false` を返してリトライを要求する

## 備考

- `VXLAN_EVPN_NVO` テーブル自体にハードコードされた数値定数はない
- SAI `tunnel_map_type` の定数は EVPN NVO が参照する source_vtep (VXLAN_TUNNEL) 側で設定される
- `FLEX_COUNTER_UPD_INTERVAL 1` (`vxlanorch.cpp:36`) はフレックスカウンタ更新間隔 (秒) だが NVO テーブルには直接関係しない
