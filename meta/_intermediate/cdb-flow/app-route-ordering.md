# app-route ordering scan (Phase B intermediate)

対象: `docs/reference/config-db/app-route.md` (APPL_DB `ROUTE_TABLE`)。
ソース: `sonic-swss/orchagent/routeorch.cpp`, `orchagent/nhgorch.cpp` (community master)。

## 検出した順序依存・タイミング依存

### 1. PortsOrch readiness ガード (NhgOrch のみ)

```cpp
// nhgorch.cpp:41-44
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

`NhgOrch::doTask` 冒頭で `allPortsReady()` が false なら即 return。`RouteOrch::doTask` には同等のガードはなく、`m_vrfOrch->isVRFexists` チェック (L711) が事実上の依存関門となる。

→ NHG 経路: PortsOrch 初期化完了が先行必須。

### 2. VRF 先行ガード (RouteOrch)

```cpp
// routeorch.cpp:706-715
if (!key.compare(0, strlen(VRF_PREFIX), VRF_PREFIX))
{
    size_t found = key.find(':');
    string vrf_name = key.substr(0, found);

    if (!m_vrfOrch->isVRFexists(vrf_name))
    {
        it++;
        continue;
    }
    vrf_id = m_vrfOrch->getVRFid(vrf_name);
    ip_prefix = IpPrefix(key.substr(found+1));
}
```

`ROUTE_TABLE|<vrf-name>:<prefix>` の VRF 名が `VrfOrch` に未登録の場合、ログなしで `it++` (m_toSync 残置) → 次サイクル再評価。VrfOrch が CONFIG_DB `VRF` を消化して `m_vrfOrch->isVRFexists` が真を返すまで毎ループ retry し続ける。

→ 順序依存: 非デフォルト VRF prefix の場合、`VRF` 登録が必須先行。

### 3. NHG 先行ガード (RouteOrch)

```cpp
// routeorch.cpp:1004-1015
try
{
    const NhgBase& nh_group = getNhg(nhg_index);
    nhg = nh_group.getNhgKey();
    ctx.using_temp_nhg = nh_group.isTemp();
}
catch (const std::out_of_range& e)
{
    SWSS_LOG_ERROR("Next hop group %s does not exist", nhg_index.c_str());
    ++it;
    continue;
}
```

`nexthop_group` フィールド指定時、NhgOrch の `m_syncdNextHopGroups` に当該 index が未登録なら ERROR ログ + `++it` で残置 → NhgOrch が `NEXTHOP_GROUP_TABLE` (APPL_DB) を消化するまで retry。

→ 順序依存: `nexthop_group=<idx>` 経路では NHG_TABLE entry が `ROUTE_TABLE` set より先行必須。

### 4. neighbor 先行 (single NH / ECMP)

single NH 経路:

```cpp
// routeorch.cpp:2149-2155
else
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s, resolving neighbor", ...);
    m_neighOrch->resolveNeighbor(nexthop);
    return false;
}
```

ECMP 経路:

```cpp
// routeorch.cpp:2194-2243
for(auto it = nextHops.getNextHops().begin(); ...)
{
    if(!m_neighOrch->hasNextHop(nextHop))
    {
        ...
        m_neighOrch->resolveNeighbor(nextHop);
    }
}
...
addTempRoute(ctx, nextHops);
return false;
```

NeighOrch の `m_syncdNextHops` 未登録時:
- single NH → `resolveNeighbor` (ARP/ND 送信) → `addRoute` false → `m_toSync` 残置
- ECMP → 未解決 NH ごとに `resolveNeighbor` を発火し、`addTempRoute` で**解決済み NH のみのサブセット一時ルート**を install。元 ECMP は残置

`NeighOrch::resolveNeighbor` が ARP/ND を投げて kernel/zebra → APPL_DB `NEIGH_TABLE` → NeighOrch に neighbor が登録された後、次サイクルで本ルートが成立する。

→ 順序依存: 各 nexthop IP の neighbor 解決が必須。未解決時は ECMP は縮退、single は完全保留。

### 5. RIF (router interface) 先行

```cpp
// routeorch.cpp:2083-2090
next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
/* rif is not created yet */
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s", ...);
    return false;
}
```

interface NH（directly-connected）で IntfsOrch が RIF を未作成の場合、`addRoute` false → 残置 → `INTF_TABLE` 消化後に成立。

→ 順序依存: directly-connected ルートは `INTF_TABLE` が `ROUTE_TABLE` より先行必須。

### 6. NhgOrch 内: 再帰メンバ NHG の先行

```cpp
// nhgorch.cpp:128-164
for (auto& nhgm : nhgv)
{
    const auto& nhgm_it = m_syncdNextHopGroups.find(nhgm);
    if (nhgm_it == m_syncdNextHopGroups.end())
    {
        SWSS_LOG_INFO("Member nexthop group %s in parent nhg %s not ready", ...);
        non_existent_member = true;
        continue;
    }
    ...
}
...
if (nhgs.empty())
{
    it++;
    continue;
}
```

再帰 NHG (`nexthop_group` フィールドを持つ NHG) で全メンバが未登録なら `it++` で残置。一部のみ存在する場合は存在するメンバだけで合成し処理を継続する（部分縮退）。

→ 順序依存: 再帰 NHG は子 NHG が先行必須（少なくとも 1 つは登録要）。

### 7. NHG 上限到達 → tempRoute サブセット install (SAI race)

```cpp
// routeorch.cpp:2237-2243
addTempRoute(ctx, nextHops);
return false;
```

`addNextHopGroup` が `m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount` で false を返した場合、元 ECMP は `m_toSync` 残置のまま **単一 NH のサブセット tempRoute** を ASIC に install。

```cpp
// routeorch.cpp:1094-1100
// If already exhaust the nexthop groups, and there are pending removing routes in bulker,
// flush the bulker and possibly collect some released nexthop groups
if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount &&
    gRouteBulker.removing_entries_count() > 0)
{
    break;
}
```

bulker 内に削除待ち NHG があれば doTask ループを break して flush を促す。

→ タイミング依存: NHG 上限近傍ではフル ECMP の install が遅延し、観測上は ECMP 縮退として現れる。

### 8. PIC `context_index` の RetryCache

```cpp
// routeorch.cpp:2055-2060
if (!ctx.context_index.empty() && !m_srv6Orch->contextIdExists(ctx.context_index))
{
    SWSS_LOG_INFO("Context ID %s does not exist, move task entry to RetryCache", ctx.context_index.c_str());
    ctx.retry_cst = make_constraint(RETRY_CST_PIC, ctx.context_index);
    return false;
}
```

```cpp
// routeorch.cpp:192
createRetryCache(APP_ROUTE_TABLE_NAME);
```

PIC `context_index` 未登録の場合、`RETRY_CST_PIC` 制約で **RetryCache に park**（`m_toSync` 残置 polling と異なり、明示的 retry-cache 利用箇所）。Srv6Orch 側からの `notifyRetry(RETRY_CST_PIC+context_index)` で再 enqueue される。

→ 順序依存: SRv6 PIC 経路では `PIC_CONTEXT` が `ROUTE_TABLE` より先行必須。RetryCache park により無限ポーリングは回避。

### 9. SAI race: `SAI_STATUS_ITEM_NOT_FOUND` on set (DualToR)

```cpp
// routeorch.cpp:2572-2581
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    SWSS_LOG_ERROR("Failed to set route ... not found");
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
```

DualToR で tunnel route が削除された直後に learned route が同じ prefix を `set_route_entry_attribute` しようとして race。内部 cache を補正して次サイクルで create にフォールバック。

→ タイミング依存（SAI race）: 同一 prefix への DEL→SET 連続発生時の補正。

### 10. bulker 内 `SAI_STATUS_ITEM_ALREADY_EXISTS` (同一バッチ重複)

```cpp
// routeorch.cpp:2301-2307
sai_status_t status = gRouteBulker.create_entry(...);
if (status == SAI_STATUS_ITEM_ALREADY_EXISTS)
{
    SWSS_LOG_ERROR("Failed to create route ... already exists in bulker");
    return false;
}
```

同一 doTask 反復内で同 prefix を 2 回 create しようとした場合の防御。`m_toSync` 残置 → 次サイクルで bulker クリア後に再評価。

→ タイミング依存（バッチ内重複）: 通常運用では起きない。

## 影響範囲のまとめ

| 順序関係 | 必須先行 | 不成立時の挙動 |
|---|---|---|
| 非デフォルト VRF prefix | `VRF` (VrfOrch) | `it++` 残置 polling |
| `nexthop_group` 指定 | `NEXTHOP_GROUP_TABLE` (NhgOrch) | `++it` + ERROR ログ |
| directly-connected | `INTF_TABLE` (IntfsOrch RIF) | `addRoute` false 残置 |
| single NH | `NEIGH_TABLE` (NeighOrch) | `resolveNeighbor` → 残置 |
| ECMP | 全 NH の `NEIGH_TABLE` | tempRoute サブセット install + 残置 |
| 再帰 NHG | 子 NHG | 部分縮退 or `it++` |
| SRv6 PIC | `PIC_CONTEXT` (Srv6Orch) | RetryCache park |
| ASIC NHG 上限 | NHG 解放 | tempRoute install + bulker flush |

## 検出メソッド

grep targets:
- `routeorch.cpp`: `isVRFexists`, `getRouterIntfsId`, `hasNextHop`, `resolveNeighbor`, `getNhg`, `contextIdExists`, `addTempRoute`, `SAI_STATUS_ITEM_NOT_FOUND`, `SAI_STATUS_ITEM_ALREADY_EXISTS`, `RETRY_CST_PIC`
- `nhgorch.cpp`: `allPortsReady`, `m_syncdNextHopGroups.find`, `is_recursive`

`ERROR_TABLE` への書き込みは grep 結果なし。順序依存違反は基本的に `m_toSync` 残置 polling か明示的 RetryCache（PIC 限定）で吸収される。
