# BGP_PEER_GROUP_AF 値依存挙動分析

BGP_NEIGHBOR_AF と同一の `sonic-bgp-cmn-af` grouping を uses するため、
同じ enum フィールドを持つ。

## enum フィールド (BGP_NEIGHBOR_AF 分析と同一)
- `send_community`: standard/extended/both/large/all/none → frrcfgd hdl_send_com
- `tx_add_paths`: tx_all_paths → addpath-tx-all-paths / tx_best_path_per_as → addpath-tx-bestpath-per-AS
- `cap_orf`: send/receive/both → frrcfgd hdl_capa_orf_pfxlist
- `afi_safi` (key): ipv4_unicast/ipv6_unicast/l2vpn_evpn で AF ブロック選択

## 差異
- peer-group スコープ: `BGP_PEER_GROUP_AF|<vrf>|<pg_name>|<afi_safi>`
- peer-group に属する全 neighbor に継承される (FRR peer-group 動作)

## まとめ
- enum: BGP_NEIGHBOR_AF と同一
