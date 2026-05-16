# ROUTE_TABLE (APPL_DB) 失敗・retry 分岐調査 (Phase D)

ターゲットページ: `docs/reference/config-db/route.md`

ソース (sonic-swss @ `4305596156d70e9797e8a881b3d19b46de0bce0d`):
- `orchagent/routeorch.cpp`
- `orchagent/saihelper.cpp`
- `orchagent/nhgorch.cpp`

---

## 1. doTask 入口での早期スキップ / リトライ

| 位置 | 条件 | 挙動 |
|------|------|------|
| `routeorch.cpp` L609 | `gPortsOrch->allPortsReady()` が false | 全 ROUTE_TABLE タスクを保留（次イベントまで待機） |
| L697–L701 | `m_resync == true` | KFV を消費せず `it++`、`"resync"` complete まで保留 |
| L709–L714 | `Vrf<name>:` プレフィクスだが VRFOrch に VRF が未登録 | `it++`（erase しない）→ VRF が登録されるまで retry |
| L807–L812 | `nhg_index` と `nexthop`/`ifname` の両方が非空 | `ERROR: Route has both nexthop_group and ips/aliases` → `erase`（ハード失敗） |
| L876–L880 | `aliases.size() == 0 && !blackhole && !srv6_nh` | `WARN: Skip the route, empty ifname` → `erase`（ハード失敗） |
| L893–L897 | `vni_label` が L3 VNI でない | `WARN: received on non L3 VNI` → `it++`（retry） |
| L985–L991 | EVPN: `ipv.size() != rmacv.size()` 等 | `ERROR: invalid router mac/vni label field` → `erase`（ハード失敗） |
| L996–L1003 | `nhg_index` で `NhgOrch::getNhg()` が `out_of_range` | `ERROR: Next hop group does not exist` → `it++`（retry） |

---

## 2. addRoute() 内: nexthop 解決失敗と retry

**RIF 未作成** (`routeorch.cpp` L2086–L2090):
- `getRouterIntfsId()` が `SAI_NULL_OBJECT_ID` を返す → `return false` → doTask が `it++` で **retry**

**インタフェース DOWN** (L2106–L2109):
- `isNextHopFlagSet(nexthop, NHFLAGS_IFDOWN)` が true → `INFO: Interface down for NH, skip Route` → `return false` → **retry**

**neighbor 未解決** (L2121–L2154):
- overlay VxLAN: `createRemoteVtep()` 失敗 → `ERROR: Failed to create remote vtep` → `return false` → retry
- tunnel NH 作成失敗 → `ERROR: Failed to create Tunnel Nexthop` → `return false` → retry
- SRv6: `srv6Nexthops()` 失敗 → `ERROR: Failed to create SRV6 nexthop` → `return false` → retry
- 通常 IP neighbor: `INFO: resolving neighbor` + `m_neighOrch->resolveNeighbor()` でARP/ND probe キック → `return false` → retry

**ECMP NHG 作成失敗** (L2188–L2242):
- `addNextHopGroup()` が false を返す（リソース枯渇等）
- 解決済み NH が 1 つ以上あれば `addTempRoute()` で 1-NH 仮経路を投入してフォールバック
- 解決済み NH が 0 の場合は何もせず `return false`（retry）

---

## 3. NHG リソース枯渇 (NHG 上限到達)

`routeorch.cpp` L1478–L1485 (`addNextHopGroup`):

```cpp
if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount)
{
    SWSS_LOG_DEBUG("Failed to create new next hop group. "
            "Reaching maximum number of next hop groups.");
    return false;
}
```

- `m_maxNextHopGroupCount` は SAI `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` 由来。
- 上限到達時は `addTempRoute` 経由で 1-NH 仮経路にフォールバック（ECMP は一時的に縮退）。
- `doTask` L1094–L1100: NHG 枯渇中かつ bulker に削除待ちがある場合、ループを break して flush を優先（枯渇緩和）。

---

## 4. addRoutePost() / removeRoutePost() での SAI 失敗分岐

共通パターン (`saihelper.cpp` L745–L761):

```cpp
bool parseHandleSaiStatusFailure(task_process_status status)
{
    switch (status)
    {
        case task_need_retry: return false;   // false = retry
        case task_failed:     return true;    // true  = 失敗確定、erase
    }
}
```

| 状況 | SAI status | handleSai*Status 結果 | 振る舞い |
|------|-----------|----------------------|---------|
| 既存エントリの SET で `ITEM_NOT_FOUND` | `SAI_STATUS_ITEM_NOT_FOUND` | 専用パス: キャッシュ削除 | `return false`（retry: 次回は新規 create） |
| SAI_STATUS_SUCCESS 以外（一般） | 各種 | `task_need_retry` → false | retry |
| 致命的 SAI エラー | 各種 | `task_failed` → true | erase（ハード失敗） |
| FG NHG create 失敗 | 失敗 | `m_fgNhgOrch->removeFgNhg()` でロールバック後 false | retry |

---

## 5. APPL_STATE_DB への失敗反映

- `publishRouteState(ctx)` は SAI 操作完了後（成功・失敗確定後）に呼ばれる。
- **retry 扱い**（`return false` でループ継続）の場合は `publishRouteState` を呼ばない → APPL_STATE_DB に何も書かれない（「未確定」状態）。
- **成功確定**（L1050, L1090, L2729, L2970）: `SAI_STATUS_SUCCESS` で publish → APPL_STATE_DB `ROUTE_TABLE:<prefix>` に `protocol=<proto>` 書込。
- DEL 成功: fvs 空で publish → APPL_STATE_DB エントリ削除。

---

## 6. 要約表

| 失敗カテゴリ | 検出箇所 | ログ / 観測手段 | 振る舞い |
|------------|---------|----------------|---------|
| Ports 未準備 | `doTask` 冒頭 | PortsOrch の syslog | 全タスク保留 |
| VRF 未作成 | `doTask` L713 | `m_toSync` の積み上がり | retry |
| NHG ref 不在 | `doTask` L1003 | `Next hop group does not exist` | retry |
| nexthop + nhg_index 同時指定 | `doTask` L807 | `has both nexthop_group and ips/aliases` | ハード失敗 (erase) |
| ifname 空 (unicast) | `doTask` L877 | `Skip the route, empty ifname` | ハード失敗 (erase) |
| L3 VNI 非適合 | `doTask` L893 | `received on non L3 VNI` | retry |
| RIF 未作成 | `addRoute` L2088 | `Failed to get next hop` | retry |
| IFDOWN フラグ | `addRoute` L2108 | `Interface down for NH` | retry |
| neighbor 未解決 | `addRoute` L2151, L2219 | `resolving neighbor` + ARP/ND probe | retry |
| NHG 上限到達 | `addNextHopGroup` L1478 | `Reaching maximum number of next hop groups` (DEBUG) | 1-NH temp 経路フォールバック |
| SAI route create 失敗 | `addRoutePost` L2514 | `Failed to create route` | handleSaiCreateStatus 経由で retry / ハード失敗 |
| SAI ITEM_NOT_FOUND | `addRoutePost` L2575 | キャッシュ不整合 (dualtor 等) | キャッシュから削除して retry |
