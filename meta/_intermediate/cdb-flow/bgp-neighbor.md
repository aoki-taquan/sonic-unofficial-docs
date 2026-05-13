# CONFIG_DB 例外条件分析: BGP_NEIGHBOR

## Consumer

- `bgpcfgd` `BGPPeerMgrBase` (peer_type="general", check_neig_meta=True): `main.py` L87
- `frr-mgmt-framework` `frrcfgd`: `bgp_neighbor_handler` + `bgp_table_handler_common`

## 例外条件

### 1. Loopback0 IPv4 / bgp_router_id 双方未設定 → return False (再試行)
- ソース: `managers_bgp.py` `add_peer()`

### 2. local_addr 欠如 → log_warn (処理は続行)
- `"Peer %s. Missing attribute 'local_addr'"` を warn ログ。
- peer は追加されるが local interface との紐付けなし。

### 3. check_neig_meta 有効時: DEVICE_NEIGHBOR_METADATA 未準備 → skip
- `name` フィールドが data にあり、そのエントリが DEVICE_NEIGHBOR_METADATA に存在しない場合:
  `log_info("DEVICE_NEIGHBOR_METADATA is not ready for neighbor '%s' - '%s'")` して return False。
- frrcfgd: `peer_group_name` が存在しない peer_group を参照 → `LOG_ERR('invalid peer-group %s was referenced')` → continue。

### 4. admin_status が 'up'/'down' 以外 → log_err (drop)
- `"Can't update the peer. It has wrong attribute value attr['admin_status'] = '%s'"`

### 5. frrcfgd: local_asn 未設定 VRF → 全更新スキップ
- ソース: `frrcfgd.py` L2660

### 6. interface neighbor 作成失敗 → LOG_ERR + continue
- `failed to create neighbor of interface %s for VRF %s`
