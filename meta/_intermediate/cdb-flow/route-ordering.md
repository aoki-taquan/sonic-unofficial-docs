# ROUTE_TABLE (APPL_DB) — Phase B 書込み順依存スキャンノート

対象テーブル: `ROUTE_TABLE` (APPL_DB)
Consumer: `orchagent RouteOrch` (`sonic-swss/orchagent/routeorch.cpp`)
スキャン範囲: L706-717 (VRF チェック), L838-884 (NHG/overlay チェック), L2408-2460 (addRoutePre), L1494-1516 (addNextHopGroup), L1102-1108 (DEL path)

---

## 検出した順序依存・タイミング依存

### 1. VRF 経路: `VRF` エントリが先行必須

`routeorch.cpp:706-714` — key が `Vrf` プレフィックスで始まる場合（例: `Vrf-RED:192.168.1.0/24`）、`m_vrfOrch->isVRFexists(vrf_name)` を検査し、VRF が存在しなければ `it++; continue` で処理を後回しにする。VRF SAI オブジェクトが生成されるまで経路の SAI プログラミングは行われない。

```cpp
// routeorch.cpp L711-714
if (!m_vrfOrch->isVRFexists(vrf_name))
{
    it++;
    continue;
}
```

**ADD 順序**: `CONFIG_DB|VRF|<name>` → VRFOrch が `APPL_DB|VRF_TABLE|<name>` を SAI に反映 → `APPL_DB|ROUTE_TABLE|<vrf_name>:<prefix>` を書き込む。

**DEL 順序**: `ROUTE_TABLE|<vrf_name>:*` を全 DEL → その後 VRF を DEL。VRF を先に DEL すると VRFOrch がリファレンスカウントを持っている限り DEL を遅延させるが、APPL_DB 上の ROUTE_TABLE エントリは孤立したまま残る。

evidence: `routeorch.cpp:706-716`

---

### 2. `nexthop_group` 参照: NhgOrch エントリが先行必須

`routeorch.cpp:2409-2415` — `nexthop_group` フィールドが指定されている場合（kernel NHG ID ではなく NhgOrch 管理の NHG インデックス文字列）、`gNhgOrch->hasNhg(ctx.nhg_index)` および `gCbfNhgOrch->hasNhg(ctx.nhg_index)` を両方確認し、いずれにも存在しなければ `return false`（後回し）。

```cpp
// routeorch.cpp L2411-2414
if (!gNhgOrch->hasNhg(ctx.nhg_index) && !gCbfNhgOrch->hasNhg(ctx.nhg_index))
{
    SWSS_LOG_INFO("Failed to get next hop group with index %s", ctx.nhg_index.c_str());
    return false;
}
```

**ADD 順序**: `NEXTHOP_GROUP_TABLE` エントリを NhgOrch が SAI に登録完了 → その後 `ROUTE_TABLE` に `nexthop_group: <index>` を書き込む。

**DEL 順序**: `ROUTE_TABLE` の DEL（参照解除）を先に行い、NhgOrch のリファレンスカウントが 0 になってから `NEXTHOP_GROUP_TABLE` を DEL する。

evidence: `routeorch.cpp:2408-2415`

---

### 3. 通常 nexthop 経路: NeighOrch が先行必須（マルチホップの場合）

`routeorch.cpp:1499-1516` (addNextHopGroup), `routeorch.cpp:2440-2446` (addRoute 単一 NH 非インタフェース) — nexthop が通常 IP アドレスの場合（インタフェース直結ではない）、`m_neighOrch->hasNextHop(it)` を確認し、存在しなければ `return false`（後回し）。

```cpp
// routeorch.cpp L2440-2445
if (!m_neighOrch->hasNextHop(nexthop))
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s",
            nextHops.to_string().c_str(), ipPrefix.to_string().c_str());
    return false;
}
```

**ADD 順序**: ARP/NDP 解決 → NeighOrch が nexthop を登録 → `ROUTE_TABLE` 書き込み。FRR (zebra) は通常ネイバー解決後に ROUTE_TABLE へ書き込む（zebra 内部で順序を担保）ため、fpmsyncd 経由の通常フローでは問題にならないが、直接 APPL_DB を操作する場合は注意。

evidence: `routeorch.cpp:1494-1516`, `routeorch.cpp:2423-2446`

---

### 4. EVPN overlay 経路: L3 VNI が先行必須

`routeorch.cpp:870-884` — `vni_label` フィールドが存在する場合（EVPN Type-5 経路）、各 VNI に対して `m_vrfOrch->isL3VniVlan(vni)` を確認。L3 VNI として登録されていない VNI を持つ経路は `it++; continue` で後回し。

```cpp
// routeorch.cpp L872-884
if (!m_vrfOrch->isL3VniVlan(vni))
{
    SWSS_LOG_WARN("Route %s is received on non L3 VNI %s", key.c_str(), vni_str.c_str());
    l3Vni = false;
    break;
}
if (!l3Vni)
{
    it++;
    continue;
}
```

**ADD 順序**: `VXLAN_TUNNEL_MAP` による L3 VNI 設定 → VrfOrch が L3 VNI 登録 → `ROUTE_TABLE` に `vni_label` を含む EVPN 経路を書き込む。

evidence: `routeorch.cpp:869-884`

---

### 5. インタフェース経路 (subnet route): IntfsOrch が先行必須

`routeorch.cpp:2427-2436` — nexthop が `isIntfNextHop()`（インタフェース名のみで IP なし）の場合、`m_intfsOrch->getRouterIntfsId(nexthop.alias)` が `SAI_NULL_OBJECT_ID` ならば `return false`。RIF（Router Interface）が SAI に登録されるまで経路プログラミングを保留。

```cpp
// routeorch.cpp L2429-2435
auto next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s", ...);
    return false;
}
```

**ADD 順序**: `INTERFACE` / `PORTCHANNEL_INTERFACE` テーブルに IP アドレス設定 → IntfsOrch が RIF を SAI に登録 → `ROUTE_TABLE` に直結サブネット経路を書き込む。

evidence: `routeorch.cpp:2427-2436`

---

### 6. DEL: ROUTE_TABLE DEL → 参照先オブジェクト DEL の順が必須

DEL パスは `routeorch.cpp:1102-1108` で `removeRoute(ctx)` を呼ぶ。`removeRoute` は SAI から route entry を削除し、nexthop group のリファレンスカウントを減算する。

- **NHG を先に DEL すると**: NhgOrch がリファレンスカウントを持つため DEL を遅延させるが、SAI レベルの不整合が発生しうる。
- **VRF を先に DEL すると**: VRFOrch は参照中 VRF の DEL を遅延させるが、ROUTE_TABLE エントリが取り残される。

**推奨 DEL 順序**:
```
ROUTE_TABLE|<prefix> DEL
  → NEXTHOP_GROUP_TABLE DEL（ref=0 後）
  → VRF DEL
```

evidence: `routeorch.cpp:1102-1108`, `routeorch.cpp:2409-2415`, `routeorch.cpp:706-716`

---

## 7. SAI bulk batch — gRouteBulker によるバッチ SAI 発行

`RouteOrch` は SAI route エントリ操作を 1 件ずつ発行せず、`EntityBulker<sai_route_api_t> gRouteBulker(sai_route_api, gMaxBulkSize)` にキューイングしてバッチで送る。

**コード証跡**:
- `routeorch.cpp:41` — `gRouteBulker(sai_route_api, gMaxBulkSize)` コンストラクタ
- `routeorch.cpp:2301` — `gRouteBulker.create_entry()` (ADD)
- `routeorch.cpp:2791,2797,2802` — `gRouteBulker.set_entry_attribute()` / `remove_entry()` (DEL)
- `routeorch.cpp:1117` — `gRouteBulker.flush()` (バッチ発行)
- `routeorch.cpp:1094-1100` — NHG 枯渇時の中間 flush

**処理シーケンス**:
1. `m_toSync` 全エントリをループ → `addRoute` / `removeRoute` が bulker にキューイング（SAI 未発行）
2. ループ後 `gRouteBulker.flush()` → `sai_route_bulk_create` / `sai_route_bulk_remove` 一括発行
3. `addRoutePost` / `removeRoutePost` で SAI ステータス確認、失敗は `m_toSync` に残留（リトライ）

**中間 flush 条件**: NHG 数が `m_maxNextHopGroupCount` に到達かつ bulker 内に削除待ちエントリがある場合、ループを中断して flush し NHG を回収してから再開（`routeorch.cpp:1094-1100`）。

**独立 bulker**: MPLS ラベル経路は `gLabelRouteBulker(sai_mpls_api, gMaxBulkSize)` で別バッチ管理（`routeorch.cpp:42`）。NHG メンバは `gNextHopGroupMemberBulker` で独立管理。

evidence: `routeorch.cpp:41-43`, `routeorch.cpp:1094-1120`, `routeorch.cpp:2277-2375`, `routeorch.cpp:2739-2810`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | VRF SAI 登録 → VRF 経路 (`Vrf<name>:<prefix>`) ADD | 強制先行（isVRFexists が false → `it++` 後回し） | VRF を先に作成してから経路を書き込む |
| 2 | NhgOrch NHG 登録 → `nexthop_group` 指定経路 ADD | 強制先行（hasNhg が false → `return false` 後回し） | NEXTHOP_GROUP_TABLE を先に作成 |
| 3 | NeighOrch nexthop 登録 → 通常 IP 経路 ADD | 強制先行（hasNextHop が false → `return false` 後回し） | ARP/NDP 解決後に経路を書き込む |
| 4 | L3 VNI 登録 → EVPN overlay 経路 (`vni_label` 付き) ADD | 強制先行（isL3VniVlan が false → `it++` 後回し） | VXLAN_TUNNEL_MAP / VRF 設定後に経路を書き込む |
| 5 | IntfsOrch RIF 登録 → インタフェース直結経路 ADD | 強制先行（getRouterIntfsId==NULL → `return false` 後回し） | INTERFACE テーブルに IP を設定後に経路を書き込む |
| 6 | ROUTE_TABLE DEL → NHG / VRF DEL | 推奨（参照解除なし DEL はリファレンスカウントが詰まる） | 経路 DEL 後にリファレンス先を DEL |
| 7 | SAI bulk batch: ループ内 queue → flush → post 確認 | 実装制約（flush 前は SAI 未発行、post 前はステータス不定） | NHG 枯渇時は中間 flush が自動発生 |
