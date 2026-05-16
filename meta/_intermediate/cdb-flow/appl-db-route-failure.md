# APPL_DB ROUTE_TABLE 失敗・retry 分岐 (Task F Phase D 中間メモ)

ターゲットページ: `docs/reference/config-db/appl-db-route.md`

ソース (sonic-swss @ `4305596156d70e9797e8a881b3d19b46de0bce0d`):
- `orchagent/routeorch.cpp`
- `orchagent/nhgorch.cpp`
- `orchagent/crmorch.cpp`

## 1. doTask 入口での早期スキップ / リトライ

| 位置 | 条件 | 挙動 | 副作用 |
|------|------|------|--------|
| `routeorch.cpp` L609-L612 | `gPortsOrch->allPortsReady()` が false | 何もせずリターン (全ROUTE_TABLE タスクが次イベントまで待機) | toSync 据え置き → 後で再実行 |
| L697-L701 | `m_resync == true` | 当該 KFV を消費せず `it++`、`"resync"` complete メッセージまで保留 | `m_toSync` に残る (実質 retry) |
| L709-L714 | `Vrf<name>:` プレフィクスだが VRFOrch にその VRF が存在しない | `it++` (erase しない) → 後で再評価 | retry。VrfOrch が VRF を作成するまで保留 |
| L807-L812 | `nhg_index` (NHG ref) と `nexthop`/`ifname` の両方が非空 | `ERROR`「Route ... has both nexthop_group and ips/aliases」 → `erase` | ハード失敗、再投入されない |
| L876-L880 | `aliases.size() == 0 && !blackhole && !srv6_nh` | `WARN`「Skip the route ..., for it has an empty ifname field.」 → `erase` | ハード失敗 |
| L893-L897 | `vni_label` が L3 VNI でない | `WARN`「Route ... is received on non L3 VNI ...」→ `it++` | retry (L3 VNI が後で設定されれば成功) |
| L996-L1003 | `nhg_index` で `NhgOrch::getNhg()` が `out_of_range` 例外 | `ERROR`「Next hop group %s does not exist」 → `it++` | retry。NhgOrch が当該 NHG を作成するまで保留 |
| L985-L991 | EVPN: `ipv.size() != rmacv.size()` または `ipv.size() != vni_labelv.size()` | `ERROR`「invalid router mac/vni label field」 → `erase` | ハード失敗 |
| L915-L926 | nexthop alias が `eth0`/`docker0`/`usb0`/`lo`/`Loopback*` | `removeRoute(ctx)` 成功時 `erase`、失敗時 `it++` | 既存 ASIC 経路を削除して APPL_STATE_DB に publish |

## 2. addRoute() 内: nexthop 解決失敗と retry

`routeorch.cpp` L2050-L2156 (単一 NH 経路):

- L2086-L2090: `getRouterIntfsId()` が `SAI_NULL_OBJECT_ID` を返す (RIF 未作成) → `return false` → `addRoute` 全体が false → doTask が `it++` で **retry**。
- L2106-L2109: `m_neighOrch->isNextHopFlagSet(nexthop, NHFLAGS_IFDOWN)` (`IFDOWN` フラグ立ち) → `INFO`「Interface down for NH ..., skip this Route for programming」 → `return false` → **retry**。
- L2121-L2155 (IP neighbor 未解決パス):
  - overlay (VxLAN): `createRemoteVtep()` 失敗 → `ERROR`「Failed to create remote vtep ...」→ `return false` → retry。
  - overlay tunnel NH 作成失敗 → `ERROR`「Failed to create Tunnel Nexthop ...」→ `return false` → retry。
  - SRv6: `m_srv6Orch->srv6Nexthops()` 失敗 → `ERROR`「Failed to create SRV6 nexthop ...」→ `return false` → retry。
  - 通常 IP neighbor: `INFO`「Failed to get next hop ..., resolving neighbor」→ `m_neighOrch->resolveNeighbor(nexthop)` 呼び出し (ARP/ND probe をキック) → `return false` → retry。

`routeorch.cpp` L2161-L2244 (NHG 経路):

- L2188-L2200: 既存の NHG が無く `addNextHopGroup()` も失敗。
  - `nextHops.is_srv6_nexthop()` または既存経路の nhg が srv6 → `return false` (tempRoute なしで retry)。
- L2197-L2229: 各 NH について `hasNextHop` が false → overlay は `createRemoteVtep` / `addTunnelNextHop` を試行 (失敗で `return false`)、それ以外は `INFO`「Failed to get next hop ... resolving neighbor」+ `resolveNeighbor(nextHop)`。
- L2231-L2240: それでも NHG が作れない場合 `addTempRoute(ctx, nextHops)` を呼んで **temporary route** を 1 NH 構成で投入し、`return false` (元経路は失敗扱い)。
  - `addTempRoute` 本体 (L1947-L1989): `m_neighOrch->isNeighborResolved(*it)` でない NH と `NHFLAGS_IFDOWN` の NH を集合から除外。残った NH 集合が空なら何も書かずに退出。
  - つまり「NHG リソース枯渇 or NHG 作成失敗時にも、解決済み NH が 1 つ以上あれば部分的に経路を書き込む」フォールバック。

## 3. NHG リソース枯渇 (NHG 上限到達)

`routeorch.cpp` L1424-L1431 (`createFineGrainedNextHopGroup`)、L1478-L1485 (`addNextHopGroup`):

```cpp
if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount)
{
    SWSS_LOG_DEBUG("Failed to create new next hop group. \
            Reaching maximum number of next hop groups.");
    return false;
}
```

- `m_maxNextHopGroupCount` は SAI `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` 由来 (`routeorch.cpp` L60-L91)。STATE_DB SWITCH_CAPABILITY に `MAX_NEXTHOP_GROUP_COUNT` として publish される。
- 上限に達した場合 `addNextHopGroup` は false を返し、呼び出し元 `addRoute` は前節の通り `addTempRoute` 経由で 1-NH temp 経路にフォールバック。
- `doTask` L1096-L1101: NHG 残量が逼迫して bulker に削除待ちが溜まっている時、ループを break して flush を優先する (枯渇緩和)。

`nhgorch.cpp` L319-L362: NhgOrch 管理の temp NHG。`gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` のとき NHG 拡張をスキップし temp のまま保留。リソースが空くまで「temp として」生き続ける。

## 4. SAI 失敗の分岐 (handleSaiCreateStatus / handleSaiSetStatus)

`routeorch.cpp`:

- L1435-L1442 (NHG `create_next_hop_group`)、L1456-L1465 (NHG remove)、L1566-L1574 (member)、L1747-L1757 (member)、L1908-L1919 (FG remove)、L2510-L2526 (route create after bulker)、L2555-L2568 (default route set), L2573-L2586 (route set)、L2649-L2659 (member set)、L2828-L2841 / L2842-L2853 / L2869-L2879 (route remove)。

共通パターン:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to ...");
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`task_process_status` 区分:
- `task_success`: 警告のみで継続 (例: `SAI_STATUS_ITEM_ALREADY_EXISTS` を「成功」として吸収)
- `task_need_retry`: 呼び出し元が false を返し → doTask が `it++` で再投入 (retry)
- `task_failed`: ハード失敗 → `parseHandleSaiStatusFailure` がメトリクスを上げて false 返却、`m_toSync` から `erase`
- `task_invalid_entry` / `task_ignore`: erase して破棄

L2575: `SAI_STATUS_ITEM_NOT_FOUND` 専用パス。orchagent 内部キャッシュには経路があるが SAI 側で既に消えている場合 (dualtor の tunnel route 上書きが典型) → `m_syncdRoutes` から削除し `return false` (= retry: 次回は「新規 create」として処理される)。

L2302: `gRouteBulker.create_entry()` が即座に `SAI_STATUS_ITEM_ALREADY_EXISTS` を返した場合 → `ERROR` を出して `return false` (retry はせず、bulker 内に同一エントリ二重投入が無いことを期待)。

L2470-L2477 (FG nhg create 失敗): SAI が個別 status を `object_statuses` に書く → 失敗時 `m_fgNhgOrch->removeFgNhg(vrf_id, ipPrefix)` で逆ロールバックして `return false`。

## 5. CRM (Critical Resource Monitor) との関係

`crmorch.cpp`:

- `CRM_IPV4_ROUTE` / `CRM_IPV6_ROUTE` / `CRM_NEXTHOP_GROUP` / `CRM_NEXTHOP_GROUP_MEMBER` の used カウンタを `incCrmResUsedCounter` (route 成功時) / `decCrmResUsedCounter` (削除時) で更新。`routeorch.cpp` L148, L168, L257, L280, L446, L522, L1445, L1580, L1637, L2481-L2536, L2884-L2888 など。
- `checkCrmThresholds()` (L1116-L1190) が周期実行され、`utilization >= res.highThreshold` を超えた時点で `SWSS_LOG_WARN` + `event_publish("chk_crm_threshold", ...)` を発火し、`exceededLogCounter` が `CRM_EXCEEDED_MSG_MAX` 未満の間だけログ出力 (スパム抑止)。`utilization <= res.lowThreshold` で `THRESHOLD_CLEAR` を出してカウンタを 0 に戻す。
- **CRM は経路投入を直接ブロックしない**。SAI の `AVAILABLE_*_ROUTE_ENTRY` が 0 になれば、create で `SAI_STATUS_INSUFFICIENT_RESOURCES` などが返り、上記 (4) の handleSaiCreateStatus 経路で扱われる。
- 観測手順は `crm show resources ipv4_route` / `... ipv6_route` / `... nexthop_group` で CRM カウンタを照会、syslog の `THRESHOLD_EXCEEDED` を監視。

## 6. APPL_STATE_DB への失敗反映

- `publishRouteState(ctx, status=SAI_STATUS_SUCCESS)` (`routeorch.cpp` L3185-L3202) は `ResponsePublisher` 経由で `APP_ROUTE_TABLE_NAME` (= `ROUTE_TABLE`) を `APPL_STATE_DB` 側にミラー publish する。`is_set` のとき `protocol` のみ含み、DEL のときは fvs 空 (= APPL_STATE_DB から削除)。
- 成功パス (L1050, L1090, L2729, L2970) は `SAI_STATUS_SUCCESS` で publish。
- 失敗で retry 扱いになる経路は `publishRouteState` を呼ばずに `return false`、`m_toSync` に据え置く → APPL_STATE_DB には何も書かれない (= 「未確定」状態として観測可能)。
- 一部の終端失敗 (`SAI_API_ROUTE` set のハード失敗等) では `parseHandleSaiStatusFailure` が呼ばれ、状態は ResponsePublisher の `status` 経由でクライアントへ伝搬する設計だが、`publishRouteState` 直接の失敗 status 渡しは現状 SUCCESS のみ。

## 7. 表 (ページ用要約)

| 失敗カテゴリ | 検出箇所 | 観測手段 | 振る舞い |
|------------|---------|---------|---------|
| Ports 未準備 | `doTask` 冒頭 | syslog (PortsOrch 側) | 全 ROUTE_TABLE タスク保留 |
| VRF 未作成 | `doTask` L713 | `m_toSync` の積み上がり | `it++` で retry |
| NHG ref 不在 | `doTask` L1003 | `Next hop group %s does not exist` | retry |
| nexthop+nhg_index 同時指定 | `doTask` L807 | `has both nexthop_group and ips/aliases` | erase (ハード失敗) |
| ifname 空 (unicast) | `doTask` L877 | `Skip the route ..., empty ifname` | erase |
| L3 VNI 非適合 | `doTask` L893 | `received on non L3 VNI` | retry |
| RIF 未作成 | `addRoute` L2088 | `Failed to get next hop ...` | retry |
| IFDOWN フラグ | `addRoute` L2108 | `Interface down for NH ...` | retry |
| neighbor 未解決 | `addRoute` L2151, L2219 | `resolving neighbor` + ARP/ND probe | retry |
| NHG 上限到達 | `addNextHopGroup` L1478 | `Reaching maximum number of next hop groups` (DEBUG) | temp route フォールバック |
| SAI route create 失敗 | L2516 ほか | `Failed to create route ...` | handleSaiCreateStatus 経由で retry/erase |
| SAI route set 失敗 (ITEM_NOT_FOUND) | L2575 | キャッシュ不整合 → 自動修復 | キャッシュから消して retry |
| CRM 閾値超過 | `checkCrmThresholds` L1168 | syslog `THRESHOLD_EXCEEDED` + event `chk_crm_threshold` | 観測のみ。SAI 実枯渇で初めて create が失敗 |
