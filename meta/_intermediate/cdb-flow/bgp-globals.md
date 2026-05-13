# CONFIG_DB 例外条件分析: BGP_GLOBALS / BGP_GLOBALS_AF

## Consumer

- `bgpcfgd` (`managers_bgp.py`, `main.py`): `BGPPeerMgrBase` が `BGP_GLOBALS` を直接 subscribe しない。`frr-mgmt-framework/frrcfgd/frrcfgd.py` の `bgp_table_handler_common` が `BGP_GLOBALS` を処理。
- `frrcfgd`: `BGP_GLOBALS` の `local_asn` が未設定の VRF のエントリは全部 skip (LOG_DEBUG)。

## 例外条件

### 1. local_asn 未設定 → 全フィールド更新スキップ
- ソース: `frrcfgd.py` L2660-2662
- `local_asn` が未設定の VRF で `BGP_GLOBALS` (以外のテーブル) に更新が来ると
  `ignore table {} update because local_asn for VRF {} was not configured` を LOG_DEBUG して continue。
- 例外: `BGP_GLOBALS` 自体に `local_asn` フィールドが含まれる場合のみ処理を続ける。

### 2. 非 default VRF が設定前に参照 → エラーログ
- ソース: `frrcfgd.py` L2451
- `non-default VRF {} was not configured` として LOG_ERR → skip。

### 3. Jinja2 テンプレートエラー → log_err + return True
- ソース: `managers_bgp.py` `add_peer()` L~
- テンプレートレンダリング失敗時: `log_err` して `return True` (エントリは処理済みとして扱う = 再試行なし)。

### 4. frrcfgd による BGP_GLOBALS_AF の AF 分解
- `BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` key の `|` 区切りが不正な場合、`ValueError` が発生し catch → skip。
- ソース: `frrcfgd.py` L2665, `except ValueError: L2246`

## BGP_GLOBALS_AF 固有

### route_flap_dampen は IPv4 unicast 限定
- YANG の `must` 制約: `afi_safi = 'ipv4_unicast'` でないと設定不可。違反は Yang validation で拒否。

### max_ebgp_paths / max_ibgp_paths デフォルト 1
- 未設定時 YANG default=1 が適用。frrcfgd はこれを FRR に渡す。
