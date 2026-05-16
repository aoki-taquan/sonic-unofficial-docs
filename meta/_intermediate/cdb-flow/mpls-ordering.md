# mpls ordering scan (Phase B intermediate)

対象: `docs/reference/config-db/appl-mpls-route.md` (APPL_DB `LABEL_ROUTE_TABLE`)
ソース走査:
- `sonic-swss/orchagent/mplsrouteorch.cpp` (`RouteOrch::doLabelTask` / `addLabelRoute` / `addLabelRoutePost` / `addTempLabelRoute` / `removeLabelRoute*`)
- `sonic-swss/orchagent/routeorch.cpp` (bulker / PortsOrch 共有ガード)
- `sonic-swss/orchagent/nhgorch.cpp` (MPLS NH `isLabeled()` 分岐 / `NextHopGroupMember::createSaiObject`)

コミュニティ master 限定。

---

## 1. NEIGHBOR / NEXTHOP 先行条件

### 1-a. single NH — NeighOrch 解決待ち

```cpp
// mplsrouteorch.cpp:514-540 (addLabelRoute, single NH path)
if (m_neighOrch->hasNextHop(nexthop))
{
    next_hop_id = m_neighOrch->getNextHopId(nexthop);
}
else if (nexthop.isMplsNextHop() && m_neighOrch->isNeighborResolved(nexthop))
{
    NeighborContext ctx = NeighborContext(nexthop);
    if (m_neighOrch->addNextHop(ctx))
        next_hop_id = m_neighOrch->getNextHopId(nexthop);
    else
        return false;
}
else
{
    m_neighOrch->resolveNeighbor(nexthop);   // ARP/ND キック
    return false;                            // m_toSync 残置 → retry
}
```

`NEIGH_TABLE` / `m_syncdNextHops` 未確立のうちは `resolveNeighbor` を発火して `return false` で残置。
MPLS NH (`push<N>`/`swap<N>`) は **基底 IP neighbor が `isNeighborResolved` == true** になってから
NeighOrch 側 `addNextHop(ctx)` で初めて作成される（nhgorch.cpp:563-570 も同様）。

**順序依存**: `NEIGH_TABLE|<gw-ip>` の確立 → `hasNextHop(nexthop)` 成立 → `inseg_entry` 作成

### 1-b. ECMP — addTempLabelRoute による部分縮退

```cpp
// mplsrouteorch.cpp:547-583 (addLabelRoute, ECMP path)
for (auto it_nh = nextHops.getNextHops().begin(); ...)
{
    if (!m_neighOrch->hasNextHop(nextHop))
    {
        m_neighOrch->resolveNeighbor(nextHop);
    }
}
addTempLabelRoute(ctx, nextHops);   // 解決済み NH のサブセット inseg を一時 install
return false;                       // 元 ECMP は m_toSync 残置
```

```cpp
// mplsrouteorch.cpp:420-457 (addTempLabelRoute)
// isNeighborResolved(*it) でフィルタ → 解決済み単独 NH をランダム選択 → addLabelRoute 呼出
```

全 NH 解決後の次サイクルで本来の ECMP NHG に置換。1 個以上解決済みなら部分縮退で疎通は維持される。

**順序依存（縮退あり）**: 全 NH の `NEIGH_TABLE` 解決が本来 ECMP 成立の前提。

### 1-c. nhgorch MPLS NH 遅延作成

```cpp
// nhgorch.cpp:563-570 (NextHopGroupMember::createSaiObject)
else if (isLabeled() && gNeighOrch->isNeighborResolved(m_key))
{
    NeighborContext ctx = NeighborContext(m_key);
    if (gNeighOrch->addNextHop(ctx))
        nh_id = gNeighOrch->getNextHopId(m_key);
}
// else: resolveNeighbor + nh_id = SAI_NULL_OBJECT_ID → 上位 retry
```

`nexthop_group=<idx>` 経由の MPLS NH も IP neighbor 解決が先行必須。
MPLS NH の remove は `~NextHopGroupMember()` (nhgorch.cpp:677-682) が `removeMplsNextHop()` で行う。

---

## 2. ROUTE_TABLE 書込み順序 — doLabelTask 内処理フロー

`RouteOrch::doLabelTask` (`mplsrouteorch.cpp:34-417`) は以下の固定順で処理する:

1. **resync ハンドリング** (L63-95): `key == "resync"` の SET で `m_syncdLabelRoutes` 全件を
   `DEL_COMMAND` として self-enqueue し `m_resync=true`。以降の受信 op は `it++` 残置で待機。
2. **SET / DEL ループ** (L100-330): `addLabelRoute` / `removeLabelRoute` は
   `gLabelRouteBulker.create_entry()` / `set_entry_attribute()` / `remove_entry()` で bulker
   に積むのみで ASIC 反映なし。正常パス末尾も `return false` (→ 項 4)。
3. **NHG 上限近傍での早期 break** (L313-316):
   ```cpp
   if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount &&
       gLabelRouteBulker.removing_entries_count() > 0)
   {
       break;
   }
   ```
   SET ループを途中で抜けて bulker flush へ進み、NHG 解放を促す。
4. **`gLabelRouteBulker.flush()`** (L335): SET / DEL を一括 ASIC 反映。
5. **post-process ループ** (L340-406): `addLabelRoutePost` / `removeLabelRoutePost` で
   `m_syncdLabelRoutes` 更新と CRM (`CRM_MPLS_INSEG`) 反映。失敗時は `it_prev++` で再評価。
6. **NHG ref-count 整理** (L408-415): `m_bulkNhgReducedRefCnt` 巡回で参照数 0 の NHG を remove。

**タイミング依存**: 同一 doLabelTask バッチ内の SET/DEL 処理順序は上記で固定。
ConsumerStateTable 側で同一 key の SET/DEL は最後の op に集約される。

---

## 3. SAI inseg_entry / next_hop 作成順序

### 3-a. SAI 操作の順序

```
addLabelRoute()  → gLabelRouteBulker.create_entry() / set_entry_attribute()  [ASIC 未反映]
                   ↓
gLabelRouteBulker.flush()                                                      [ASIC 一括反映]
                   ↓
addLabelRoutePost() → m_syncdLabelRoutes 更新 + CRM incCrmResUsedCounter()    [確定]
```

`addLabelRoute` の正常パス末尾 (L664) は `return false` で残置のまま bulker flush を待つ。
確定 (`m_toSync.erase`) は `addLabelRoutePost` が `m_syncdLabelRoutes` に反映してから。

### 3-b. SAI INSEG ENTRY 属性の設定順 (`addLabelRoutePost`)

新規作成時 (`gLabelRouteBulker.bulk_entry_pending_removal` が偽、かつ未 sync):

```cpp
// mplsrouteorch.cpp:609-627
vector<sai_attribute_t> inseg_attrs;
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_PACKET_ACTION;   // DROP or FORWARD
inseg_attrs.push_back(inseg_attr);
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID;     // next_hop / nhg OID
inseg_attrs.push_back(inseg_attr);
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_NUM_OF_POP;       // mpls_pop 値
inseg_attrs.push_back(inseg_attr);
gLabelRouteBulker.create_entry(...)
```

既存エントリ更新時: `PACKET_ACTION` set → `NEXT_HOP_ID` set の順 (L640-661)。

### 3-c. MPLS NH (next_hop) と inseg_entry の依存

`next_hop_id` (SAI OID) が `SAI_NULL_OBJECT_ID` のうちは `addLabelRoute` が `return false`。
SAI `next_hop` object は NeighOrch 側 `addNextHop(ctx)` が create し、その後 RouteOrch / NhgOrch が
OID を引いて `SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID` に渡す。

**SAI 順序**: `sai_neighbor_api->create_neighbor_entry` (NeighOrch) →
`sai_next_hop_api->create_next_hop` (NeighOrch `addNextHop`) →
`sai_mpls_api->create_inseg_entry` (RouteOrch bulker flush) →
`sai_mpls_api->set_inseg_entry_attribute` (post-process)

---

## 4. 先行条件のまとめ

| 順序関係 | 必須先行 | 不成立時の挙動 |
|---|---|---|
| intf NH | IntfsOrch RIF (`INTERFACE` 系) | `return false` 残置 |
| single NH | NeighOrch (`NEIGH_TABLE`) 解決 | `resolveNeighbor` + 残置 |
| MPLS NH (`push`/`swap`) | 基底 IP `NEIGH_TABLE` + NhgOrch `isLabeled` 分岐 | retry |
| ECMP (全 NH 解決) | 全 nexthop IP の NEIGH 解決 | `addTempLabelRoute` 縮退 + 残置 |
| `nexthop_group` 指定 | NhgOrch (`NEXTHOP_GROUP_TABLE|<idx>`) | `ERROR` + `++it` |
| NhgOrch 経由 NHG | PortsOrch readiness | `NhgOrch::doTask` 早期 return |
| 非デフォルト VRF label | VrfOrch (`CONFIG_DB:VRF`) | `it++` 残置 (fpmsyncd は通常書かない) |
| bulker 確定 | `gLabelRouteBulker.flush()` + post-process | 正常パスも 1 サイクル遅延 |
| ASIC NHG 上限 | NHG 解放 | bulker 早期 break + `addTempLabelRoute` |

---

## 5. 参照元

- `sonic-net/sonic-swss` `orchagent/mplsrouteorch.cpp` (L34-961, 特に L420-590, L589-665, L667-754)
- `sonic-net/sonic-swss` `orchagent/nhgorch.cpp` (L41-44, L544-590, L677-682, L782-786)
- `sonic-net/sonic-swss` `orchagent/routeorch.cpp` (L192, L313-316)
- 詳細証跡は `meta/_intermediate/cdb-flow/appl-mpls-route-ordering.md` を参照
