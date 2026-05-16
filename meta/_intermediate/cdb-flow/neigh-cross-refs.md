# NEIGH テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/neigh.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/neighorch.cpp`（APPL_DB `NEIGH_TABLE` → SAI 経路）および `sonic-net/sonic-swss/cfgmgr/nbrmgr.cpp`（CONFIG_DB `NEIGH` → Netlink 経路）。

## スキャン手順

```
grep -nE 'm_intfsOrch\.|m_fdbOrch\.|m_vr_id|getVRFname|getRouterIntfsId|isInbandIntfInMgmtVrf|isRemoteSystemPortIntf|SUBJECT_TYPE_FDB' \
    .cache/sonic-sources/sonic-swss/orchagent/neighorch.cpp
```

## 検出された暗黙参照テーブル / オーケストレーター

### 1. INTERFACE（IntfsOrch 経由）

`addNeighbor()` は先頭で `m_intfsOrch->getRouterIntfsId(alias)` を呼び出し、INTERFACE テーブルが確立した RIF (Router Interface) SAI オブジェクト ID を取得する。RIF が存在しない場合 (`rif_id == SAI_NULL_OBJECT_ID`) は即 `false` を返し SAI プログラミングをスキップする。

| 参照タイミング | 用途 | evidence |
|---|---|---|
| `addNeighbor()` | `rif_id` 取得 → `sai_neighbor_entry_t.rif_id` に設定 | neighorch.cpp:1204–1212 |
| `addNextHop()` | `rif_id` 取得 → `SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID` に設定 | neighorch.cpp:271,304–305 |
| `removeNeighbor()` | `rif_id` 取得 → 削除対象 neighbor_entry の特定 | neighorch.cpp:1492,1501,1633 |
| `doSetNeighTask()` 早期スキップ | `p.m_rif_id == 0` ならキュー留め (`it++`) | neighorch.cpp:949–954 |
| 管理 VRF フィルタ | `isInbandIntfInMgmtVrf(alias)` で管理 VRF 上の neigh をスキップ | neighorch.cpp:912 |
| リモートシステムポート判定 | `isRemoteSystemPortIntf(alias)` でリモート port の neighbor を inband 経由に切替 | neighorch.cpp:260,654,685,833 |
| サブネット判定 | `isPrefixSubnet(ipll_prefix, alias)` で link-local scope の no_host_route 判定 | neighorch.cpp:1232 |

**IntfsOrch との関係**: `NeighOrch` コンストラクタで `m_intfsOrch` として注入され、neighbor 追加/削除のたびに `increaseRouterIntfsRefCount` / `decreaseRouterIntfsRefCount` を呼び出して INTERFACE テーブル側の RIF 参照カウントを管理する。

### 2. VRF（VRFOrch 経由）

VRF は `Port.m_vr_id` フィールドを通じて間接参照される。VLAN 上に同一 IP の neighbor が既に存在する場合、同一 VRF 内かどうかを確認してから古い neighbor を削除する。

| 参照タイミング | 用途 | evidence |
|---|---|---|
| `addNeighbor()` 重複チェック | `existing_vlan.m_vr_id == new_vlan.m_vr_id` で同一 VRF 判定 | neighorch.cpp:1287–1296 |
| `addPrefixRouteForNeighbor()` | `port.m_vr_id` を `sai_route_entry_t.vr_id` に設定 | neighorch.cpp:1082,1091 |
| `removeNeighbor()` | `port_vrf_id = port.m_vr_id` → prefix route 削除時の VR ID | neighorch.cpp:1455–1471 |
| VRF 名ログ出力 | `gDirectory.get<VRFOrch*>()->getVRFname(existing_vlan.m_vr_id)` | neighorch.cpp:1289 |

**デフォルト VRF**: `port.m_vr_id` が 0 の場合は `gVirtualRouterId`（グローバル VRF）を使用する（neighorch.cpp:1077,1456）。

### 3. FDB（FdbOrch 経由）

`NeighOrch` はコンストラクタで `m_fdbOrch->attach(this)` を呼び出し、FDB flush イベントの Observer として登録される。VLAN からポートが削除されると FDB がフラッシュされ、`processFDBFlushUpdate()` が呼ばれて該当 MAC を持つ neighbor エントリが再解決キューに入る。

| 参照タイミング | 用途 | evidence |
|---|---|---|
| `processFDBFlushUpdate()` | FDB エントリの MAC と VLAN を neighbor テーブルと照合し、一致する neighbor を再解決 | neighorch.cpp:155–185 |
| `update(SUBJECT_TYPE_FDB_FLUSH_CHANGE)` | FdbOrch から通知を受けて `processFDBFlushUpdate()` を dispatch | neighorch.cpp:195–198 |
| コンストラクタ | `m_fdbOrch->attach(this)` で Observer 登録 | neighorch.cpp:43 |
| デストラクタ | `m_fdbOrch->detach(this)` で Observer 解除 | neighorch.cpp:67–70 |

**FDB との関係**: NEIGH エントリは FDB エントリの MAC に依存する。VLAN ポート削除で FDB がフラッシュされると、対応する neighbor も自動的に再解決トリガーがかかる。

## 参照方向まとめ

```
CONFIG_DB NEIGH  ─(nbrmgrd)→  Netlink RTM_NEWNEIGH  →  Linux kernel neighbor table
APPL_DB NEIGH_TABLE ─(neighorch)→ IntfsOrch [INTERFACE RIF]
                                          ↓ rif_id
                               SAI create_neighbor_entry / create_next_hop
                                          ↑
                               FdbOrch   [FDB flush 通知]
                               VRFOrch   [Port.m_vr_id → sai_route_entry_t.vr_id]
```

## 主要ソース参照

| ファイル | ref | 内容 |
|---|---|---|
| `orchagent/neighorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d | NeighOrch 実装全体 |
| `cfgmgr/nbrmgr.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d | doSetNeighTask → Netlink |
