# VXLAN_TUNNEL_MAP — Phase C 暗黙参照抽出ノート

ソース: `sonic-swss/orchagent/vxlanorch.cpp`  
対象ページ: `docs/reference/config-db/vxlan-tunnel-map.md`  
抽出日: 2026-05-16

## 抽出した暗黙参照

### 1. VXLAN_TUNNEL (VxlanTunnelOrch)

- **参照箇所**: `vxlanorch.cpp:2047-2058`
- **参照方法**: `VxlanTunnelMapOrch::addOperation()` が `tunnel_orch->isTunnelExists(tunnel_name)` で親トンネルを確認、`tunnel_orch->getVxlanTunnel(tunnel_name)` でポインタを取得
- **依存関係**: `VXLAN_TUNNEL_MAP` のキーに含まれる `<tunnel_name>` が `VxlanTunnelOrch` に登録済みである必要がある。未登録時は `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist")` を記録して `return false` (リトライ待ち)。`del_tnl_hw_pending` フラグが立っていても同様にブロック (`vxlanorch.cpp:2053-2058`)。

### 2. VLAN (PortsOrch)

- **参照箇所**: `vxlanorch.cpp:2030-2034, 2145-2148`
- **参照方法**: `gPortsOrch->getVlanByVlanId(vlan_id, tempPort)` で VLAN オブジェクトを取得
- **依存関係**: VLAN が `PortsOrch` に未登録の場合 `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", vlan_id)` を記録して `return false` (リトライ待ち)。削除時に VLAN が消えていた場合は `SWSS_LOG_ERROR("Delete VLAN-VNI map.vlan id doesn't exist: %d")` を記録して `return true` (永続破棄)。

### 3. VRF (VRFOrch)

- **参照箇所**: `vxlanorch.cpp:2095-2113`
- **参照方法**: `VRFOrch* vrf_orch = gDirectory.get<VRFOrch*>()` → `vrf_orch->isL3VniVlan(vni_id)` でこの VNI が L3VNI として登録済みかを確認
- **依存関係**: `isL3VniVlan()` が `true` の場合、SAI `create_tunnel_map_entry()` を呼ばず `SAI_NULL_OBJECT_ID` を記録する (暗黙 no-op)。CONFIG_DB に L3VNI を明示するフィールドはなく VRFOrch 内部状態に依存する **silent 挙動差**。

### 4. PortsOrch (brideport / tunnel port 管理)

- **参照箇所**: `vxlanorch.cpp:2082-2084`
- **参照方法**: トンネルが非 active かつ DIP トンネル不使用の場合 `gPortsOrch->addTunnel()` / `gPortsOrch->addBridgePort()` でソース VTEP トンネルポートをブリッジに追加
- **依存関係**: `VXLAN_TUNNEL_MAP` の最初のエントリ追加がトンネルポートの HW 作成トリガになる。逆に最後のエントリ削除時 (`vlan_vrf_vni_count == 0`) にトンネルポートの HW 削除が走る (`vxlanorch.cpp:2193-2226`)。

## 依存解決順序まとめ

```
VLAN (PortsOrch) ──┐
VRF  (VRFOrch)  ───┼──→ VXLAN_TUNNEL ──→ VXLAN_TUNNEL_MAP
                   └──────────────────────↗
```

削除方向（逆順が安全）:
`VXLAN_EVPN_NVO` → `VXLAN_TUNNEL_MAP` → `VXLAN_TUNNEL`  
(`VLAN` は `VXLAN_TUNNEL_MAP` 削除後に削除可)

## ページ適用状況

- `docs/reference/config-db/vxlan-tunnel-map.md` の末尾に `<!-- cross-refs -->` ブロックとして追加済み。
