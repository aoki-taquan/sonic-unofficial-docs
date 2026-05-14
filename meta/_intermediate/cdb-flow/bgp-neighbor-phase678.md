# BGP_NEIGHBOR — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/bgp-neighbor.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py / managers_bgp.py 代入)

<!-- derivation -->

### 1. bgp_sessions → `BGP_NEIGHBOR` の一括代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2273`

```python
results['BGP_NEIGHBOR'] = bgp_sessions
```

- `bgp_sessions` は minigraph XML の `<BGPSession>` タグを解析して構築される辞書。各エントリに `name`、`local_addr`、`nhopself`、`holdtime`、`keepalive`、`weight` 等が代入される。
- `asn` は同一デバイスの `<DeviceAttribute><ASN>` から自動解決される（minigraph.py:1413,1417）。

### 2. `admin_status` — start_peer / end_peer から条件代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1368,1379`

```python
table[start_peer.lower()]['admin_status'] = admin_status
table[end_peer.lower()]['admin_status'] = admin_status
```

- `<BGPSession><AdminStatus>` が `"down"` の場合のみ `admin_status = down` を代入。指定なし（デフォルト）は `up` として省略。

### 3. `src_address` — BGP Sentinels / PeerRange から代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1399,1406`

```python
bgp_sentinel_sessions[name]['src_address'] = bgpPeer.find(str(QName(ns, "Address"))).text
bgp_peers_with_range[name]['src_address'] = bgpPeer.find(str(QName(ns, "Address"))).text
```

- Sentinel / PeerRange タイプの BGP セッションでは `src_address` が明示的に付与される。通常のピアでは省略。

### 4. managers_bgp.py での `VRF` + neighbor アドレス結合

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:242`

```python
self.directory.put(self.db_name, self.table_name, vrf + '|' + nbr, data)
```

- `BgpNbrmPeer` は CONFIG_DB の `BGP_NEIGHBOR` テーブルを読み取り、VRF 名を prefix に付与してテンプレートレンダリングに渡す。デフォルト VRF では `vrf = ""` となり `|<neighbor_ip>` 形式のキーになる。

<!-- /derivation -->

---

## Phase 7: 条件付き登録 (add_manager)

<!-- derivation -->

### BgpPeerMgr の `check_neig_meta` 条件登録

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:140,143,146`

```python
if check_neig_meta:
    deps.append(("CONFIG_DB", swsscommon.CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME, ""))
if check_deployment_id:
    deps.append(("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/deployment_id"))
if self.check_loopback4096:
    deps.append(("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback4096"))
```

- `check_neig_meta=True` の場合 `DEVICE_NEIGHBOR_METADATA` テーブルへの依存が追加される。依存テーブルが揃うまで `set_handler` は pending 状態を維持し、early return する。
- `Loopback4096` が存在しない場合、VOQ 系 BGP neighbor の登録はスキップされる。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### BgpPeerMgr.set_handler() の early return 条件

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:159,187,192`

1. **bgp_asn 未設定 early return**: `DEVICE_METADATA["localhost"]["bgp_asn"]` が存在しない場合、`set_handler` は即時 `False` を返す（ピア登録をスキップ）。
2. **type 未設定 early return**: `DEVICE_METADATA["localhost"]["type"]` が存在しない場合も同様にスキップ。
3. **neigmeta 依存チェック**: `check_neig_meta=True` かつ `DEVICE_NEIGHBOR_METADATA` が空の場合、`set_handler` は pending リストへ。
4. **dispatch — eBGP / iBGP 分岐**: `peer_asn == bgp_asn` の場合 iBGP テンプレートを選択。異なる場合は eBGP テンプレートへ dispatch。

<!-- /handler-branching -->
