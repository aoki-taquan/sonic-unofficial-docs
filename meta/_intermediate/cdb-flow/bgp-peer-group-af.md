# CONFIG_DB 例外条件分析: BGP_PEER_GROUP_AF

## Consumer

- `frrcfgd` (`frrcfgd.py`): `bgp_table_handler_common` (L2305)
- key_map: `nbr_af_key_map` (BGP_NEIGHBOR_AF と同一マップ)

## 例外条件

### 1. key パース失敗 (ValueError) → skip
- key 形式: `<vrf>|<pg_name>|<afi_safi>`。
- `af_ip_type.lower().split('_')` が 1 要素の場合 ValueError → catch → continue。
- ソース: `frrcfgd.py` L2665-2666

### 2. local_asn 未設定 VRF → スキップ
- ソース: `frrcfgd.py` L2660

### 3. peer-group 未作成のまま AF 設定 → vtysh エラー (frrcfgd は LOG_ERR)
- `BGP_PEER_GROUP_AF` の SET で対象 peer-group が FRR に存在しない場合、
  vtysh コマンドが失敗 → `LOG_ERR('failed running BGP neighbor config command')` → continue。
- ソース: `frrcfgd.py` L2791-2792

### 4. BGP_PEER_GROUP_AF と BGP_NEIGHBOR_AF のフィールド共通
- 両テーブルは同一 `nbr_af_key_map` を使用。max_prefix / send_default_route の複合条件は BGP_NEIGHBOR_AF と同様。
