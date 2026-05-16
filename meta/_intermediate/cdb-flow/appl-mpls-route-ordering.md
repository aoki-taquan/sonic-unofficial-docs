# appl-mpls-route ordering scan (Phase B intermediate)

対象: `docs/reference/config-db/appl-mpls-route.md` (APPL_DB `LABEL_ROUTE_TABLE`)。
ソース: `sonic-swss/orchagent/mplsrouteorch.cpp` (`RouteOrch::doLabelTask` / `addLabelRoute` / `addLabelRoutePost`)、`orchagent/nhgorch.cpp` (MPLS NH `isLabeled()` 分岐)、補助で `orchagent/routeorch.cpp` (bulker/PortsOrch ガード共有)、`fpmsyncd/routesync.cpp::onLabelRouteMsg()` (warm reboot 連動)。コミュニティ master。

## 検出した順序依存・タイミング依存

### 1. PortsOrch readiness ガード (NhgOrch 経由のみ)

```cpp
// nhgorch.cpp:41-44 — NhgOrch::doTask 冒頭
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

`doLabelTask` 自身には `allPortsReady` 直接ガードはない。ただし `nexthop_group=<idx>` 経路は `NhgOrch` の `m_syncdNextHopGroups` 反映を必要とし、NhgOrch は PortsOrch readiness を満たすまで `doTask` を空 return する。単一 intf NH パスでも `m_intfsOrch->getRouterIntfsId(alias)` (`mplsrouteorch.cpp:503,707`) が `SAI_NULL_OBJECT_ID` なら `addLabelRoute` / `addLabelRoutePost` は `return false`。

→ 順序依存: `PORT` 初期化 → `INTERFACE` 系 RIF → `LABEL_ROUTE_TABLE`。

### 2. VRF 先行ガード (VRF-aware key)

```cpp
// mplsrouteorch.cpp:107-119
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
    label = to_uint<uint32_t>(key.substr(found+1));
}
```

`LABEL_ROUTE_TABLE|<vrf>:<label>` 形式で VrfOrch に未登録なら、ログなしで `it++` 残置。VrfOrch が `CONFIG_DB:VRF` を消化するまで毎ループ retry。

ただし現状の **fpmsyncd は非デフォルト VRF の MPLS ルートをそもそも書かない** (`routesync.cpp:2674-2681` で `SWSS_LOG_INFO("Unsupported Non-default VRF")` のみ)。
→ doLabelTask の VRF 残置パスはあくまで「外部から手書きで `LABEL_ROUTE_TABLE|Vrf...:` を書いた場合」のみ顕在化する。

### 3. NHG 先行ガード (`nexthop_group` フィールド指定)

```cpp
// mplsrouteorch.cpp:255-267
try
{
    const NhgBase& nh_group = getNhg(nhg_index);
    ctx.nhg = nh_group.getNhgKey();
    ctx.using_temp_nhg = nh_group.isTemp();
}
catch (const std::out_of_range& e)
{
    SWSS_LOG_ERROR("Next hop group %s does not exist", nhg_index.c_str());
    ++it;
    continue;
}
```

NhgOrch の `m_syncdNextHopGroups` 未登録 → `ERROR` + `++it` で残置 polling。NhgOrch が `NEXTHOP_GROUP_TABLE` を消化するまで retry。
NhgOrch は項 1 の `allPortsReady` ガードを併せ持つ → 連鎖的に PortsOrch 完了が前提。

`addLabelRoute` 内でも race を防ぐ二重チェックがあり、NHG が消失していれば `return false` で残置:

```cpp
// mplsrouteorch.cpp:481-491
try {
    const NhgBase& nhg = getNhg(ctx.nhg_index);
    ...
}
catch (const std::out_of_range& e) {
    SWSS_LOG_WARN("Next hop group key %s does not exist", ctx.nhg_index.c_str());
    return false;
}
```

→ 順序依存: `nexthop_group=<idx>` 経路は `NEXTHOP_GROUP_TABLE|<idx>` の NhgOrch 反映が先行必須。

### 4. NeighOrch 先行 — single NH

```cpp
// mplsrouteorch.cpp:514-540 (addLabelRoute, single NH)
if (m_neighOrch->hasNextHop(nexthop))
{
    ...
}
else
{
    SWSS_LOG_INFO("Failed to get next hop %s for %u, resolving neighbor", ...);
    m_neighOrch->resolveNeighbor(nexthop);
    return false;
}
```

NeighOrch の `m_syncdNextHops` 未登録なら ARP/ND をキックして `return false` → `m_toSync` 残置。`NEIGH_TABLE` 反映後の次サイクルで成立。
MPLS の場合、NH に outgoing label がある形（`m_key.isMplsNextHop()` 相当）でも、まず IP neighbor 解決を待ち、その後 NhgOrch 側の `isLabeled()` 分岐で MPLS NH を派生作成する（項 9 を参照）。

→ 順序依存: 各 nexthop IP の `NEIGH_TABLE` 解決が先行必須。

### 5. NeighOrch 先行 — ECMP (部分縮退 + tempLabelRoute)

```cpp
// mplsrouteorch.cpp:547-583 (addLabelRoute, ECMP)
if (!hasNextHopGroup(nextHops))
{
    ...
    for (auto it_nh = nextHops.getNextHops().begin(); ...)
    {
        if (!m_neighOrch->hasNextHop(nextHop))
        {
            SWSS_LOG_INFO("Failed to get next hop %s ... resolving neighbor", ...);
            m_neighOrch->resolveNeighbor(nextHop);
        }
    }
    ...
    addTempLabelRoute(ctx, nextHops);
    return false;
}
```

未解決 NH があるなら `resolveNeighbor` をキックしつつ `addTempLabelRoute` (`mplsrouteorch.cpp:420-`) で **解決済み単独 NH のサブセット一時 inseg** を ASIC に install。元 ECMP は m_toSync 残置 → 全 NH 解決後の次サイクルで本来の ECMP NHG に置換。

→ 順序依存（縮退あり）: 全 NH の NEIGH 解決が本来の ECMP 成立の前提。1 個以上解決済みなら部分縮退で疎通維持。IP route 版 `addTempRoute` と同等パスを MPLS 版で複製している。

### 6. RIF 先行 — directly-connected / intf NH

```cpp
// mplsrouteorch.cpp:501-510 (addLabelRoute)
next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %u", ...);
    return false;
}
```

`addLabelRoutePost` 側にも同型のガードあり (`mplsrouteorch.cpp:705-714`)。RIF 未作成なら `return false` で残置 → `INTERFACE`/`VLAN_INTERFACE`/`PORTCHANNEL_INTERFACE` 反映後に成立。

→ 順序依存: directly-connected / intf NH を含む MPLS ルートは IntfsOrch RIF 作成が先行必須。

### 7. SRv6 PIC / RetryCache — MPLS では未使用

`routeorch.cpp:192` の `createRetryCache(APP_ROUTE_TABLE_NAME);` は IP route 用。`APP_LABEL_ROUTE_TABLE_NAME` に対する `createRetryCache` 呼出はなく、`mplsrouteorch.cpp` 内に `RETRY_CST_*` / `contextIdExists` / `pic_context_id` 参照は 0 件。
→ MPLS は明示 RetryCache を持たず、未成立は基本 `m_toSync` 残置 polling で吸収する。

### 8. doLabelTask 内 bulk drain 順序

`RouteOrch::doLabelTask` (`mplsrouteorch.cpp:34-417`) は SET / DEL を以下の固定順で進める:

1. **resync ハンドリング** (`mplsrouteorch.cpp:63-95`): `key == "resync"` の SET で `m_syncdLabelRoutes` 全件を `DEL_COMMAND` として self-enqueue し `m_resync=true`。`m_resync=true` の間は受信 op を `it++` 残置で待機し、`resync` complete で flush。warm-style cold-resync 用パス。
2. **SET / DEL ループ** (`mplsrouteorch.cpp:100-330`): `addLabelRoute()` / `removeLabelRoute()` は `gLabelRouteBulker.create_entry()` / `set_entry_attribute()` / `remove_entry()` (`mplsrouteorch.cpp:627,644,652,661,882`) で bulker に積むのみで ASIC 反映なし。`addLabelRoute` の正常パス末尾も `return false` (項 12)。
3. **NHG 上限近傍での早期 break** (`mplsrouteorch.cpp:313-316`):

   ```cpp
   if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount &&
       gLabelRouteBulker.removing_entries_count() > 0)
   {
       break;
   }
   ```

   SET ループを途中で抜けて bulker flush へ進み、NHG 解放を促す。
4. **`gLabelRouteBulker.flush()`** (`mplsrouteorch.cpp:335`) — SET / DEL を一括 ASIC 反映。
5. **post-process ループ** (`mplsrouteorch.cpp:340-406`): `addLabelRoutePost` / `removeLabelRoutePost` を呼び、`m_syncdLabelRoutes` 更新と CRM (`CRM_MPLS_INSEG`) 反映を行う。失敗時は `it_prev++` で再評価。
6. **NHG ref-count 整理** (`mplsrouteorch.cpp:408-415`): `m_bulkNhgReducedRefCnt` を巡回して参照数 0 の NHG を `removeNextHopGroup`。

bulker 内重複検出: 同 doLabelTask 内で同 label を 2 回 create しようとすると `SAI_STATUS_ITEM_ALREADY_EXISTS` が即時返り `ERROR` + `return false` (`mplsrouteorch.cpp:628-633`)。retry なし、次サイクルで bulker クリア後に再評価。

注: `m_publisher.flush()` (IP route の APPL_STATE_DB 通知) は **MPLS では存在しない** (`mplsrouteorch.cpp` 内に `m_publisher` 参照 0 件)。Phase B Side-effects (`appl-mpls-route-side.md`) で確認済みの「APPL_STATE_DB ミラーなし」と整合。

→ タイミング依存: 同一 doLabelTask バッチ内の順序は固定。ConsumerStateTable 側で SET/DEL が merge されるため、バッチ間では最後の op のみが orchagent に届く。

### 9. nhgorch 側: MPLS NH の遅延作成 (`isLabeled()` 分岐)

```cpp
// nhgorch.cpp:563-570 (NextHopGroupMember::createSaiObject)
else if (isLabeled() && gNeighOrch->isNeighborResolved(m_key))
{
    NeighborContext ctx = NeighborContext(m_key);
    if (gNeighOrch->addNextHop(ctx))
    {
        nh_id = gNeighOrch->getNextHopId(m_key);
    }
}
```

MPLS NH は **IP neighbor が解決済になってから初めて** NeighOrch 経由で派生 NH を作成する。未解決時はこの分岐に入らず `resolveNeighbor` 経路 (`nhgorch.cpp:583-585`) に落ち、`nh_id = SAI_NULL_OBJECT_ID` のまま返却 → 上位で retry。
逆方向の lifecycle: ref_count が 0 になった MPLS NH は `~NextHopGroupMember()` 内 (`nhgorch.cpp:677-682`) で `removeMplsNextHop()` され、NeighOrch から除去される。

→ 順序依存: MPLS NH (`push<N>`/`swap<N>`) は基底 IP neighbor の `NEIGH_TABLE` 反映が先行必須。NhgOrch / RouteOrch が両方ライフサイクルを観るが、MPLS NH の create/remove は NeighOrch 側 API に委譲。

### 10. SAI race / set 系の handle

```cpp
// mplsrouteorch.cpp:777-840 (addLabelRoutePost)
status = *it_status++;
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set label %u with next hop(s) %s", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_MPLS, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

MPLS には IP route 版の `SAI_STATUS_ITEM_NOT_FOUND` 専用補正 (DualToR tunnel race) はない。SAI status は一律 `handleSaiSetStatus(SAI_API_MPLS, ...)` / `handleSaiRemoveStatus(SAI_API_MPLS, ...)` (`mplsrouteorch.cpp:907-915`) に委譲し、`task_need_retry` / `task_failed` のいずれかに振り分けて Phase D で集約整理済み。

→ タイミング依存: MPLS には DualToR 起源の同一 label DEL→SET race 補正パスは存在しない（MPLS 経路は DualToR tunnel 経由で書かれないため）。

### 11. Warm reboot 順序

`mplsrouteorch.cpp` / `nhgorch.cpp` 内に `warm` / `reconcile` / `WarmStart` の文字列は 0 件。warm reboot 時の MPLS 経路順序は **fpmsyncd 側 + RouteOrch 共通の resync プロトコル**で組まれる。

- 起動時 fpmsyncd は `WarmStartHelper::checkAndStart()` で warm-restart モードに入り（IP route と共通、`fpmsyncd.cpp:153-172`）、FRR 再接続後に再 push される経路を restoration timer / eoiuHoldTimer 満了まで集約する。
- ただし fpmsyncd の MPLS 経路書込みは `onLabelRouteMsg()` 経由で、`WarmStartHelper::insertRefreshMap` / `onWarmStartEnd` の差分計算は IP route テーブル前提で組まれている (`routesync.cpp` の `m_warmStartHelper` 系参照箇所は `RouteSync::onRouteMsg` 側に集中)。**MPLS 経路の warm reconcile は IP route ほど精緻ではなく**、起動直後に zebra から再 push される MPLS inseg がそのまま `SET` として doLabelTask に届く。
- doLabelTask 側は項 1 で示した `key == "resync"` プロトコルで cold-restart 用の wholesale 置換に対応する（warm reboot で fpmsyncd が `resync` を打つ運用ではないが、CLI / 上位ツールが `resync` SET を打てば全 LABEL_ROUTE_TABLE エントリを一括 DEL→再 SET できる）。

→ 順序依存: warm reboot 時の MPLS 経路は PortsOrch → IntfsOrch → NeighOrch → NhgOrch → RouteOrch の通常起動順序に依存し、未成立な依存があれば項 4-6 の retry / 項 5 の tempLabelRoute 縮退が連発するため reconcile 時間に影響する。

### 12. bulker 確定の遅延 (`addLabelRoute` 正常パスも `return false`)

`addLabelRoute` の正常パス末尾 (`mplsrouteorch.cpp:664` 付近) も `return false` で `m_toSync` 残置のまま bulker flush を待つ。確定は項 8 の post-process ループで `addLabelRoutePost` が `m_syncdLabelRoutes` 反映 + `gCrmOrch->incCrmResUsedCounter(CRM_MPLS_INSEG)` を実行して `m_toSync.erase` する。

→ タイミング依存: 正常書込みでも 1 サイクル分の遅延（bulker 経由）が乗る。

## 影響範囲のまとめ

| 順序関係 | 必須先行 | 不成立時の挙動 |
|---|---|---|
| NHG 経路 (`nexthop_group`) | PortsOrch readiness (NhgOrch 経由) | `NhgOrch::doTask` 早期 return |
| 非デフォルト VRF label | VrfOrch (`CONFIG_DB:VRF`) | `it++` 残置 (fpmsyncd は通常書かない) |
| `nexthop_group` 指定 | NhgOrch (`NEXTHOP_GROUP_TABLE`) | `ERROR` ログ + `++it` |
| intf NH | IntfsOrch RIF (`INTERFACE` 系) | `return false` 残置 |
| single NH | NeighOrch (`NEIGH_TABLE`) | `resolveNeighbor` + 残置 |
| ECMP | 全 NH の NEIGH 解決 | `addTempLabelRoute` サブセット install + 残置 |
| MPLS NH (`push`/`swap`) | 基底 IP `NEIGH_TABLE` 解決 → NhgOrch `isLabeled` 分岐 | retry |
| ASIC NHG 上限 | NHG 解放 | bulker 早期 break + tempLabelRoute |
| 同一バッチ内重複 create | bulker flush 完了 | `SAI_STATUS_ITEM_ALREADY_EXISTS` で `return false` |
| warm reboot | fpmsyncd `WarmStartHelper` + 通常起動順 | 通常 SET フロー (MPLS は専用 reconcile 差分なし) |

## 検出メソッド

grep targets:
- `mplsrouteorch.cpp`: `isVRFexists`, `getRouterIntfsId`, `hasNextHop`, `resolveNeighbor`, `getNhg`, `gLabelRouteBulker`, `m_maxNextHopGroupCount`, `SAI_STATUS_ITEM`, `handleSaiSetStatus`, `handleSaiRemoveStatus`, `addTempLabelRoute`, `m_resync`, `RETRY_CST`, `m_publisher`, `warm`, `reconcile`
- `nhgorch.cpp`: `allPortsReady`, `isLabeled`, `removeMplsNextHop`, `isNeighborResolved`
- `fpmsyncd/routesync.cpp`: `onLabelRouteMsg`, `WarmStart`

`RETRY_CST_*` / `m_publisher` / DualToR 専用 `SAI_STATUS_ITEM_NOT_FOUND` 補正は MPLS 経路には存在しないことを確認。`ERROR_TABLE` 書込は 0 件。順序依存違反は基本 `m_toSync` 残置 polling で吸収される。
