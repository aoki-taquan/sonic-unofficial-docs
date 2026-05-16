# BGP_MONITORS — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_MONITORS`
Consumer: `bgpcfgd` / `BGPPeerMgrBase(peer_type="monitors")` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`)
スキャン範囲: `BGPPeerMgrBase.__init__()`, `set_handler()`, `add_peer()`, `BGPPeerGroupMgr.update()`, `main.py` managers リスト全行精読

---

## 検出した順序依存・タイミング依存

### 1. DEVICE_METADATA 先行必須 — `bgp_asn` / `bgp_router_id` ガード

- `BGPPeerMgrBase.__init__()` は deps リストに `("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn")` を登録する (`managers_bgp.py:119`)。
- `add_peer()` で `lo_ipv4 is None AND "bgp_router_id" not in DEVICE_METADATA["localhost"]` の場合は即 `return False`（再試行待ち）(`managers_bgp.py:186-189`)。
- FRR への `router bgp <asn>` コマンドは `bgp_asn = DEVICE_METADATA["localhost"]["bgp_asn"]` から取得し、`remote-as` も同値を使用 (`managers_bgp.py:192`, `instance.conf.j2:4`)。
- **順序依存**: `BGP_MONITORS` エントリを書く前に `DEVICE_METADATA|localhost.bgp_asn` が存在しなければ `add_peer()` は空 `bgp_asn` 参照で `KeyError` になる。`bgp_router_id` も未設定かつ Loopback0 IPv4 未設定の場合は `return False` → 再試行ループに入る。
- **推奨**: `DEVICE_METADATA|localhost` (`bgp_asn`, `bgp_router_id`) を先に書いてから `BGP_MONITORS` エントリを追加すること。
- evidence: `managers_bgp.py:119,186-192`

### 2. BGP_GLOBALS (Loopback0 / ルータ ID 相当) 先行必須 — peer-group update-source

- `BGPPeerGroupMgr.update_pg()` は `peer-group.conf.j2` をレンダリングして FRR に `neighbor BGPMON update-source <lo0_ipv4>` を注入する (`peer-group.conf.j2:12`)。
- `lo0_ipv4` は `get_lo_ipv4("Loopback0|")` で CONFIG_DB の `CFG_LOOPBACK_INTERFACE_TABLE_NAME` から取得する。
- deps に `("CONFIG_DB", CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0")` が登録済み (`managers_bgp.py:121`)。
- **順序依存**: `Loopback0` IPv4 アドレスが `LOOPBACK_INTERFACE|Loopback0|<ip>` として設定される前に `BGP_MONITORS` を書くと、`lo0_ipv4=None` となり `update-source` が未設定（`result_without_lo0_ipv4.conf` 参照）。BGP session 確立後に Loopback0 を追加してもピアの `update-source` は再設定されない（`update_peer()` は `admin_status` 以外の更新を drop するため）。
- **推奨**: `LOOPBACK_INTERFACE|Loopback0|<ip>` を先に設定してから `BGP_MONITORS` エントリを書くこと。
- evidence: `managers_bgp.py:121,216-218`, `peer-group.conf.j2:12`, `tests/data/monitors/peer-group.conf/result_without_lo0_ipv4.conf`

### 3. ROUTE_MAP (policies.conf.j2) 先行注入 — peer-group 参照前に route-map 定義が必要

- `BGPPeerGroupMgr.update()` は `update_policy()` → `update_pg()` の順で FRR にコマンドを送出する (`managers_bgp.py:36-38`)。
- `update_policy()` は `FROM_BGPMON deny 10` / `TO_BGPMON permit 10` の route-map を定義し、`update_pg()` は `neighbor BGPMON route-map FROM_BGPMON in` / `neighbor BGPMON route-map TO_BGPMON out` を peer-group に紐付ける。
- FRR は route-map が未定義の状態で `route-map <name> in/out` を受け取ると警告を出して適用しない場合がある。
- **順序依存**: `bgpcfgd` 内部では `update_policy()` → `update_pg()` の順序が保証されているが、外部から直接 vtysh で peer-group 設定を先行させた場合や、FRR restart 後の replay 時に policy テンプレートが失敗すると route-map 未定義のまま peer-group が参照する状態になり得る。
- **推奨**: `bgpcfgd` 経由（CLI/minigraph）で `BGP_MONITORS` を設定することで `update_policy()` 先行が自動保証される。vtysh 直接設定は非推奨。
- evidence: `managers_bgp.py:36-38,46-52`, `tests/data/monitors/policies.conf/result_all.conf`

### 4. BGP_GLOBALS / bgpcfgd ハンドラ起動順 — main.py での manager 登録位置

- `main.py` の managers リストでは `BGPDataBaseMgr(DEVICE_METADATA)` が先頭（L75）、`BGPPeerMgrBase("BGP_MONITORS")` が L89 に配置されている。
- `BGPDataBaseMgr` は DEVICE_METADATA の変更を directory に格納し、`BGPPeerMgrBase` の deps ガード（`bgp_asn` 依存）を解除する役割を持つ。
- **起動順**: `bgpcfgd` 内部では `managers` リストを順番に `subscribe()` するが、イベントループは全 manager が購読後に開始される。CONFIG_DB に既にデータが存在する場合は初期ロード時に deps ガードが評価される。
- **順序依存**: `bgpcfgd` コンテナ起動時に CONFIG_DB に `BGP_MONITORS` エントリが既に存在し、かつ `DEVICE_METADATA.bgp_asn` も存在する場合は問題ない。`bgpcfgd` 起動前に `BGP_MONITORS` を書き込み、起動後に `DEVICE_METADATA` を書き込む構成は `return False` → 再試行で自動解決する。
- evidence: `main.py:75-89`

### 5. `local_addr` インターフェース依存 — 対応インターフェースが先行必須

- `add_peer()` で `local_addr` が設定されている場合、`get_local_interface(data["local_addr"])` が `None` を返すと `return False`（再試行待ち）(`managers_bgp.py:199-202`)。
- `get_local_interface()` は `directory.get_slot("LOCAL", "local_addresses")` と `directory.get_slot("LOCAL", "interfaces")` を参照する。
- deps に `("LOCAL", "local_addresses", "")` / `("LOCAL", "interfaces", "")` が登録済み (`managers_bgp.py:124-125`)。
- **順序依存**: `BGP_MONITORS` エントリの `local_addr` に指定した IP のインターフェース（例: `INTERFACE|eth0|192.0.2.1/24`）が CONFIG_DB に存在しない場合、ピア追加は無限再試行状態になる。インターフェース追加後に `InterfaceMgr` が directory を更新し、次のイベントループで自動解決する。
- evidence: `managers_bgp.py:124-125,194-202,528-539`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DEVICE_METADATA\|localhost.bgp_asn` → `BGP_MONITORS` | 先行必須（欠如時 KeyError / return False） | deps ガード + return False で再試行 |
| 2 | `LOOPBACK_INTERFACE\|Loopback0\|<ip>` → `BGP_MONITORS` | 推奨先行（欠如時 update-source 未設定） | lo0_ipv4=None でも peer 追加は続行（update-source なし） |
| 3 | route-map 定義 (`policies.conf.j2`) → peer-group route-map 紐付け | bgpcfgd 内部で自動保証（update_policy → update_pg 順） | vtysh 直接設定時は手動で先行定義が必要 |
| 4 | `BGPDataBaseMgr(DEVICE_METADATA)` 登録 → `BGPPeerMgrBase(BGP_MONITORS)` イベント処理 | main.py 登録順で自動保証 | deps ガード + return False で再試行 |
| 5 | `INTERFACE\|<intf>\|<local_addr>` → `BGP_MONITORS.local_addr` | 推奨先行（欠如時 return False 再試行ループ） | InterfaceMgr が directory 更新後に自動解決 |
