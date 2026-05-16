# BGP_NEIGHBOR — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/bgp-neighbor.md` Phase C 追加分。
leafref として YANG に明示されているもの以外の、実装上の暗黙参照を網羅する。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | bgpcfgd の BGP_NEIGHBOR ハンドラ（BGPPeerMgrBase） |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | frrcfgd の BGP_NEIGHBOR ハンドラ |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang` | YANG 定義 |

## YANG 明示 leafref (参考)

| leaf | leafref 先 |
|------|-----------|
| `vrf_name` (BGP_NEIGHBOR_LIST) | `BGP_GLOBALS.vrf_name` |
| `peer_group_name` (BGP_NEIGHBOR_LIST) | `BGP_PEER_GROUP.peer_group_name` (同 vrf 内) |
| `neighbor` (BGP_NEIGHBOR_LIST) | union: IP addr / `PORT.name` / `PORTCHANNEL.name` / Vlan文字列 |
| `vrf_name` (BGP_NEIGHBOR_AF_LIST) | `BGP_GLOBALS.vrf_name` |
| `neighbor` (BGP_NEIGHBOR_AF_LIST) | `BGP_NEIGHBOR.BGP_NEIGHBOR_LIST.neighbor` |

## 暗黙参照 (leafref 超え)

### 1. DEVICE_METADATA["localhost"]["bgp_asn"]
- **参照先フィールド**: `DEVICE_METADATA|localhost|bgp_asn`
- **参照元**: `managers_bgp.py` L119, L192, L501; `frrcfgd.py` L2163
- **意味**: neighbor 追加時に `router bgp <asn>` コマンドを生成するために必須。bgp_asn が未設定だと bgpcfgd は neighbor を追加できない（依存チェックが先行する）。

### 2. DEVICE_METADATA["localhost"]["type"] / ["subtype"]
- **参照先フィールド**: `DEVICE_METADATA|localhost|type`、`subtype`
- **参照元**: `managers_bgp.py` L120; Jinja2 テンプレート内で `peer_type` 分岐と組み合わせて使用
- **意味**: デバイスロール (ToRRouter / SpineRouter 等) によって生成する FRR コマンドが変わる（allowas-in、table-map、next-hop-self など）。

### 3. DEVICE_METADATA["localhost"]["deployment_id"]
- **参照先フィールド**: `DEVICE_METADATA|localhost|deployment_id`
- **参照元**: `managers_bgp.py` L143（`check_deployment_id=True` のとき依存に追加）
- **意味**: deployment_id を Jinja2 テンプレートに渡し、ルートマップの community 値や EBGP policy に埋め込む。`bgp.use_deployment_id` 定数が true の場合のみ有効。

### 4. LOOPBACK_INTERFACE["Loopback0"]
- **参照先テーブル**: `LOOPBACK_INTERFACE`、キー `Loopback0|<prefix>`
- **参照元**: `managers_bgp.py` L121, L184-189, L212, L216-218
- **意味**: neighbor 追加前のガード条件。Loopback0 の IPv4 アドレスが存在しない かつ bgp_router_id も未設定の場合は `return False`（再試行待ち）。また、Jinja2 テンプレートへ `CONFIG_DB__LOOPBACK_INTERFACE` として全ループバック情報を渡す。
- **追加**: `internal` peer_type の場合は `LOOPBACK_INTERFACE|Loopback4096` も依存に追加（L146）。

### 5. DEVICE_NEIGHBOR_METADATA
- **参照先テーブル**: `DEVICE_NEIGHBOR_METADATA`（全エントリ）
- **参照元**: `managers_bgp.py` L140, L220-224
- **意味**: `check_neig_meta=True` かつ `bgp.use_neighbors_meta=true` の場合、neighbor の `name` フィールドが `DEVICE_NEIGHBOR_METADATA` に存在しなければ `return False`（再試行待ち）。これは minigraph 由来のメタデータ連携ガード。

### 6. BGP_DEVICE_GLOBAL["tsa_enabled"] / ["idf_isolation_state"]
- **参照先テーブル**: `BGP_DEVICE_GLOBAL`
- **参照元**: `managers_bgp.py` L122-123; `BGPPeerGroupMgr.update_pg()` L62-63
- **意味**: TSA (Traffic Shift Away) / IDF isolation の状態を peer-group テンプレートレンダリング時に参照し、route-map を動的に付与する。neighbor 追加の都度 `DeviceGlobalCfgMgr.check_state_and_get_tsa_routemaps()` を呼ぶ。

### 7. BGP_BBR
- **参照先テーブル**: `BGP_BBR`（key: `all`、field: `status`）
- **参照元**: `managers_bgp.py` L206
- **意味**: Best Border Router (BBR) の状態を Jinja2 テンプレートへ `CONFIG_DB__BGP_BBR` として渡す。テンプレート側で `bbr_enabled` フラグの有無により BGP add-path / bestpath 設定が変わる。

### 8. BGP_GLOBALS (frrcfgd パス)
- **参照先テーブル**: `BGP_GLOBALS`
- **参照元**: `frrcfgd.py` L2175-2178; `frrcfgd.py` L2450-2453
- **意味**: frrcfgd パス (`frr_mgmt_framework_config=true`) では neighbor を FRR に反映するために VRF の `local_asn` を `BGP_GLOBALS` から取得する。BGP_GLOBALS に該当 VRF のエントリがなければ neighbor 設定を skip。

### 9. BGP_PEER_GROUP (frrcfgd パス)
- **参照先テーブル**: `BGP_PEER_GROUP`
- **参照元**: `frrcfgd.py` L2187, L2828
- **意味**: neighbor の `peer_group_name` フィールドが参照する peer-group が `BGP_PEER_GROUP` に存在しない場合、`LOG_ERR "invalid peer-group %s was referenced"` を出して continue（neighbor 設定を drop）。frrcfgd は BGP_PEER_GROUP を先にキャッシュし、存在チェックを行う。

### 10. PORT / PORTCHANNEL (interface 型 neighbor)
- **参照先テーブル**: `PORT`、`PORTCHANNEL`
- **参照元**: YANG leafref (sonic-bgp-neighbor.yang L84-88); frrcfgd.py L2807
- **意味**: `neighbor` フィールドが IP でなくインタフェース名 (PORT/PORTCHANNEL 名) の場合、frrcfgd は `vtysh neighbor <name> interface` コマンドを発行する。失敗すると `LOG_ERR "failed to create neighbor of interface"` を出して skip。

### 11. LOCAL["local_addresses"] / LOCAL["interfaces"]
- **参照先スロット**: bgpcfgd 内部ディレクトリの `LOCAL` スロット
- **参照元**: `managers_bgp.py` L124-125; `get_local_interface()` 経由
- **意味**: neighbor の `local_addr` フィールドが設定されている場合、その IP アドレスが現在のインタフェース（INTERFACE テーブル由来のローカルアドレス一覧）に存在するかを確認する。存在しなければ `return False`（待機）。実体は `sonic-swss` が管理する INTERFACE テーブルの IP エントリ。

## 参照関係サマリ

```
BGP_NEIGHBOR
  ├─ [YANG leafref] BGP_GLOBALS.vrf_name          (vrf_name フィールド)
  ├─ [YANG leafref] BGP_PEER_GROUP.peer_group_name (peer_group_name フィールド)
  ├─ [YANG leafref] PORT.name / PORTCHANNEL.name   (neighbor フィールド, union)
  ├─ [暗黙] DEVICE_METADATA.localhost.bgp_asn      (必須依存, bgpcfgd+frrcfgd)
  ├─ [暗黙] DEVICE_METADATA.localhost.type         (Jinja2 テンプレート分岐)
  ├─ [暗黙] DEVICE_METADATA.localhost.deployment_id (条件付き: use_deployment_id)
  ├─ [暗黙] LOOPBACK_INTERFACE["Loopback0"]        (ガード: lo_ipv4 or bgp_router_id)
  ├─ [暗黙] LOOPBACK_INTERFACE["Loopback4096"]     (条件付き: internal peer_type)
  ├─ [暗黙] DEVICE_NEIGHBOR_METADATA               (条件付き: use_neighbors_meta)
  ├─ [暗黙] BGP_DEVICE_GLOBAL.tsa_enabled          (TSA routemap 付与)
  ├─ [暗黙] BGP_DEVICE_GLOBAL.idf_isolation_state  (IDF routemap 付与)
  ├─ [暗黙] BGP_BBR.all.status                     (BBR 状態, テンプレート渡し)
  ├─ [暗黙] BGP_GLOBALS.local_asn                  (frrcfgd: VRF ASN 解決)
  ├─ [暗黙] BGP_PEER_GROUP (実体確認)              (frrcfgd: peer-group 存在ガード)
  └─ [暗黙] INTERFACE (ローカルアドレス一覧)       (bgpcfgd: local_addr 整合ガード)
```

## evidence

- `managers_bgp.py`: L119-146 (deps 宣言), L186-224 (add_peer ガード群), L205-213 (テンプレートへの渡し)
- `frrcfgd.py`: L2162-2186 (初期化時 DEVICE_METADATA/BGP_GLOBALS 読み取り), L2803-2812 (interface neighbor 作成), L2826-2830 (peer-group 存在チェック)
- `sonic-bgp-neighbor.yang`: L75-103 (leafref 定義)
