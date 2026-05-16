# NEIGH — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/neigh.md`
調査日: 2026-05-16
ソース: `sonic-swss/orchagent/neighorch.cpp`

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/neighorch.cpp` | `NeighOrch::doTask` / `addNeighbor` / `addNextHop` — APPL_DB `NEIGH_TABLE` の orchagent 処理本体 |
| `sonic-swss/cfgmgr/nbrmgr.cpp` | `NbrMgr::doSetNeighTask` — CONFIG_DB `NEIGH` の nbrmgrd ハンドラ（Netlink 経由） |

## 検出した書込み順依存

### 1. `allPortsReady()` — 全 PORT/VLAN 初期化先行必須

`NeighOrch::doTask` (neighorch.cpp:881-884):

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

`gPortsOrch->allPortsReady()` が `false` の間は `doTask` 全体が即 `return` する。
PORT / VLAN / LAG などの物理ポート初期化（PortsOrch による APPL_DB `PORT_TABLE` / `VLAN_TABLE` の処理）が完了するまで、`NEIGH_TABLE` のいかなるエントリも処理されない。

- **順序制約**: PORT/VLAN の orchagent 初期化完了 → APPL_DB `NEIGH_TABLE` SET の順。
- evidence: `neighorch.cpp:881-884`

### 2. PORT 存在確認 — `getPort` ガード

`NeighOrch::doTask` SET_COMMAND ブランチ (neighorch.cpp:942-947):

```cpp
Port p;
if (!gPortsOrch->getPort(alias, p))
{
    SWSS_LOG_INFO("Port %s doesn't exist", alias.c_str());
    it++;
    continue;
}
```

neighbor の interface alias に対応する Port オブジェクトが PortsOrch に未登録の場合、エントリはキューに残り次サイクルで再試行する（`it++; continue`）。

- **順序制約**: 対象インターフェイス (`Ethernet*` / `Vlan*` / `PortChannel*`) の PORT/VLAN/LAG エントリ確立 → NEIGH_TABLE SET の順。
- evidence: `neighorch.cpp:942-947`

### 3. INTERFACE (RIF) 先行必須 — `m_rif_id` ガード

`NeighOrch::doTask` SET_COMMAND ブランチ (neighorch.cpp:949-953):

```cpp
if (!p.m_rif_id)
{
    SWSS_LOG_INFO("Router interface doesn't exist on %s", alias.c_str());
    it++;
    continue;
}
```

Port が存在しても Router Interface (RIF) が未作成の場合は同様に再試行待ちになる。
RIF は `IntfsOrch` が APPL_DB `INTF_TABLE` エントリを処理することで SAI に作成される。

- **順序制約**: `INTF_TABLE|<alias>` エントリ確立（IntfsOrch による RIF 作成）→ NEIGH_TABLE SET の順。
- evidence: `neighorch.cpp:949-953`

### 4. `addNeighbor` 内の RIF 再確認 — `getRouterIntfsId` ガード

`NeighOrch::addNeighbor` (neighorch.cpp:1204-1209):

```cpp
sai_object_id_t rif_id = m_intfsOrch->getRouterIntfsId(alias);
if (rif_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get rif_id for %s", alias.c_str());
    return false;
}
```

`doTask` の RIF チェックを通過しても、`addNeighbor` 内でも RIF ID を再取得する。`SAI_NULL_OBJECT_ID` の場合は `false` を返し、エントリはキューに残って再試行される。

- evidence: `neighorch.cpp:1204-1209`

### 5. SAI `sai_neighbor_entry` 作成順 — ARP/ND 解決後に neighbor_entry を作成

`NeighOrch::addNeighbor` (neighorch.cpp:1211-1221):

```cpp
sai_neighbor_entry_t neighbor_entry;
neighbor_entry.rif_id = rif_id;
neighbor_entry.switch_id = gSwitchId;
copy(neighbor_entry.ip_address, ip_address);

sai_attribute_t neighbor_attr;
neighbor_attr.id = SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS;
memcpy(neighbor_attr.value.mac, macAddress.getMac(), 6);
neighbor_attrs.push_back(neighbor_attr);
```

`sai_neighbor_entry_t` は `rif_id`（RIF 先行必須）と解決済み MAC アドレスを組み合わせて構築される。
MAC アドレスが未解決（ゼロ MAC）の場合は APPL_DB の `NEIGH_RESOLVE_TABLE` 経由で ARP/ND resolution を要求し（neighorch.cpp:974/resolveNeighborEntry）、MAC が確定した後に再度 NEIGH_TABLE に SET が来て `addNeighbor` が呼ばれる。

- **順序制約**: ARP/NDP 解決完了（`neighsyncd` が MAC 付き NEIGH_TABLE を書き込む）→ `sai_neighbor_api->create_neighbor_entry` の順。
- evidence: `neighorch.cpp:1211-1334`

### 6. SAI `create_neighbor_entry` → `create_next_hop` の順序

`NeighOrch::addNeighbor` (neighorch.cpp:1333-1370):

```cpp
status = sai_neighbor_api->create_neighbor_entry(&neighbor_entry, ...);
// ... error check ...
if (!addNextHop(ctx))
{
    status = sai_neighbor_api->remove_neighbor_entry(&neighbor_entry);
    // rollback
}
```

SAI への書き込みは必ず `create_neighbor_entry` → `create_next_hop` の順で行われる。
`addNextHop` が失敗した場合、既に作成した `neighbor_entry` をロールバック削除した上で `false` を返す（アトミック性の確保）。

バルク処理パス (`bulk_op=true`) では `gNeighBulker.create_entry` と `gNextHopBulker.create_entry` をキューイングし、`drain()` で一括コミットする。

- **順序制約**: `sai_neighbor_api->create_neighbor_entry` → `sai_next_hop_api->create_next_hop` の順（違反時はロールバック）。
- evidence: `neighorch.cpp:1333-1390`

### 7. VLAN 間重複 neighbor の削除優先

`NeighOrch::addNeighbor` (neighorch.cpp:1263-1307):

```cpp
for (auto vlan_port: vlan_ports)
{
    if (vlan_port == alias) { continue; }
    NeighborEntry temp_entry = { ip_address, vlan_port };
    if (m_syncdNeighbors.find(temp_entry) != m_syncdNeighbors.end())
    {
        // Neighbor already exists on another VLAN. If they belong to the same VRF, delete the old neighbor
        if (existing_vlan.m_vr_id == new_vlan.m_vr_id)
        {
            if (!removeNeighbor(removeContext)) { return false; }
        }
    }
}
```

同一 IP の neighbor が別 VLAN に既存する場合（同じ VRF 内）、新規追加の前に旧 neighbor を先に削除する。
この削除処理が失敗した場合は `addNeighbor` 自体が `false` を返し、エントリは再試行待ちになる。

- **順序制約**: VLAN 間 neighbor 移動時は旧 VLAN での DEL → 新 VLAN での SET の順（同一 VRF 内でのみ自動処理）。
- evidence: `neighorch.cpp:1263-1307`

### 8. CONFIG_DB NEIGH → Netlink → APPL_DB NEIGH_TABLE の経路分離

CONFIG_DB の `NEIGH` テーブル（スタティック neighbor）は `nbrmgrd` が処理し、Netlink `RTM_NEWNEIGH` でカーネルの neighbor テーブルを直接操作する。orchagent (`NeighOrch`) は **APPL_DB の `NEIGH_TABLE`** を処理する別経路であり、両者は独立している。

- CONFIG_DB `NEIGH` → `nbrmgrd` → カーネル neighbor テーブル（SAI/orchagent 経由なし）
- APPL_DB `NEIGH_TABLE` → `neighorch` → SAI → ASIC

`neighsyncd` が カーネルの neighbor イベント (Netlink `RTM_NEWNEIGH`) を購読し、APPL_DB `NEIGH_TABLE` へ書き込むことで SAI プログラミング経路と繋がる。

- **順序制約**: CONFIG_DB `NEIGH` 設定（nbrmgrd 処理）はカーネルへの直接反映であり、SAI neighbor 作成順序とは無関係。ASIC への neighbor プログラムには `neighsyncd` → APPL_DB → `neighorch` の経路が必要。
- evidence: `neighorch.cpp:244-248`（runtime-trace セクション段階 4 も参照）

## 順序依存サマリ

| # | 依存関係 | 方向 | 対象パス | 違反時の挙動 |
|---|----------|------|---------|------------|
| 1 | `allPortsReady()` — PORT/VLAN 初期化完了 | 強制先行 | APPL_DB NEIGH_TABLE 全処理 | `doTask` 全体が即 `return`（次サイクル再試行） |
| 2 | 対象インターフェイス PORT 存在 | 強制先行 | SET_COMMAND ハンドラ | `it++; continue`（再試行待ち） |
| 3 | RIF (Router Interface) 存在 — `m_rif_id` | 強制先行 | SET_COMMAND ハンドラ | `it++; continue`（再試行待ち） |
| 4 | `getRouterIntfsId` で RIF 再確認 | 強制先行 | `addNeighbor` 内 | `return false`（再試行待ち） |
| 5 | ARP/ND 解決完了（MAC 確定）| 強制先行 | `sai_neighbor_entry` 作成 | MAC 未解決時は NEIGH_RESOLVE_TABLE 経由で再解決を要求 |
| 6 | `create_neighbor_entry` → `create_next_hop` | SAI 内部順序 | SAI プログラミング | NH 作成失敗時は neighbor_entry をロールバック削除 |
| 7 | 旧 VLAN DEL → 新 VLAN SET | 自動処理（同 VRF 内） | VLAN 間 neighbor 移動 | 旧エントリ削除失敗時は `return false`（再試行） |
| 8 | CONFIG_DB NEIGH と APPL_DB NEIGH_TABLE は独立 | 経路分離 | nbrmgrd vs neighorch | SAI 反映には APPL_DB 経路 (neighsyncd) が必要 |
