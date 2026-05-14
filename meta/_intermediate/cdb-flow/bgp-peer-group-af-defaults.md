# BGP_PEER_GROUP_AF — Phase A: コード由来の暗黙デフォルト

調査日: 2026-05-14
ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
YANG: `sonic-bgp-peergroup.yang`, `sonic-bgp-common.yang`

---

## 1. field 列挙と YANG default

`sonic-bgp-cmn-af` grouping のすべての leaf は YANG `default` 文を持たない。
すべてのフィールドは optional（存在しない場合は FRR コマンドを発行しない）。

| フィールド | YANG 型 | YANG default | 実装 default / fallback |
|-----------|---------|-------------|------------------------|
| `afi_safi` | string | なし | key の一部（必須） |
| `admin_status` | stypes:admin_status | なし | フィールド不在 → FRR コマンド発行なし |
| `send_default_route` | boolean | なし | 不在 → default-originate なし |
| `default_rmap` | leafref(ROUTE_MAP) | なし | 不在 → default-originate に route-map なし |
| `max_prefix_limit` | uint32 | なし | 不在 → maximum-prefix なし |
| `max_prefix_warning_only` | boolean | なし | 不在 → warning-only なし |
| `max_prefix_warning_threshold` | uint8 (1..100) | なし | 不在 → threshold 引数なし |
| `max_prefix_restart_interval` | uint16 (1..65535) | なし | 不在 → restart 引数なし |
| `route_map_in` | leaf-list (max 1) | なし | 不在 → route-map in なし |
| `route_map_out` | leaf-list (max 1) | なし | 不在 → route-map out なし |
| `soft_reconfiguration_in` | boolean | なし | 不在 → soft-reconfiguration なし |
| `unsuppress_map_name` | leafref(ROUTE_MAP) | なし | 不在 → unsuppress-map なし |
| `rrclient` | boolean | なし | 不在 → route-reflector-client なし |
| `weight` | uint16 (0..65535) | なし | 不在 → weight なし |
| `as_override` | boolean | なし | 不在 → as-override なし |
| `send_community` | bgp_community_type enum | なし | 不在 → send-community なし |
| `tx_add_paths` | bgp_tx_add_paths_type enum | なし | 不在 → addpath なし |
| `unchanged_as_path` | boolean | なし | 不在 → attribute-unchanged なし |
| `unchanged_med` | boolean | なし | 不在 → attribute-unchanged なし |
| `unchanged_nexthop` | boolean | なし | 不在 → attribute-unchanged なし |
| `filter_list_in` | leafref(AS_PATH_SET) | なし | 不在 → filter-list in なし |
| `filter_list_out` | leafref(AS_PATH_SET) | なし | 不在 → filter-list out なし |
| `nhself` | boolean | なし | 不在 → next-hop-self なし |
| `nexthop_self_force` | boolean | なし | 不在 → next-hop-self force なし |
| `prefix_list_in` | leafref(PREFIX_SET) | なし | 不在 → prefix-list in なし |
| `prefix_list_out` | leafref(PREFIX_SET) | なし | 不在 → prefix-list out なし |
| `remove_private_as_enabled` | boolean | なし | 不在 → remove-private-AS なし |
| `replace_private_as` | boolean | なし | 不在 → replace-AS オプションなし |
| `remove_private_as_all` | boolean | なし | 不在 → all オプションなし |
| `allow_as_in` | boolean | なし | 不在 → allowas-in なし |
| `allow_as_count` | uint8 | なし | 不在 → allowas-in カウント省略 |
| `allow_as_origin` | boolean | なし | 不在 → allowas-in origin なし |
| `cap_orf` | sonic_bgp_orf enum | なし | 不在 → capability orf なし |
| `route_server_client` | boolean | なし | 不在 → route-server-client なし |

---

## 2. 暗黙デフォルト・実行時 fallback（コード由来）

### 2-1. `admin_status` — af 種別ディスパッチ

`nbr_af_key_map` には `admin_status|ipv4`, `admin_status|ipv6`, `admin_status|l2vpn` の 3 エントリがある。
フィールド名 `admin_status` は key の `<afi_safi>` のプレフィックス（`ipv4_unicast` → `ipv4`）で絞り込まれる。

`hdl_admin_status` (L1456):
- `up` → `true` に変換
- `down` → `false` に変換
- OP_DELETE → `status = 'false'` として `no neighbor PG activate` を発行
- `admin_status` 不在 → activate コマンド発行なし（FRR のデフォルト: ipv4 は自動 activate、ipv6/l2vpn は inactive）

**YANG vs 実装の乖離**:
- YANG default なし。FRR デフォルト動作（ipv4 自動 activate）は CONFIG_DB には反映されない。
  `admin_status` を書かない場合、frrcfgd は activate コマンドを発行しないが、FRR 側で BGP_GLOBALS が
  `no bgp default ipv4-unicast` で初期化されているため ipv4_unicast は inactive 扱いとなる。
  **実質的に `admin_status=true` を明示しないと ipv4 セッションも inactive になる。**

### 2-2. `send_community` — 削除時の reset シーケンス

`hdl_send_com` (L945):
- SET 時: まず `no neighbor PG send-community all` を発行してから指定値を設定（全種類 reset → 指定値設定）
- DELETE 時: `com_type = 'all'` とし `no neighbor PG send-community all` のみ発行
- `send_community=none` のとき: SET 時も `no neighbor PG send-community all` のみ（追加コマンドなし）

**暗黙ルール**: `none` と「フィールド不在」は FRR 上は同じ状態だが、DELETE は `none` 相当の `no send-community all` を発行する点が異なる。

### 2-3. `remove_private_as_*` — 複合フィールドの reset シーケンス

`hdl_rm_priv_as` (L958) は SET/DELETE にかかわらず、まず 4 パターン全 `no` を発行する:
- `no neighbor PG remove-private-AS`
- `no neighbor PG remove-private-AS all`
- `no neighbor PG remove-private-AS replace-AS`
- `no neighbor PG remove-private-AS all replace-AS`

その後 SET の場合のみ実際の値を適用。DELETE の場合は `no` だけで完了。

**dead field 注記**: `remove_private_as_enabled=false` は「有効化しない」を示すが、FRR には
`remove-private-AS false` コマンドは存在しないため、`hdl_rm_priv_as` の出力は `no` コマンド群になる。

### 2-4. `cap_orf` — 削除時の reset

`hdl_capa_orf_pfxlist` (L972):
- まず `no neighbor PG capability orf prefix-list both` を発行（全モード clear）
- SET の場合のみ指定値（`send`/`receive`/`both`）を追加設定

### 2-5. `unchanged_as_path` / `unchanged_med` / `unchanged_nexthop` — 複合コマンド

`hdl_attr_unchanged` (L1342): まず `no neighbor PG attribute-unchanged` を発行して全属性 clear 後、
SET の場合に指定値を適用。3 フィールドのうち 1 つでも変化した場合に全体が再送される。

### 2-6. `allow_as_in` + `allow_as_count` + `allow_as_origin` — comb_attr なし

`BGP_PEER_GROUP_AF` は `bgp_table_handler_common` に `comb_attr_list=[]` で渡される（L3910 デフォルト引数）。
`keepalive`/`holdtime` のような複合制約はない。

ただし `nbr_af_key_map` の allowas-in エントリはリスト形式で副フィールドを含む:
```python
(['allow_as_in', '+allow_as_count&allow_as_origin'], ...)
```
- `allow_as_in=true` かつ `allow_as_origin=true` → `allowas-in origin`
- `allow_as_in=true` かつ `allow_as_count=N` → `allowas-in N`
- `allow_as_in=true` のみ → `allowas-in`（カウント省略 → FRR デフォルト 3）
- `allow_as_in=false` → `no neighbor PG allowas-in`

### 2-7. `max_prefix_*` — 複合コマンド生成

```python
(['max_prefix_limit', '++max_prefix_warning_threshold',
  '+max_prefix_restart_interval&max_prefix_warning_only'], ...)
```
- `max_prefix_limit` 単独 → `neighbor PG maximum-prefix N`
- `+ max_prefix_warning_threshold` → `neighbor PG maximum-prefix N T`（T は 1-100%）
- `+ max_prefix_restart_interval` → `neighbor PG maximum-prefix N T restart R`
- `+ max_prefix_warning_only=true`（restart_interval なし） → `neighbor PG maximum-prefix N T warning-only`
- `max_prefix_warning_threshold` 不在 → warning_threshold 引数も `restart_interval` 引数もスキップ

**J2 テンプレートとの差異** (`bgpd.conf.db.nbr_af.j2` L68-78):
J2 テンプレートは `max_prefix_restart_interval` と `max_prefix_warning_only` の優先順位が frrcfgd と同一だが、
J2 では `max_prefix_warning_threshold` が不在でも `max_prefix_restart_interval` を出力できる。
frrcfgd の `++` 記号（オプション）でも同様の動作をするため実質同一。

### 2-8. `default_rmap` — `send_default_route` 連動

`nbr_af_key_map` に 2 エントリがある:
```python
(['send_default_route', '+default_rmap'], '{no}neighbor {} default-originate {:default-rmap}')
('default_rmap',                          '{no}neighbor {} default-originate route-map {}')
```
- `send_default_route=true` + `default_rmap=MAP` → `neighbor PG default-originate route-map MAP`
- `send_default_route=true` のみ → `neighbor PG default-originate`
- `send_default_route=false` → `no neighbor PG default-originate`
- `default_rmap` 単独（`send_default_route` なし） → `neighbor PG default-originate route-map MAP`（別エントリで処理）

### 2-9. `nexthop_self_force` の依存性

J2 テンプレート (`bgpd.conf.db.nbr_af.j2` L18-24) では `nhself=true` が前提:
```jinja
{% if 'nhself' in n_af_val and n_af_val['nhself'] == 'true' %}
{% if 'nexthop_self_force' in n_af_val and n_af_val['nexthop_self_force'] == 'true' %}
  neighbor {{nbr_name}} next-hop-self force
```
`nexthop_self_force` 単独で設定しても `nhself=true` がなければ J2 テンプレートでは無視される。
ただし `frrcfgd` の `nbr_af_key_map` では両フィールドは独立エントリなので frrcfgd 経由では
`nexthop_self_force=true` 単独で `neighbor PG next-hop-self force` が発行される。

**書き込み経路依存の乖離**: J2（minigraph/init_cfg 時）と frrcfgd（運用時 SET）で動作が異なる。

---

## 3. dead field / 実質無効フィールド

| フィールド | 状況 | 根拠 |
|-----------|------|------|
| `afi_safi` (leaf) | dead（key の一部として使用。独立 leaf としての書き込みは無意味） | key parse: `key.split('|')` で AF を抽出。DB 値は参照されない |

---

## 4. VRF / local_asn ガード

`__update_bgp` L2659: `local_asn` が未設定の VRF に対する BGP_PEER_GROUP_AF 更新は
`LOG_DEBUG 'ignore table ...'` して `continue`（skip）。FRR コマンドは発行されない。

BGP_GLOBALS が先に存在しない状態での BGP_PEER_GROUP_AF 書き込みは silently ignored。

---

## 5. Key parse の fallback

L2665-2668:
```python
if table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF' and key is not None:
    _, af_ip_type = key.split('|')
    tbl_key, _ = af_ip_type.lower().split('_')
```
key の `|` 不在や `_` 不在は ValueError → L1619-1625 の except で catch し
`syslog LOG_ERR + continue`（skip）。

---

## 6. 書き込み経路比較

| 経路 | BGP_PEER_GROUP_AF を書くか | デフォルト差異 |
|------|--------------------------|--------------|
| frrcfgd (vtysh → CONFIG_DB 同期) | はい（FRR running-config を DB に反映） | FRR デフォルト値は DB に書かれない（例: send-community の FRR デフォルト=both は DB には現れない） |
| sonic-mgmt-common REST/gNMI | はい | YANG バリデーション済み |
| minigraph/sonic-cfggen | なし（BGP_PEER_GROUP_AF 生成しない） | — |
| db_migrator | なし | — |

---

## 7. まとめ: 主要 findings

1. **YANG default なし / 全フィールド optional**: フィールド不在は「コマンド発行しない」= FRR 実装デフォルト依存
2. **`admin_status` 最重要**: 不在でも FRR の `no bgp default ipv4-unicast` 設定により ipv4 も inactive になる。activate するには必ず `admin_status=true` を書く必要がある
3. **`nexthop_self_force` 経路依存乖離**: frrcfgd 経由は単独で機能するが J2 テンプレートでは `nhself=true` が前提
4. **`send_community` の implicit reset**: SET 時に必ず `no send-community all` を先発行。意図しない community 設定が残ることはない
5. **`remove_private_as_*` 複合 reset**: 3 フィールドのいずれか変化で 4 パターン全 no を先発行
6. **dead field**: `afi_safi` leaf は key の一部であり独立 leaf として読まれない
7. **VRF guard**: BGP_GLOBALS より先に書くと silently skip される。依存順序が重要
