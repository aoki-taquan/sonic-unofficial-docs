# CONFIG_DB 例外条件分析: BGP_PEER_GROUP

## Consumer

- `frrcfgd` (`frrcfgd.py`): `bgp_neighbor_handler` (L2303) — `BGP_NEIGHBOR` と共通ハンドラ
- `bgpcfgd` `BGPPeerGroupMgr`: peer-group テンプレートを使って FRR に push

## 例外条件

### 1. peer-group 作成失敗 → LOG_ERR + continue (skip)
- `frrcfgd` は peer-group が未作成の場合、vtysh で `neighbor {} peer-group` コマンドを実行。
- 失敗時: `'failed to create peer-group %s for VRF %s'` → continue。
- ソース: `frrcfgd.py` L2799-2802

### 2. local_asn 未設定 VRF → 全更新スキップ
- ソース: `frrcfgd.py` L2660

### 3. BGPPeerGroupMgr の Jinja2 エラー
- `policy_template.render()` 失敗: `log_err` して `return False`。
- `peergroup_template.render()` 失敗: `log_err` して `return False`。
- ソース: `managers_bgp.py` `update_policy()`, `update_pg()`

### 4. TSA / IDF isolation route-map の自動付与
- `DeviceGlobalCfgMgr.check_state_and_get_tsa_routemaps()` が TSA 状態を確認。
- TSA 有効時: peer-group コマンドに TSA route-map が自動追加される。
- この処理でテンプレートエラーが出ると peer-group 全体が skip。

### 5. 削除時: peer-group に紐付く neighbor が残存 → FRR エラー (bgpcfgd はログのみ)
- FRR 10.1 以降: listen range がある場合、先に `no bgp listen range` を実行してから peer-group 削除。
- ただし `BGP_PEER_GROUP` 自体は bgpcfgd が直接 subscribe していない (frrcfgd のみ)。
