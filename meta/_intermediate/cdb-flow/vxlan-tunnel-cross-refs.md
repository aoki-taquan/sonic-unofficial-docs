# VXLAN_TUNNEL — Phase C 暗黙参照抽出ノート

ソース: `sonic-swss/orchagent/vxlanorch.cpp`  
対象ページ: `docs/reference/config-db/vxlan-tunnel.md`  
抽出日: 2026-05-16

## 抽出した暗黙参照

### 1. VRF (VRFOrch)

- **参照箇所**: `vxlanorch.cpp:2095,2286,2311`
- **参照方法**: `VRFOrch* vrf_orch = gDirectory.get<VRFOrch*>()` → `vrf_orch->isVRFexists(vrf_name)` / `vrf_orch->getVRFid(vrf_name)`
- **依存関係**: `VXLAN_VRF_MAP` の addOperation 時に VRF OID を取得して SAI tunnel-map entry の `VIRTUAL_ROUTER_ID` 属性に設定する。VRF が未登録の場合は pending となり、VRF 作成後の再通知まで処理が保留される。
- **TUNNEL_MAP_T**: `TUNNEL_MAP_T_VIRTUAL_ROUTER` → SAI MAP_TYPE `VNI_TO_VRID` / `VRID_TO_VNI`

### 2. VXLAN_TUNNEL_MAP (VxlanTunnelMapOrch)

- **参照箇所**: `vxlanorch.cpp:2110,2120`
- **参照方法**: `tunnel_orch->addVlanMappedToVni(vni_id, vlan_id)` — VXLAN_TUNNEL_MAP の処理後に TUNNEL 側の内部マップも更新
- **依存関係**: TUNNEL_MAP が TUNNEL より先に書かれた場合、`isTunnelActive()` が false を返し MAP 処理がサスペンド。TUNNEL 書き込み後に vxlanmgrd がリトライする。
- **削除時**: tunnel 削除前に MAP エントリが残存していると `SWSS_LOG_WARN("Need to delete mapping entries")` でリトライ待ち (`vxlanmgr.cpp`)

### 3. VXLAN_EVPN_NVO (EvpnNvoOrch)

- **参照箇所**: `vxlanorch.cpp:2773-2809`
- **参照方法**: `EvpnNvoOrch::addOperation()` が `request.getAttrString("source_vtep")` で VXLAN_TUNNEL.name を取得し、`tunnel_orch->getVxlanTunnel(vtep_name)` でポインタを解決する
- **依存関係**: VXLAN_TUNNEL エントリが先に存在しないと NVO の source_vtep 解決が失敗する。NVO 残留時に TUNNEL を削除すると `SWSS_LOG_WARN("Tunnel %s deletion failed. Need to delete NVO")` でリトライ待ちになる。

### 4. VLAN (PortsOrch)

- **参照箇所**: `vxlanorch.cpp:2030,2145,2483,2559,2645,2727`
- **参照方法**: `gPortsOrch->getVlanByVlanId(vlan_id, tempPort)` で VLAN オブジェクトを検索
- **依存関係**: VXLAN_TUNNEL_MAP の VNI-VLAN 紐付け時に参照。VLAN が PortsOrch に未登録の場合は `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", vlan_id)` を記録してスキップ。後続の EVPN_REMOTE_VNI / EVPN_REMOTE_MAC 処理も VLAN 依存。

### 5. SAI トンネルマップ (内部)

- `TUNNEL_MAP_T_VLAN` → `VNI_TO_VLAN_ID` / `VLAN_ID_TO_VNI` ペア (`vxlanorch.cpp:40-54,759-760`)
- `TUNNEL_MAP_T_VIRTUAL_ROUTER` → `VNI_TO_VRID` / `VRID_TO_VNI` ペア (`vxlanorch.cpp:42-60,767-768`)
- `TUNNEL_MAP_T_BRIDGE` → `VNI_TO_BRIDGE` / `BRIDGE_TO_VNI` ペア (`vxlanorch.cpp:775-776`)

## 依存解決順序まとめ

```
VLAN (PortsOrch) ─┐
VRF  (VRFOrch)  ──┼──→ VXLAN_TUNNEL ──→ VXLAN_TUNNEL_MAP ──→ VXLAN_EVPN_NVO
                   └──→ VXLAN_VRF_MAP
```

削除方向（逆順が安全）:
`EVPN_NVO` → `VXLAN_VRF_MAP` / `VXLAN_TUNNEL_MAP` → `VXLAN_TUNNEL`

## ページ適用状況

- `docs/reference/config-db/vxlan-tunnel.md` の末尾に `<!-- cross-refs -->` ブロックとして追加済み。
