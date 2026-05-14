# BGP_PEER_RANGE — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/bgp-peer-range.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py / managers_bgp.py 代入)

<!-- derivation -->

### 1. `bgp_peers_with_range` → `BGP_PEER_RANGE` の代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2275,2607`

```python
results['BGP_PEER_RANGE'] = bgp_peers_with_range
# または
results['BGP_PEER_RANGE'] = {}
```

- `bgp_peers_with_range` は `<PeerRange>` タグを持つ BGP セッション定義から構築される。
- `peerSubnets` がない場合（純粋なルータトポロジ）は空辞書 `{}` が代入される（minigraph.py:2607）。

### 2. `src_address` の自動付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1406,1408`

```python
bgp_peers_with_range[name]['src_address'] = bgpPeer.find(str(QName(ns, "Address"))).text
bgp_peers_with_range[name]['peer_asn'] = bgpPeer.find(str(QName(ns1, "PeerAsn"))).text
```

- PeerRange エントリには `src_address`（ローカル送信元 IP）と `peer_asn`（ピア AS 番号）が自動付与。
- これらは minigraph XML の `<Address>` / `<PeerAsn>` タグから直接マッピングされる。

### 3. managers_bgp.py での VRF prefix 結合

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:89,152`

- `BgpPeerMgr` は `BGP_PEER_RANGE` テーブルを `table_name` パラメータで初期化される。`vrf + '|' + range_name` キーで bgpcfgd の内部 directory に格納される（peer_type="range" として区別）。

<!-- /derivation -->

---

## Phase 7: 条件付き登録 (add_manager)

<!-- derivation -->

### BgpPeerMgr (peer_type="range") の依存チェック

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:119-123`

```python
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
```

- `BGP_PEER_RANGE` ハンドラは `BGP_NEIGHBOR` と同じ依存チェックを共有。`bgp_asn` / `type` / `Loopback0` が存在するまで pending。
- `check_neig_meta=False` がデフォルト（PeerRange は peer-specific な neighbor metadata を必要としない）。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### BgpPeerMgr.set_handler() (range 特化) の分岐

**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:159-250`

1. **bgp_asn 未設定 early return**: `DEVICE_METADATA["localhost"]["bgp_asn"]` が存在しない → 即 `False` を返す（通常ピアと共通）。
2. **peer_asn 比較 dispatch**: `peer_asn == bgp_asn` → iBGP PeerRange テンプレートへ。異なる → eBGP PeerRange テンプレートへ dispatch。
3. **`ip_range` / `name` 検証 early return**: `ip_range` フィールドが CIDR 形式でない、または `name` が空の場合はテンプレートレンダリングをスキップ。
4. **`src_address` 有無による分岐**: `src_address` が存在する場合 `update-source <src>` を bgpd 設定に追加。存在しない場合はデフォルト source を使用（update-source 行を省略）。

<!-- /handler-branching -->
