# VXLAN_EVPN_NVO — Phase C 暗黙参照抽出ノート

ソース: `sonic-swss/orchagent/vxlanorch.cpp`  
対象ページ: `docs/reference/config-db/vxlan-evpn-nvo.md`  
抽出日: 2026-05-16

## 抽出した暗黙参照

### 1. VXLAN_TUNNEL (VxlanTunnelOrch)

- **参照箇所**: `vxlanorch.cpp:2782-2786`
- **参照方法**: `EvpnNvoOrch::addOperation()` が `tunnel_orch->getVxlanTunnel(vtep_name)` を呼び `source_vtep_ptr` に格納する
- **依存関係**: `VXLAN_EVPN_NVO.source_vtep` が指す `VXLAN_TUNNEL` が `VxlanTunnelOrch` に登録済みである必要がある。未登録の場合 `getVxlanTunnel()` は `nullptr` を返し `source_vtep_ptr = NULL` のまま。後続の DIP トンネル作成処理 (`addTunnelUser`) で NULL 参照が発生するリスクがある。
- **削除時**: `EvpnNvoOrch::delOperation()` は `source_vtep_ptr->del_tnl_hw_pending` を確認し、HW 削除保留中は `return false` で処理保留。TUNNEL より先に NVO を削除する必要がある。

### 2. VXLAN_TUNNEL_MAP (VxlanTunnelMapOrch 経由)

- **参照箇所**: `vxlanorch.cpp:1678,1733` (addTunnelUser/delTunnelUser)
- **参照方法**: `VxlanTunnelOrch::addTunnelUser()` 内で `EvpnNvoOrch* evpn_orch = gDirectory.get<EvpnNvoOrch*>()` を取得して EVPN 状態を確認する
- **依存関係**: EVPN リモート VNI 追加 (VXLAN_REMOTE_VNI) 処理で NVO インスタンス経由でソース VTEP を参照する。VXLAN_EVPN_NVO が設定される前に VXLAN_TUNNEL_MAP が処理されても、NVO の source_vtep_ptr が NULL なら DIP トンネル作成が不完全になる。

### 3. VLAN (PortsOrch 経由)

- **参照箇所**: `vxlanorch.cpp:1719-1721,1750-1761`
- **参照方法**: `VxlanTunnelOrch::addTunnelUser()` → `gPortsOrch->addTunnel()` / `gPortsOrch->addBridgePort()` でリモートトンネルポートを VLAN ブリッジドメインに登録
- **依存関係**: EVPN NVO が有効な状態で DIP トンネルが作成される際、対応 VLAN が `PortsOrch` に登録済みである必要がある。VXLAN_TUNNEL_MAP が VLAN より先に設定された場合と同様の pending 動作。

## 依存解決順序まとめ

```
VLAN (PortsOrch) ──┐
                   ├──→ VXLAN_TUNNEL ──→ VXLAN_TUNNEL_MAP ──→ VXLAN_EVPN_NVO
VRF  (VRFOrch)  ──┘
```

削除方向（逆順が安全）:
`VXLAN_EVPN_NVO` → `VXLAN_TUNNEL_MAP` / `VXLAN_VRF_MAP` → `VXLAN_TUNNEL`

## ページ適用状況

- `docs/reference/config-db/vxlan-evpn-nvo.md` の末尾に `<!-- cross-refs -->` ブロックとして追加済み。
