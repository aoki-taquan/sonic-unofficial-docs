# ROUTE_TABLE 失敗挙動調査 (Phase D)

## 調査対象ソース

- `orchagent/routeorch.cpp` SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/routesync.cpp` SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## doTask() — フィールド検証フェーズ

### 1. `nexthop_group` と `nexthop`/`ifname` の同時指定 (routeorch.cpp:810-814)

**トリガー**: `nexthop_group` フィールドに値があり、かつ `nexthop` (ips) または `ifname` (aliases) も非空。

```cpp
if (!nhg_index.empty() && (!ips.empty() || !aliases.empty()))
{
    SWSS_LOG_ERROR("Route %s has both nexthop_group and ips/aliases", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

**結果**: エントリを `m_toSync` から削除（再試行なし）。SAI 操作は行われない。APPL_STATE_DB にもエラーは書き込まれない（`publishRouteState` が呼ばれない）。

---

### 2. EVPN VNI フィールド不正 (routeorch.cpp:982-988)

**トリガー**: `router_mac` または `vni_label` フィールドの MAC / VNI 値が不正フォーマット。

```cpp
SWSS_LOG_ERROR("Skip route %s, it has an invalid router mac field %s", key.c_str(), remote_macs.c_str());
// or
SWSS_LOG_ERROR("Skip route %s, it has an invalid vni label field %s", key.c_str(), vni_labels.c_str());
it = consumer.m_toSync.erase(it);
continue;
```

**結果**: エントリを `m_toSync` から削除（再試行なし）。EVPN Type-5 経路は SAI に到達しない。

---

### 3. SRv6 エンドポイント数不一致 (routeorch.cpp:937-947)

**トリガー**: SRv6 経路で `segment` / `seg_src` / `srv6_vpn_sid` の要素数が一致しない。

```cpp
SWSS_LOG_ERROR("inconsistent number of endpoints and srv6 vpn sids.");
it = consumer.m_toSync.erase(it);
continue;
// or
SWSS_LOG_ERROR("inconsistent number of srv6_segv and srv6_srcs.");
it = consumer.m_toSync.erase(it);
continue;
```

**結果**: エントリを `m_toSync` から削除（再試行なし）。

---

## addRoutePre() / addRoute() — 依存オブジェクト未解決による後回し

### 4. VRF 未登録 (routeorch.cpp:711-713)

**トリガー**: key の VRF 名 (`Vrf-<name>`) が VRFOrch に未登録。

```cpp
if (!m_vrfOrch->isVRFexists(vrf_name))
{
    it++; continue;  // 後回し（エラーログなし）
}
```

**結果**: `it++` で後回し。`m_toSync` に残り、次の doTask() 呼び出し時に再試行。VRF が登録されれば自動回復。

---

### 5. NhgOrch 管理 NHG 未存在 (routeorch.cpp:2411-2415)

**トリガー**: `nexthop_group` フィールドの NHG インデックスが `gNhgOrch` にも `gCbfNhgOrch` にも存在しない。

```cpp
if (!gNhgOrch->hasNhg(ctx.nhg_index) && !gCbfNhgOrch->hasNhg(ctx.nhg_index))
{
    SWSS_LOG_INFO("Failed to get next hop group with index %s", ctx.nhg_index.c_str());
    return false;
}
```

**結果**: `addRoutePre` が `false` を返し後回し。`NEXTHOP_GROUP_TABLE` エントリが登録されれば自動回復。

---

### 6. NeighOrch 未解決 nexthop (routeorch.cpp:1963)

**トリガー**: IP nexthop の ARP/NDP が未解決（`isNeighborResolved()` が false）。

```cpp
if (!m_neighOrch->isNeighborResolved(*it))
    return false;
```

**結果**: `addNextHopGroup` が `false` を返し後回し。neighbor 解決後に自動回復。

---

### 7. RIF 未登録（インタフェース直結 nexthop）(routeorch.cpp:2083-2084)

**トリガー**: `isIntfNextHop()` が true の nexthop でインタフェース RIF が SAI に未登録。

```cpp
auto next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
if (next_hop_id == SAI_NULL_OBJECT_ID) { return false; }
```

**結果**: `addRoute` が `false` を返し後回し。`INTERFACE` テーブルへの IP 設定後に自動回復。

---

### 8. EVPN L3 VNI 未登録 (routeorch.cpp:872)

**トリガー**: `vni_label` フィールドを持つ EVPN 経路で、当該 VNI が L3 VNI として未登録。

```cpp
if (!m_vrfOrch->isL3VniVlan(vni))
    { it++; continue; }
```

**結果**: 後回し。VXLAN_TUNNEL_MAP / VRF L3 VNI 設定後に自動回復。

---

## addRoutePost() / removeRoutePost() — SAI Bulk 操作失敗

### 9. SAI create_route_entry 失敗 (routeorch.cpp:2512-2526)

**トリガー**: gRouteBulker の bulk SAI create に失敗。

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s", ...);
    if (ctx.nhg_index.empty() && nextHops.getSize() > 1)
        removeNextHopGroup(nextHops);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
        return parseHandleSaiStatusFailure(handle_status);
}
```

**結果**: NHG クリーンアップ後、`handleSaiCreateStatus` で retry / ignore / failure に振り分け。`SAI_STATUS_TABLE_FULL` 等は task_need_retry → 後回し。`SAI_STATUS_SUCCESS_WITH_MORE` 等は無視。致命的エラーは `task_failed` → エントリを `m_toSync` から削除。`publishRouteState` は `addRoute` / `addRoutePost` の完了後に呼ばれ、失敗ステータスを APPL_STATE_DB に書き込む。

---

### 10. SAI set_route_entry 失敗（更新時） (routeorch.cpp:2572-2588)

**トリガー**: 既存経路の nexthop 更新で bulk SAI set に失敗。`SAI_STATUS_ITEM_NOT_FOUND` は特別扱い。

```cpp
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    // 内部キャッシュから削除して再 create を試みる
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
SWSS_LOG_ERROR("Failed to set route %s with next hop(s) %s", ...);
task_process_status handle_status = handleSaiSetStatus(SAI_API_ROUTE, status);
```

**結果**: `SAI_STATUS_ITEM_NOT_FOUND` は内部キャッシュをクリアして次回 doTask() で create として再試行。その他の失敗は `handleSaiSetStatus` で振り分け。

---

### 11. SAI remove_route_entry 失敗 (routeorch.cpp:2872-2879)

**トリガー**: DEL 操作の bulk SAI remove に失敗。

```cpp
SWSS_LOG_ERROR("Failed to remove route prefix:%s\n", ipPrefix.to_string().c_str());
task_process_status handle_status = handleSaiRemoveStatus(SAI_API_ROUTE, status);
if (handle_status != task_success)
    return parseHandleSaiStatusFailure(handle_status);
```

**結果**: `handleSaiRemoveStatus` で振り分け。失敗時は m_syncdRoutes から削除されないため孤立エントリが残る可能性がある。

---

## fpmsyncd — APPL_DB 書き込み前の失敗

### 12. VRF ifindex 名前解決失敗 (routesync.cpp)

**トリガー**: netlink メッセージの RTA_TABLE ifindex から VRF デバイス名を取得できない。

```cpp
if (!getIfName(vrf_index, destipprefix, IFNAMSIZ))
{
    SWSS_LOG_ERROR("Fail to get the VRF name (ifindex %u)", vrf_index);
    return;
}
```

**結果**: 当該 RTM_NEWROUTE メッセージを破棄。APPL_DB に書き込まれない。再試行なし。

---

## 要約表

| 失敗種別 | 発生箇所 | 動作 | 自動回復 |
|---------|---------|------|---------|
| nexthop_group + ips 同時指定 | doTask() フィールド検証 | erase (再試行なし) | なし |
| EVPN VNI / MAC フィールド不正 | doTask() フィールド検証 | erase (再試行なし) | なし |
| SRv6 要素数不一致 | doTask() フィールド検証 | erase (再試行なし) | なし |
| VRF 未登録 | doTask() VRF 確認 | it++ 後回し | VRF 登録後に自動回復 |
| NhgOrch NHG 未存在 | addRoutePre() | false 後回し | NEXTHOP_GROUP_TABLE 登録後に自動回復 |
| NeighOrch 未解決 nexthop | addNextHopGroup() | false 後回し | neighbor 解決後に自動回復 |
| RIF 未登録 (intf nexthop) | addRoute() 単一 nexthop | false 後回し | INTERFACE 設定後に自動回復 |
| EVPN L3 VNI 未登録 | doTask() EVPN 確認 | it++ 後回し | VNI 登録後に自動回復 |
| SAI create 失敗 | addRoutePost() | handleSaiCreateStatus で振り分け | テーブル満杯なら後回し |
| SAI set 失敗 ITEM_NOT_FOUND | addRoutePost() | キャッシュ消去→次回 create | 自動 |
| SAI set / remove 失敗 (他) | addRoutePost() / removeRoutePost() | handleSai*Status で振り分け | SAI 側復旧次第 |
| VRF ifindex 解決失敗 | fpmsyncd routesync.cpp | メッセージ破棄 | なし |
