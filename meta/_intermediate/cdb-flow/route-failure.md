# ROUTE_TABLE (APPL_DB) 失敗・retry 分岐 (Task F Phase D 中間メモ)

ターゲットページ: `docs/reference/config-db/route.md`

ソース (sonic-swss @ `4305596156d70e9797e8a881b3d19b46de0bce0d`):
- `orchagent/routeorch.cpp`

## 1. NEXTHOP 未解決 → retry

`routeorch.cpp` L2086–2090 (単一 NH・インタフェース直結):

```cpp
next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
/* rif is not created yet */
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s", ...);
    return false;
}
```

RIF (Router Interface) が未作成の場合 `addRoutePre` が `return false` → `doTask` は `it++` でエントリを据え置き、次サイクルで再試行 (retry)。

L2094–2109 (単一 NH・IP neighbor 未解決):

```cpp
if (m_neighOrch->hasNextHop(nexthop))
{
    ...
    if (m_neighOrch->isNextHopFlagSet(nexthop, NHFLAGS_IFDOWN))
    {
        SWSS_LOG_INFO("Interface down for NH %s, skip this Route for programming", ...);
        return false;
    }
}
```

- `hasNextHop()` が false → `resolveNeighbor(nexthop)` で ARP/NDP probe をキックして `return false` → retry。
- `NHFLAGS_IFDOWN` (リンクダウン中の nexthop) → `return false` → retry。ポートが UP 復旧後に再処理される。

L2197–2240 (ECMP NHG 経路・部分的 NH 未解決):

各 nexthop を走査し `hasNextHop` が false の場合 `resolveNeighbor` をキック。解決済み NH のみで NHG を構成し、それでも 0 になる場合は `addTempRoute` で解決済み 1-NH の仮経路を SAI に投入して `return false` → 元の ECMP 経路は retry。

## 2. SAI bulk 失敗

`routeorch.cpp` L2301–2307 (`gRouteBulker.create_entry()` 即時 ITEM_ALREADY_EXISTS):

```cpp
sai_status_t status = gRouteBulker.create_entry(...);
if (status == SAI_STATUS_ITEM_ALREADY_EXISTS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s: already exists in bulker",
            ipPrefix.to_string().c_str(), nextHops.to_string().c_str());
    return false;
}
```

bulker 内に同一 prefix のエントリが既に存在する場合、bulk flush 前にエラーを出して `return false`。

L2388–2392 (`addRoutePost` 入口):

```cpp
if (object_statuses.empty())
{
    // Something went wrong before router bulker, will retry
    return false;
}
```

bulk flush 前に pre フェーズで早期 return した場合 `object_statuses` が空になる。post フェーズはこれを検出して silent retry。

L2509–2526 (bulk flush 後の個別 status チェック):

```cpp
sai_status_t status = *it_status++;
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s",
            ipPrefix.to_string().c_str(), nextHops.to_string().c_str());
    ...
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`handleSaiCreateStatus` の返値:
- `task_need_retry` → `parseHandleSaiStatusFailure` が false を返す → doTask が `it++` で **retry**。
- `task_failed` / `task_invalid_entry` → erase して **ハード失敗**。

L2572–2589 (`SAI_STATUS_ITEM_NOT_FOUND` 専用パス):

```cpp
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    // remove the entry from the cache and retry route creation
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
```

orchagent 内部キャッシュに経路があるが SAI 側で既に消えている場合 (dualtor の tunnel route 消去が典型)。キャッシュから削除し、次回は「新規 create」として処理させる (自己修復 retry)。

L2816–2821 (`removeRoutePost` 入口):

```cpp
if (object_statuses.empty())
{
    // Something went wrong before router bulker, will retry
    return false;
}
```

DEL パスでも同様に pre フェーズ異常を post フェーズで検出して retry。

## 3. unsupported prefix → drop / skip

`routeorch.cpp` L807–812 (`nexthop_group` と `nexthop`/`ifname` 同時指定):

```cpp
SWSS_LOG_ERROR("Route %s has both nexthop_group and ips/aliases", key.c_str());
// erases the entry
```

フィールド整合性違反。**ハード失敗 (erase)** — SAI には投入されない。

L858–860 (`ifname` フィールドが空の unicast 経路):

```cpp
SWSS_LOG_WARN("Skip the route %s, for it has an empty ifname field.", key.c_str());
// erases
```

nexthop も ifname も空で非 blackhole / 非 srv6 → **ハード失敗 (erase)**。

L873–875 (EVPN 経路が非 L3 VNI):

```cpp
SWSS_LOG_WARN("Route %s is received on non L3 VNI %s", key.c_str(), vni_str.c_str());
// it++ (retry)
```

L3 VNI が後から登録されれば成功するため **retry**。

L980–988 (EVPN: `router_mac` または `vni_label` フィールド数の不整合):

```cpp
SWSS_LOG_ERROR("Skip route %s, it has an invalid router mac field %s", ...);
SWSS_LOG_ERROR("Skip route %s, it has an invalid vni label field %s", ...);
// erases
```

フィールド数不一致 → **ハード失敗 (erase)**。

L2074–2080 (static inband port 向けホストルート):

```cpp
if (gPortsOrch->isInbandPort(nexthop.alias))
{
    // skip: ASIC adds the same full mask route automatically
    return true;
}
```

SAI が静的ネイバー作成時に自動でホストルートを追加するため、明示的 SAI プログラミング不要として **成功扱いでスキップ**。

L2398–2400 (VRF が syncd routes に未存在):

```cpp
SWSS_LOG_INFO("VRF 0x%" PRIx64 " doesn't exist in syncd routes for route %s, will retry later", ...);
return false;
```

VRF オブジェクト ID は存在するが orchagent 内部 `m_syncdRoutes` への登録が完了していない過渡状態 → **retry**。

## 4. 失敗カテゴリ一覧表

| 失敗カテゴリ | 検出箇所 (routeorch.cpp) | syslog レベル / メッセージ | 振る舞い |
|------------|------------------------|------------------------|---------|
| RIF 未作成 (intf NH) | L2086 | INFO `Failed to get next hop ...` | retry |
| IFDOWN フラグ立ち | L2108 | INFO `Interface down for NH ...` | retry |
| IP neighbor 未解決 | L2151 / L2219 | INFO `resolving neighbor` | ARP/NDP probe + retry |
| VRF 未 syncd | L2398 | INFO `doesn't exist in syncd routes ... will retry later` | retry |
| NHG ref 不在 (nhg_index) | L2052 | INFO `Next hop group key ... does not exist` | retry |
| Context ID 未作成 (SRv6) | L2057 | INFO `Context ID ... move task entry to RetryCache` | RetryCache 保留 |
| SAI bulk ITEM_ALREADY_EXISTS | L2302 | ERROR `already exists in bulker` | return false (再キューなし) |
| SAI bulk flush 後失敗 | L2514 | ERROR `Failed to create route ...` | handleSaiCreateStatus → retry or erase |
| SAI ITEM_NOT_FOUND (dualtor) | L2575 | ERROR `Failed to set route ...` + キャッシュ消去 | 自己修復 retry |
| object_statuses 空 (pre 異常) | L2388 / L2817 | (なし) | silent retry |
| nexthop_group + ips 同時指定 | L807 | ERROR `has both nexthop_group and ips/aliases` | ハード失敗 (erase) |
| ifname 空 (unicast) | L858 | WARN `empty ifname field` | ハード失敗 (erase) |
| 非 L3 VNI | L873 | WARN `received on non L3 VNI` | retry |
| EVPN フィールド数不整合 | L980/L988 | ERROR `invalid router mac/vni label field` | ハード失敗 (erase) |
| inband port ホストルート | L2074 | (なし) | 意図的スキップ (成功) |
