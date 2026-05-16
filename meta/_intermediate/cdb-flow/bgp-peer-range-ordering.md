# BGP_PEER_RANGE — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_PEER_RANGE`
Consumer: `bgpcfgd` / `BGPPeerMgrBase` (peer_type="dynamic") (`sonic-bgpcfgd/bgpcfgd/managers_bgp.py`)、`frrcfgd` / `BGPConfigDaemon` (`sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
スキャン範囲: `managers_bgp.py` (add_peer, update_peer, del_handler, post_dependencies_init, apply_op)、`frrcfgd.py` (__update_bgp, bgp_global_handler, __apply_dep_vrf_table, BGP_GLOBALS_LISTEN_PREFIX ハンドラ)

---

## 検出した順序依存・タイミング依存

### 1. BGP_GLOBALS (local_asn) が先行必須 — frrcfgd 経路

`frrcfgd` の `__update_bgp()` は VRF ベーステーブルを処理する前に `__get_vrf_asn(vrf)` を呼び出す。
`local_asn` が `bgp_asn` キャッシュにない場合（BGP_GLOBALS がまだ書かれていない）、処理は即座に `continue` でスキップされる（silent drop）。

```python
# frrcfgd.py:2658-2662
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.format(table, vrf))
    continue
```

`BGP_GLOBALS_LISTEN_PREFIX` は `vrf_tables` に属しており（frrcfgd.py:2138）、この guard が適用される。
`BGP_PEER_RANGE` は bgpcfgd が担当するが、bgpcfgd も `bgp_asn`（`DEVICE_METADATA.localhost.bgp_asn`）を deps に登録しており、未設定の場合 `add_peer()` が `False` を返してリトライ待ちになる（managers_bgp.py:192）。

**順序依存**: `BGP_PEER_RANGE` エントリを書く前に `BGP_GLOBALS|<vrf>` の `local_asn` を設定しておく必要がある。先に書いた場合は silent drop（リトライなし）。

### 2. `bgp listen range` は peer-group 作成後に発行される — frrcfgd の defer 機構

`frrcfgd` は `BGP_PEER_GROUP` の `set_handler` 内で peer-group を作成した後、`__apply_dep_vrf_table(vrf, 'BGP_GLOBALS_LISTEN_PREFIX', match=match_pg)` を呼んで保留中の listen range を後付け適用する（frrcfgd.py:2847）。

この defer 機構は `BGP_PEER_GROUP` が先行登録されていない場合に listen range コマンド発行を遅延させる。ただし bgpcfgd 経路（`BGPPeerMgrBase`）では peer-group の作成は `BGPPeerGroupMgr` が担い、`add_peer()` 内でテンプレートを直接レンダリングするため、同様の defer は存在しない。

**順序依存（frrcfgd 経路）**: `BGP_PEER_GROUP` → `BGP_GLOBALS_LISTEN_PREFIX` の順が自動保証される。逆順の場合は listen range が defer キューに積まれ、peer-group 作成後に再適用される。

### 3. DEL 時: listen range を先に削除してから peer-group を削除（FRR 10.1+）

FRR 10.1 以降、peer-group に listen range が紐付いている場合、peer-group を先に削除しようとすると FRR がエラーを返す。
`del_handler()` はこれに対応し、`no bgp listen range <prefix> peer-group <name>` を先に発行してから peer-group 削除コマンドを送る。

```python
# managers_bgp.py:456-472
# Starting with FRR 10.1, if a peer group is attached to a "listen range",
# the range must be removed before the peer group can be deleted.
if self.peer_type == 'dynamic' or self.peer_type == 'sentinels':
    ...
    cmd = self.templates["no listen range"].render(ip_range=ip_range, peer_group=nbr)
    ret_code = self.apply_op(cmd, vrf)
```

listen range 削除が失敗しても `log_err` のみで peer-group 削除を続行する。これにより FRR 側でエラーが発生するリスクがある。

**順序依存（DEL 時）**: listen range → peer-group の順で削除が必要（bgpcfgd が自動処理）。外部ツール（CLI 等）からの直接削除では順序を守らないと FRR エラーになる。

### 4. `bgp_asn` (DEVICE_METADATA) が bgpcfgd の deps に登録 — 起動時先行必須

`BGPPeerMgrBase.__init__()` の `deps` リストに `("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn")` が含まれる（managers_bgp.py:119）。

`add_peer()` は `bgp_asn = self.directory.get_slot(...)["localhost"]["bgp_asn"]` を直接参照し、存在しない場合 KeyError → テンプレートエラー → drop。

**順序依存**: `DEVICE_METADATA|localhost.bgp_asn` が CONFIG_DB に設定されていない状態では `BGP_PEER_RANGE` エントリは適用されない（silent drop）。

### 5. `ip_range` の設定順序 — change_ip_range による差分管理

`update_peer()` で `ip_range` が変更された場合、`change_ip_range()` が既存 range と新 range の差分を計算して `no bgp listen range` / `bgp listen range` を選択的に発行する（managers_bgp.py:317）。

`get_existing_ip_ranges()` が vtysh から現在の range を取得できない場合、空リストを返して全 range を新規追加として処理する（差分なし）。

**順序依存**: 複数の `ip_range` エントリを追加・変更する場合は SET を順次発行すること。並行して複数の ip_range 変更を CONFIG_DB に書くと、`get_existing_ip_ranges()` の結果が古い状態で差分計算が行われ、重複 range や不要な `no bgp listen range` が発行されるリスクがある。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `BGP_GLOBALS.<vrf>.local_asn` → `BGP_PEER_RANGE` | 先行必須（欠如時 silent drop） | bgpcfgd は deps ガードで再試行待ち、frrcfgd は continue でスキップ（リトライなし） |
| 2 | `BGP_PEER_GROUP` → `BGP_GLOBALS_LISTEN_PREFIX` (frrcfgd) | 自動 defer（逆順は後付け再適用） | `__apply_dep_vrf_table` で peer-group 作成後に自動再適用 |
| 3 | listen range 削除 → peer-group 削除（FRR 10.1+） | 強制順序（bgpcfgd が自動処理） | 外部直接操作時は `no bgp listen range` を先に発行すること |
| 4 | `DEVICE_METADATA.localhost.bgp_asn` → `BGP_PEER_RANGE` | 先行必須（deps guard、欠如時 drop） | 起動時は DEVICE_METADATA が先に読み込まれる前提 |
| 5 | ip_range 差分計算の逐次性 | 推奨（並行変更は重複リスク） | SET を逐次発行し vtysh 反映を確認してから次変更を送ること |
