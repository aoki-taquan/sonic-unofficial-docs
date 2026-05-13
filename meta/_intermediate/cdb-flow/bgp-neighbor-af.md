# CONFIG_DB 例外条件分析: BGP_NEIGHBOR_AF

## Consumer

- `frrcfgd` (`frrcfgd.py`): `bgp_table_handler_common` + `tbl_to_key_map` の `BGP_NEIGHBOR_AF`
- テーブル登録: L2110 `'BGP_NEIGHBOR_AF': nbr_af_key_map`

## 例外条件

### 1. key パース失敗 (ValueError) → skip
- AF key は `<vrf>|<nbr_ip>|<afi_safi>` 形式。`key.split('|')` でパース。
- 不正フォーマット時 `ValueError` → `except ValueError` で catch → continue。
- ソース: `frrcfgd.py` L2665, L2246

### 2. local_asn 未設定 VRF → 全更新スキップ
- ソース: `frrcfgd.py` L2660-2662

### 3. peer_group_name 参照先が存在しない → LOG_ERR + continue
- `invalid peer-group %s was referenced`
- ソース: `frrcfgd.py` L2828

### 4. send_default_route + default_rmap の依存
- `send_default_route=true` で `default_rmap` が同時に設定される場合のみ `default-originate route-map` コマンドが生成。
- `default_rmap` 単独では `default-originate` なしで route-map コマンドが生成されない (key_map 定義による)。

### 5. max_prefix 系フィールドの複合依存
- `max_prefix_limit` + `max_prefix_warning_threshold` + `max_prefix_restart_interval` OR `max_prefix_warning_only` の複合。
- `max_prefix_limit` 欠如時は他フィールドが無視される (key_map の `++` / `+` プレフィックスルール)。
