# BGP_PEER_GROUP_AF — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_PEER_GROUP_AF`
Consumer: `frrcfgd` / `BGPConfigDaemon.bgp_table_handler_common()` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: `table_handler_list`（L2293–2321）、`bgp_table_handler_common()`（L2640–2874）、`__vrf_based_table()`、VRF guard（L2656–2662）、key parse（L2865–2873）

---

## 検出した順序依存・タイミング依存

### 1. BGP_GLOBALS — VRF の local_asn が先行必須

`bgp_table_handler_common()` は処理冒頭で `__get_vrf_asn(vrf)` を呼ぶ（L2658）。`BGP_GLOBALS|<vrf>.local_asn` が CONFIG_DB に存在しない場合は `None` が返り、LOG_DEBUG して `continue`（L2659–2662）。FRR コマンドは一切発行されない。

**順序依存**: `BGP_PEER_GROUP_AF` エントリを書く前に、同一 VRF の `BGP_GLOBALS` エントリ（`local_asn` を含む）が CONFIG_DB に書かれていなければならない。

- evidence: `frrcfgd.py:2656–2662`
- 方向: 先行必須（hard block）

### 2. BGP_PEER_GROUP — peer-group の FRR 存在が先行必須

AF コマンドは `address-family <af> <ip_type>` コンテキスト内で `neighbor <pg_name> <attr>` 形式で発行される（L2869–2872）。FRR bgpd において peer-group が未定義の状態でこれを実行すると vtysh コマンドが失敗し、`failed running BGP neighbor AF config command` が LOG_ERR される（L2873）。

`BGP_PEER_GROUP` ハンドラ（`bgp_neighbor_handler`）は `neighbor <pg> peer-group` コマンドで FRR に peer-group を作成する（L2796–2801）。

**順序依存**: `BGP_PEER_GROUP_AF` を書く前に、同一 VRF の `BGP_PEER_GROUP|<vrf>|<pg_name>` エントリが CONFIG_DB に書かれ、frrcfgd が FRR に peer-group を登録済みでなければならない。

- evidence: `frrcfgd.py:2790–2801`, `frrcfgd.py:2865–2873`
- 方向: 先行必須（FRR コマンド失敗）

### 3. BGP_GLOBALS_AF — address-family コンテキストの有効化が先行必須

FRR における `address-family <af> <ip_type>` コンテキストは、`BGP_GLOBALS_AF` ハンドラ（`bgp_af_handler`）が `router bgp <asn> vrf <vrf> / address-family <af> <ip_type>` を発行することで初めて有効になる（L2771–2781）。このコンテキストが存在しない状態で `BGP_PEER_GROUP_AF` の AF コマンドを投入すると、vtysh がエラーを返す。

`table_handler_list` の順序（L2293–2305）でも `BGP_GLOBALS_AF`（#4）が `BGP_PEER_GROUP_AF`（#12）より前に登録されており、起動時の一括適用でもこの順序が保証される。

**順序依存**: `BGP_PEER_GROUP_AF` を書く前に、対応する `BGP_GLOBALS_AF|<vrf>|<af_safi>` エントリが CONFIG_DB に存在し frrcfgd が address-family コンテキストを FRR に作成済みでなければならない。

- evidence: `frrcfgd.py:2293–2305`, `frrcfgd.py:2771–2781`
- 方向: 先行必須（FRR コンテキスト未存在）

### 4. ROUTE_MAP — route_map_in / route_map_out 参照先の先行推奨

`route_map_in` / `route_map_out` / `default_rmap` / `unsuppress_map_name` は route-map 名を文字列で参照する。FRR は未定義 route-map を参照する `neighbor PG route-map <name> in/out` を受け付けるが、実際のフィルタは route-map が定義された時点で初めて有効になる。また、`bgp_table_handler_common()` の ROUTE_MAP ブランチ（L3109–3148）では `route_map` 辞書に存在しない名前に対して LOG_ERR + continue する。

**順序依存**: `route_map_in` / `route_map_out` に名前を書く場合、対応する `ROUTE_MAP|<name>|<seq>` エントリが CONFIG_DB に先行して存在することを推奨する。先に BGP_PEER_GROUP_AF を書いた場合、FRR はコマンドを受け付けるが route-map が未定義のためフィルタが機能しない中間状態になる。

- evidence: `frrcfgd.py:2669–2676`, `frrcfgd.py:3109–3133`
- 方向: 先行推奨（中間状態は発生するが hard block ではない）

### 5. bgpd CLI 投入順序 — address-family 内コマンドの順序依存

frrcfgd が生成する vtysh コマンド列は `configure terminal / router bgp <asn> vrf <vrf> / address-family <af> <ip_type>` の順でプレフィックスを組み立て、その後 `key_map.run_command()` が各 leaf を順に適用する（L2869–2872）。

FRR bgpd において `max_prefix_limit` が必須アンカーであり、`max_prefix_warning_threshold` / `max_prefix_restart_interval` / `max_prefix_warning_only` は `max_prefix_limit` が設定されていない場合は無視される（`++` オプション連鎖）。

**CLI 投入順序依存**: `max_prefix_*` フィールドは `max_prefix_limit` を必ず先に（または同時に）書くこと。また `allow_as_count` / `allow_as_origin` は `allow_as_in=true` が前提。`nexthop_self_force` は `nhself=true` との同時設定が前提（J2 テンプレ系）。

- evidence: `frrcfgd.py:2865–2872`, Phase A defaults ブロック（bgp-peer-group-af.md）
- 方向: 同時書き込み推奨（個別フィールドの先後で FRR の出力が変わる）

---

## 順序依存サマリ

| # | 先行テーブル / 設定 | 依存元フィールド | 方向 | 緩和策 | evidence |
|---|---|---|---|---|---|
| 1 | `BGP_GLOBALS|<vrf>.local_asn` | 全フィールド（VRF guard） | 先行必須（hard block） | なし（silent skip） | `frrcfgd.py:2656–2662` |
| 2 | `BGP_PEER_GROUP|<vrf>|<pg_name>` | 全フィールド（FRR peer-group 未定義） | 先行必須（FRR コマンド失敗） | なし（LOG_ERR + continue） | `frrcfgd.py:2790–2801, 2873` |
| 3 | `BGP_GLOBALS_AF|<vrf>|<af_safi>` | 全フィールド（AF コンテキスト） | 先行必須（FRR コンテキスト未存在） | 起動時は table_handler_list 順で自動保証 | `frrcfgd.py:2297, 2771–2781` |
| 4 | `ROUTE_MAP|<name>|<seq>` | `route_map_in`, `route_map_out`, `default_rmap`, `unsuppress_map_name` | 先行推奨（中間状態） | FRR は名前を受付、route-map 定義後に有効化 | `frrcfgd.py:3109–3133` |
| 5 | bgpd CLI 内 `max_prefix_limit` | `max_prefix_warning_threshold`, `max_prefix_restart_interval`, `max_prefix_warning_only` | 同時書き込み推奨 | limit なしは FRR が無視 | Phase A defaults |
