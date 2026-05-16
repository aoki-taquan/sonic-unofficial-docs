# route-cross-refs — ROUTE_TABLE 暗黙参照 (Phase C)

ソース: `orchagent/routeorch.cpp`
SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

## 抽出した暗黙参照

### 1. NEIGHBOR (APPL_DB) — NeighOrch 経由

`RouteOrch` は nexthop の実体を直接保持せず、常に `m_neighOrch` 経由で参照する。

```cpp
// addNextHopGroup() — routeorch.cpp:1499-1510
if (m_neighOrch->hasNextHop(it))
{
    next_hop_id = m_neighOrch->getNextHopId(it);
    ...
}
else
{
    m_neighOrch->addNextHop(ctx);
    next_hop_id = m_neighOrch->getNextHopId(it);
}
```

```cpp
// addRoute() 単一 nexthop path — routeorch.cpp:2094-2119
if (m_neighOrch->hasNextHop(nexthop))
{
    next_hop_id = m_neighOrch->getNextHopId(nexthop);
    ...
}
else
{
    m_neighOrch->addNextHop(ctx);
    next_hop_id = m_neighOrch->getNextHopId(nexthop);
}
```

```cpp
// 参照カウント管理 — routeorch.cpp:1363-1386
m_neighOrch->increaseNextHopRefCount(nexthop);
// ... DEL 時:
m_neighOrch->decreaseNextHopRefCount(nexthop);
```

`isNeighborResolved()` で ARP/NDP 解決済みかも確認する:
```cpp
if (!m_neighOrch->isNeighborResolved(*it))
    return false;  // routeorch.cpp:1963
```

**含意**: IP nexthop を持つ経路は APPL_DB の `NEIGH_TABLE` エントリが解決済みでなければ SAI プログラミングが遅延する。

---

### 2. NEXTHOP_GROUP (APPL_DB) — NhgOrch / CbfNhgOrch 経由

`nexthop_group` フィールドに NHG インデックスが指定されると、`gNhgOrch` または `gCbfNhgOrch` の存在確認を行う。

```cpp
// addRoute() NhgOrch パス — routeorch.cpp:2411-2415
if (!gNhgOrch->hasNhg(ctx.nhg_index) && !gCbfNhgOrch->hasNhg(ctx.nhg_index))
{
    SWSS_LOG_INFO("Failed to get next hop group with index %s", ctx.nhg_index.c_str());
    return false;
}
```

```cpp
// doTask() 内 NHG 取得 — routeorch.cpp:1006-1015
const NhgBase& nh_group = getNhg(nhg_index);
nhg = nh_group.getNhgKey();
ctx.using_temp_nhg = nh_group.isTemp();
// 存在しなければ out_of_range 例外 → ++it; continue で後回し
```

`getNhg()` の内部実装 (routeorch.cpp:3133-3143):
```cpp
if (gNhgOrch->hasNhg(nhg_index))
    return gNhgOrch->getNhg(nhg_index);
if (gCbfNhgOrch->hasNhg(nhg_index))
    return gCbfNhgOrch->getNhg(nhg_index);
// 見つからなければ out_of_range
```

**含意**: `NEXTHOP_GROUP_TABLE` (APPL_DB) エントリが NhgOrch に登録される前に `nexthop_group` を指定した ROUTE_TABLE エントリを書いても SAI プログラミングは行われず後回しになる。

---

### 3. VRF (CONFIG_DB) — VRFOrch 経由

VRF プレフィックス (`Vrf`) を持つ経路は VRFOrch への登録確認が必須。

```cpp
// doTask() VRF 存在確認 — routeorch.cpp:706-716
if (!key.compare(0, strlen(VRF_PREFIX), VRF_PREFIX))
{
    vrf_name = key.substr(0, key.find(':'));
    if (!m_vrfOrch->isVRFexists(vrf_name))
    {
        it++; continue;  // VRF が未登録なら後回し
    }
    vrf_id = m_vrfOrch->getVRFid(vrf_name);
}
```

```cpp
// EVPN L3 VNI 確認 — routeorch.cpp:872
if (!m_vrfOrch->isL3VniVlan(vni))
    it++; continue;  // L3 VNI 未登録なら後回し
```

```cpp
// 参照カウント管理 — routeorch.cpp:2013
m_vrfOrch->increaseVrfRefCount(vrf_id);
```

**含意**: `CONFIG_DB:VRF|<name>` → VRFOrch が SAI VRF 登録 → `APPL_DB:ROUTE_TABLE|<vrf_name>:<prefix>` の順が必須。

---

### 4. MUX (MuxOrch) — gDirectory 経由

MuxOrch は Dual-ToR の Active/Standby 制御を担う。RouteOrch は NHG 構築時に mux tunnel nexthop を特別扱いする。

```cpp
// addNextHopGroup() — routeorch.cpp:1490-1524
MuxOrch* mux_orch = gDirectory.get<MuxOrch*>();
sai_object_id_t mux_tunnel_nh_id = mux_orch->getTunnelNextHopId();
bool has_mux_prefix_rt_nh = mux_orch->hasPrefixBasedMuxNexthop(next_hop_set);

if (next_hop_id != mux_tunnel_nh_id)
    // 通常 NHG メンバーとして追加
else if (has_mux_prefix_rt_nh)
    // prefix-based mux nexthop はトンネル NH を NHG に含めない
```

```cpp
// addRoute() ECMP mux 判定 — routeorch.cpp:2688-2723
else if (nextHops.getSize() > 1 && mux_orch->isMuxNexthops(nextHops) && ...)
{
    // mux multi-nexthop: muxOrch::updateRoute() に委譲
}
if (mux_orch->isMuxNexthops(nextHops))
{
    mux_orch->updateRoute(ipPrefix);  // Dual-ToR の経路状態を MuxOrch に通知
}
```

**含意**: Dual-ToR 環境で `MUX_CABLE` ポートを nexthop とする経路は、RouteOrch が SAI に書き込んだ後、MuxOrch::updateRoute() でさらに書き換えられる場合がある。MuxOrch が初期化済みでなければ `gDirectory.get<MuxOrch*>()` が失敗する。

---

## 参照テーブル一覧

| 暗黙参照先 | DB | テーブル / Orch | 参照方法 | 方向 |
|-----------|-----|----------------|---------|------|
| NEIGHBOR | APPL_DB | `NEIGH_TABLE` / NeighOrch | `m_neighOrch->hasNextHop()` / `getNextHopId()` | READ (依存) |
| NEXTHOP_GROUP | APPL_DB | `NEXTHOP_GROUP_TABLE` / NhgOrch | `gNhgOrch->hasNhg()` / `gCbfNhgOrch->hasNhg()` | READ (依存) |
| VRF | CONFIG_DB | `VRF` / VRFOrch | `m_vrfOrch->isVRFexists()` / `getVRFid()` | READ (依存) |
| MUX_CABLE | CONFIG_DB | `MUX_CABLE` / MuxOrch | `mux_orch->isMuxNexthops()` / `updateRoute()` | WRITE (通知) |
