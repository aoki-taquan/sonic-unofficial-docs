# EVPN DIP トンネル 副次 DB 書込・副作用 (Phase F)

ソース: `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/orchagent/vxlanorch.h`

## SAI 副次書込

### create_tunnel_map + create_tunnel (DIP トンネル初回生成)

- `VxlanTunnel::createDynamicDIPTunnel()` → `createTunnelHw(mapper_list, TUNNEL_MAP_USE_COMMON_ENCAP_DECAP, false)`
- mapper_list: VLAN + VRF のみ (BRIDGE なし)
- peer_mode: `SAI_TUNNEL_PEER_MODE_P2P` (TNL_CREATION_SRC_EVPN 分岐)
- with_term: false (termination entry 生成なし)
- ソース: `vxlanorch.cpp:1167-1169`

### create_vlan_member (VLAN flood domain への追加)

- `EvpnRemoteVnip2pOrch::addOperation()` → `gPortsOrch->addVlanMember(vlanPort, tunnelPort, "untagged")`
- tagging_mode ハードコード: `"untagged"` (コード注記あり: "does 'untagged' make the most sense here?")
- ソース: `vxlanorch.cpp:2526-2527`

## STATE_DB 書込

### VXLAN_TUNNEL_TABLE (addRemoveStateTableEntry)

- 生成時: `src_ip`, `dst_ip`, `tnl_src="EVPN"`, `operstatus="down"` をセット
- oper up: `operstatus="up"` 更新
- oper down: `operstatus="down"` 更新
- 削除時: エントリ削除 (`del`)
- WarmBoot 時: 既存エントリ存在時はスキップ
- ソース: `vxlanorch.cpp:1901-1953`

## COUNTERS_DB 書込

- FlexCounter 登録: `addTunnelToFlexCounter()` → `m_pendingAddToFlexCntr` に蓄積 → タイマー処理で COUNTERS_DB 書込
- FlexCounter 解除: `removeTunnelFromFlexCounter()` → `COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP` から削除
- ソース: `vxlanorch.cpp:1342-1367`

## インメモリ状態

- `tnl_users_` マップ: remote_vtep → refcnt 管理
- `vxlan_tunnel_table_`: VxlanTunnel オブジェクト管理 (addTunnel/delTunnel)
