# BGP_NEIGHBOR_AF 値依存挙動分析

## enum フィールド (sonic-bgp-cmn-af 由来)

### send_community (`bgp_community_type`)
- frrcfgd `hdl_send_com` (frrcfgd.py:945):
  - まず `neighbor X send-community all` を削除
  - `none` 以外の値: `neighbor X send-community <value>` を追加
  - `none`: send-community 無効化 (コマンド追加なし)
  - 値: `standard`, `extended`, `both`, `large`, `all`, `none`

### tx_add_paths (`bgp_tx_add_paths_type`)
- frrcfgd format `tx-add-paths` (frrcfgd.py:882-885):
  - `tx_all_paths` → `addpath-tx-all-paths`
  - `tx_best_path_per_as` → `addpath-tx-bestpath-per-AS`

### cap_orf (`sonic_bgp_orf`)
- frrcfgd `hdl_capa_orf_pfxlist` (frrcfgd.py:972):
  - 削除時: `no neighbor X capability orf prefix-list both`
  - 設定時: `neighbor X capability orf prefix-list <send|receive|both>`

### afi_safi (key)
- `ipv4_unicast` / `ipv6_unicast` / `l2vpn_evpn` で FRR address-family ブロックを選択

## まとめ
- enum 有り: send_community (6値), tx_add_paths (2値), cap_orf (3値), afi_safi (key)
