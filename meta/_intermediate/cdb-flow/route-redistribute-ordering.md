# ROUTE_REDISTRIBUTE — Phase B 書込み順依存スキャンノート

対象テーブル: `ROUTE_REDISTRIBUTE`
Consumer: `frrcfgd.BGPConfigDaemon` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: L2293-2360 (table_handler_list / subscribe_all), L2530-2547 (__apply_dep_vrf_table), L2650-2665 (local_asn ゲート), L2695-2710 (BGP_GLOBALS 後の ROUTE_REDISTRIBUTE 再適用), L3149-3180 (ROUTE_REDISTRIBUTE イベント処理全行精読)

---

## 検出した順序依存・タイミング依存

### 1. BGP_GLOBALS (local_asn) が先行必須 — ハード制約

`frrcfgd.py` L2658-2661:

```python
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
    continue
```

`ROUTE_REDISTRIBUTE` は `vrf_tables` に含まれるため（L2138）、すべてのイベント処理に先立ち `__get_vrf_asn(vrf)` を呼び出す。VRF に対応する `BGP_GLOBALS.local_asn` が CONFIG_DB に未設定の場合、`local_asn is None` となり当該 ROUTE_REDISTRIBUTE イベントは **silent drop** される（ログは DEBUG レベルのみ）。

- `__get_vrf_asn()` は `self.bgp_asn[vrf]`（BGP_GLOBALS イベントで設定）または `self.metadata_asn`（DEVICE_METADATA.bgp_asn、default VRF のみ）を参照（L2442-2447）。
- **`ROUTE_REDISTRIBUTE|<vrf>|…` を書き込む前に必ず `BGP_GLOBALS|<vrf>` の `local_asn` を設定すること。** 逆順の場合は silent drop。

evidence: `frrcfgd.py:2658-2661`, `frrcfgd.py:2442-2447`

### 2. BGP_GLOBALS 設定後に ROUTE_REDISTRIBUTE が自動再適用される

`frrcfgd.py` L2703-2704:

```python
self.bgp_asn[vrf] = dval.data
self.__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')
```

`BGP_GLOBALS.local_asn` の SET が成功した直後、`frrcfgd` は `__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` を呼び出し、すでに CONFIG_DB に存在する当該 VRF の全 ROUTE_REDISTRIBUTE エントリを再適用する（L2530-2545: `config_db.get_table('ROUTE_REDISTRIBUTE')` で全エントリを走査し `bgp_message` キューに再送）。

つまり、BGP_GLOBALS.local_asn 設定**前**に ROUTE_REDISTRIBUTE エントリを CONFIG_DB に書いておいた場合は silent drop されるが、その後 BGP_GLOBALS.local_asn を設定すると **自動的にリカバーされる**。ただしこの自動再適用はアトミックではなく、BGP_GLOBALS イベントと ROUTE_REDISTRIBUTE の再適用の間に他のテーブル更新が割り込む可能性があることに注意する。

evidence: `frrcfgd.py:2703-2704`, `frrcfgd.py:2530-2545`

### 3. dst_protocol = 'bgp' 固定 — 'bgp' 以外は LOG_ERR で drop

`frrcfgd.py` L3156-3158:

```python
if dst_proto != 'bgp':
    syslog.syslog(LOG_ERR, 'only bgp could be used as dst protocol, but {} was given')
    continue
```

`dst_protocol` フィールドが `'bgp'` でない場合、ROUTE_REDISTRIBUTE イベントは処理されずに明示的に drop される。この制約はキー構造の段階では検証されず、ハンドラ内でランタイムに判定される。

evidence: `frrcfgd.py:3156-3158`

### 4. ospf3 → ospf6 変換 — af=ipv6 のときのみ

`frrcfgd.py` L3151-3152:

```python
if af == 'ipv6' and src_proto == 'ospf3':
    src_proto = 'ospf6'
```

CONFIG_DB キーに `ospf3` と書いても、FRR に送出される vtysh コマンドは `redistribute ospf6` になる（`af=ipv6` の場合のみ）。`af=ipv4` + `src_proto=ospf3` の組み合わせはそのまま `redistribute ospf3` として送出されるが、FRR bgpd は `ospf3` を認識しないため設定エラーになる。**書込み順の問題ではないが、src_protocol + address_family の組み合わせ制約を CONFIG_DB 書き込み時点で守ること。**

evidence: `frrcfgd.py:3151-3152`

### 5. table_handler_list 上の位置（起動時処理順序）

`table_handler_list` における `ROUTE_REDISTRIBUTE` の登録位置（L2316）は:

```
VRF → DEVICE_METADATA → BGP_GLOBALS → BGP_GLOBALS_AF → PREFIX_SET → PREFIX → COMMUNITY_SET → EXTENDED_COMMUNITY_SET → ROUTE_MAP → BGP_PEER_GROUP → BGP_NEIGHBOR → BGP_PEER_GROUP_AF → BGP_NEIGHBOR_AF → BGP_GLOBALS_LISTEN_PREFIX → BGP_GLOBALS_EVPN_VNI → … → ROUTE_REDISTRIBUTE → BGP_GLOBALS_AF_AGGREGATE_ADDR → …
```

起動時に `subscribe_all()` → `listen()` が呼ばれ、`table_handler_list` 順に subscribe する（L2360-2361）。Redis keyspace 通知は非同期に到達するため、起動時の subscribe 順序が処理順序を保証するわけではない。ただし `unified` モード（`config_mode == "unified"`）ではさらに `table_handler_list` 順に既存エントリを `bgp_message` キューへ投入してから逐次処理するため、**`BGP_GLOBALS` が `ROUTE_REDISTRIBUTE` より先に処理されることが保証される**（unified モード時）。

evidence: `frrcfgd.py:2293-2360`, `frrcfgd.py:2344-2355`

### 6. DEL 順序 — BGP_GLOBALS DEL 前に ROUTE_REDISTRIBUTE を DEL すること

`BGP_GLOBALS.local_asn` を削除すると `__delete_vrf_asn()` が呼ばれ `bgp_asn[vrf]` が消去される。その後 ROUTE_REDISTRIBUTE エントリを削除しようとしても `local_asn is None` で silent drop され、FRR bgpd 側に `no redistribute <src>` が送出されない。結果として **FRR は redistribute 設定を保持したまま**になる。

**推奨削除順序**: `ROUTE_REDISTRIBUTE` 全エントリを DEL → `BGP_GLOBALS.local_asn` を DEL。

evidence: `frrcfgd.py:2658-2661`, `frrcfgd.py:2449-2465`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 影響 | 緩和策 |
|---|----------|------|------|--------|
| 1 | `BGP_GLOBALS.local_asn` 設定 → `ROUTE_REDISTRIBUTE` 書き込み | ハード先行必須 | silent drop | BGP_GLOBALS を先に設定 |
| 2 | BGP_GLOBALS.local_asn SET 後に ROUTE_REDISTRIBUTE 自動再適用 | 自動リカバー | 順序逆でも最終的に反映される | 本番では正順を守る |
| 3 | `dst_protocol='bgp'` のみ許可 | ランタイム制約 | LOG_ERR + drop | dst_protocol は 'bgp' 固定で書くこと |
| 4 | `ospf3` + `ipv6` → FRR では `ospf6` に変換 | 変換（意図的）| FRR 送出コマンドが変わる | CONFIG_DB 値と FRR 実際コマンドの乖離を認識 |
| 5 | unified モード: BGP_GLOBALS が ROUTE_REDISTRIBUTE より先に処理 | 起動時保証 | 正常 | unified モードでは順序保証あり |
| 6 | `ROUTE_REDISTRIBUTE` DEL → `BGP_GLOBALS` DEL | 推奨削除順序 | FRR 側に redistribute 残存 | ROUTE_REDISTRIBUTE を先に全削除 |
