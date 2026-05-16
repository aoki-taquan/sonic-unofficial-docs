# CONFIG_DB 暗黙参照分析: BGP_PEER_GROUP (Phase C)

## 分析対象

`BGP_PEER_GROUP` テーブルが持つ暗黙的な参照関係（被参照・参照先）を
`bgpcfgd` / `frrcfgd` ソースから抽出する。

## 被参照（BGP_NEIGHBOR → BGP_PEER_GROUP）

`BGP_NEIGHBOR` の `peer_group_name` フィールドが `BGP_PEER_GROUP` の
`<vrf>|<peer_group_name>` キーを参照する。

### 証跡

- `frrcfgd.py` L2196-2197: 初期化時に `BGP_NEIGHBOR` の `peer_group_name` を読み取り、
  `self.bgp_peer_group[vrf][pg_name].ref_nbrs.add(peer)` で紐付ける。
- `frrcfgd.py` L2822-2829: `BGP_NEIGHBOR` SET 処理時に `peer_group_name` が
  `BGP_PEER_GROUP` に存在しない場合 `LOG_ERR('invalid peer-group %s was referenced')` を記録して skip。
- `frrcfgd.py` L2848: `BGP_PEER_GROUP` 変更時に `BGP_NEIGHBOR` 側を再適用する
  `match_nbr = lambda data: data.get('peer_group_name', None) == key` で逆引き依存。
- `frrcfgd.py` L2553-2555: `__nbr_impl_action` は IP neighbor では `['asn', 'peer_group_name']`、
  インタフェース neighbor では `['peer_group_name']` のみを implicit action トリガーとして扱う。

### 解決タイミング

`BGP_NEIGHBOR.peer_group_name` が SET される時点で `frrcfgd` が `BGP_PEER_GROUP` テーブルを
インメモリキャッシュ (`self.bgp_peer_group`) に照合。peer-group が未登録の場合は `LOG_ERR` + skip。
peer-group は先に存在している必要がある（先行登録制約）。

## 参照先（BGP_PEER_GROUP_AF → ROUTE_MAP）

`sonic-bgp-common` grouping (`sonic-bgp-cmn-af`) の `BGP_PEER_GROUP_AF` 経由で
`ROUTE_MAP_SET` を leafref 参照する。

### 証跡

- `sonic-bgp-common.yang` L385-387: `route_map_in` が
  `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name` を leafref。
- `sonic-bgp-common.yang` L394-396: `route_map_out` が同上の leafref。
- `sonic-bgp-common.yang` L356: `default_rmap` が同上の leafref。
- `sonic-bgp-common.yang` L410: `unsuppress_map_name` が同上の leafref。
- `frrcfgd.py` L1903-1904: `nbr_af_key_map` で `route_map_in` / `route_map_out` を
  `neighbor {} route-map {} in/out` コマンドに変換（`BGP_PEER_GROUP_AF` にも同一マップ適用）。
- `managers_allow_list.py` L609-618: `bgpcfgd` が peer-group に紐付く route-map を FRR
  running-config から `__get_peer_group_to_route_map()` で抽出し allow-list 更新に利用。
  `re.compile(r'^\s*neighbor %s route-map (\S+) in$' % pg)` でマッチ。

### 解決タイミング

YANG leafref は YANG バリデーション時に解決（ROUTE_MAP が CONFIG_DB に存在しない場合、
`sonic-cfggen` または `bgpcfgd` の YANG バリデーションで拒否）。
FRR 実行時は `frrcfgd` が vtysh コマンド発行時に ROUTE_MAP の存在を前提とする（FRR 側でエラー）。

## 被参照（BGP_GLOBALS_LISTEN_PREFIX → BGP_PEER_GROUP）

`BGP_GLOBALS_LISTEN_PREFIX` の `peer_group` フィールドが
`BGP_PEER_GROUP_LIST.peer_group_name` を参照する（dynamic neighbor listen range）。

### 証跡

- `frrcfgd.py` L2845-2846: `BGP_PEER_GROUP` 適用時に
  `match_pg = lambda data: data.get('peer_group', None) == key` で
  `BGP_GLOBALS_LISTEN_PREFIX` を再適用する。

## サマリテーブル

| 依存方向 | 参照元フィールド | 参照元テーブル | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|----------------|--------------|--------------|--------------|---------|------|
| 逆参照（被参照） | `peer_group_name` | `BGP_NEIGHBOR` | `BGP_PEER_GROUP`（本テーブル） | `BGP_PEER_GROUP\|<vrf>\|<pg_name>` | NEIGHBOR の peer-group 所属先。peer-group 未存在時は `LOG_ERR` + skip | `frrcfgd.py:2822-2829` |
| 逆参照（被参照） | `peer_group` | `BGP_GLOBALS_LISTEN_PREFIX` | `BGP_PEER_GROUP`（本テーブル） | `BGP_PEER_GROUP\|<vrf>\|<pg_name>` | dynamic neighbor listen range の peer-group 紐付け。peer-group 変更時に再適用される | `frrcfgd.py:2845-2846` |
| 順参照（AF経由） | `route_map_in` / `route_map_out` | `BGP_PEER_GROUP_AF` | `ROUTE_MAP_SET` | `ROUTE_MAP_SET\|<name>` | インバウンド/アウトバウンド route-map。YANG leafref で参照。frrcfgd が `neighbor {} route-map {} in/out` に変換 | `sonic-bgp-common.yang:385-396`, `frrcfgd.py:1903-1904` |
| 順参照（AF経由） | `default_rmap` | `BGP_PEER_GROUP_AF` | `ROUTE_MAP_SET` | `ROUTE_MAP_SET\|<name>` | default-originate 時の route-map | `sonic-bgp-common.yang:356` |
| 順参照（AF経由） | `unsuppress_map_name` | `BGP_PEER_GROUP_AF` | `ROUTE_MAP_SET` | `ROUTE_MAP_SET\|<name>` | suppress 解除 route-map | `sonic-bgp-common.yang:410` |
| ランタイム逆参照 | peer-group → route-map（running-config） | `bgpcfgd` allow-list | FRR running-config | — | allow-list 更新時に peer-group の route-map in を running-config から抽出 | `managers_allow_list.py:609-618` |
