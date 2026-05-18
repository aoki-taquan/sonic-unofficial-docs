# EVPN DIP トンネル — 書込み順依存調査 (Phase B)

## 調査対象

- `sonic-swss/orchagent/vxlanorch.cpp` (master)
- `sonic-swss/orchagent/vxlanorch.h` (master)

## 検出された順序依存

### 1. VXLAN_TUNNEL (VTEP) active → DIP トンネル生成 (強制先行)

`VxlanTunnelOrch::addTunnelUser()` (vxlanorch.cpp:1685-1699) は冒頭で
`evpn_orch->getEVPNVtep()` を呼び EVPN VTEP ポインタを取得する。
ポインタが NULL ならば警告ログを出して即 `false` を返す (vxlanorch.cpp:1687-1692)。
ポインタが非 NULL でも `vtep_ptr->isActive()` が false ならば
`"VTEP not yet active"` 警告を出して `false` を返す (vxlanorch.cpp:1694-1699)。
どちらの場合もキューへの再エンキューは行われない。呼び出し元 (`EvpnRemoteVnip2pOrch::addOperation()`)
が `return false` を受けて再試行するかどうかは呼び出し元の実装依存。

**結論**: `VXLAN_TUNNEL` + `VXLAN_EVPN_NVO` が処理され VTEP が active になるまで
DIP トンネルは生成されない。

### 2. VXLAN_EVPN_NVO 設定 → getEVPNVtep() 非 NULL (強制先行)

`EvpnNvoOrch::getEVPNVtep()` は内部の `source_vtep_ptr` ポインタを返す。
このポインタは `EvpnNvoOrch::addOperation()` が `VXLAN_EVPN_NVO` エントリを処理した時点で
設定される。`VXLAN_EVPN_NVO` が未設定の場合は `NULL` を返し、すべての
`addTunnelUser()` 呼び出しが先頭ガードで `false` を返す (vxlanorch.cpp:1687-1692)。

### 3. VXLAN_TUNNEL_MAP (ローカル VNI-VLAN マップ) → EVPN_REMOTE_VNI 処理 (強制先行)

`EvpnRemoteVnip2pOrch::addOperation()` (vxlanorch.cpp:2490-2494) は
`vxlan_tun_map_orch->isVniVlanMapExists(vni_id, ...)` を呼び、
ローカルの VNI-VLAN マッピングが存在しない場合は `return false` でリトライキューに残す。
つまり、`VXLAN_TUNNEL_MAP` でローカル側の VNI マップが先に作られていないと
リモート VNI の処理が進まない。

### 4. VLAN 存在 → EVPN_REMOTE_VNI 処理 (強制先行)

同関数 (vxlanorch.cpp:2483-2487) は `gPortsOrch->getVlanByVlanId(vlan_id, vlanPort)` を呼び、
VLAN が存在しない場合 `return false`。再試行は orchagent のイベントループ依存。

### 5. DIP トンネル参照カウント 0 (del_tnl_hw_pending クリア) → NVO 削除 (強制先行)

`EvpnNvoOrch::delOperation()` (vxlanorch.cpp:2803-2807) は
`source_vtep_ptr->del_tnl_hw_pending` が true の場合に `return false` で削除をブロックする。
`del_tnl_hw_pending` は DIP トンネルが HW 削除待ちの間 true に保持される。
DIP トンネルの参照カウントがすべてゼロになり `deletePendingSIPTunnel()` が完了するまで
EVPN NVO の CONFIG_DB エントリ削除が SAI に反映されない。

## まとめ (テーブル)

| # | 先行条件 | 後続操作 | 強制度 | 根拠 |
|---|----------|----------|--------|------|
| 1 | `VXLAN_EVPN_NVO` 処理済み (getEVPNVtep 非 NULL) | DIP トンネル生成 | 強制先行 | vxlanorch.cpp:1685-1692 |
| 2 | `VXLAN_TUNNEL` (VTEP) isActive() = true | DIP トンネル生成 | 強制先行 | vxlanorch.cpp:1694-1699 |
| 3 | `VXLAN_TUNNEL_MAP` で VNI-VLAN マップ存在 | EVPN_REMOTE_VNI 処理 | 強制先行 | vxlanorch.cpp:2490-2494 |
| 4 | 対象 VLAN が存在 | EVPN_REMOTE_VNI 処理 | 強制先行 | vxlanorch.cpp:2483-2487 |
| 5 | 全 DIP トンネル参照カウント 0 (del_tnl_hw_pending=false) | EVPN NVO 削除 | 強制先行 | vxlanorch.cpp:2803-2807 |
