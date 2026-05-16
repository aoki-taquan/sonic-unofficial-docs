# appl-db-route ordering scan (Phase B intermediate)

対象: `docs/reference/config-db/appl-db-route.md` (APPL_DB `ROUTE_TABLE`)。
ソース: community master `sonic-net/sonic-swss`
- `orchagent/routeorch.cpp` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `orchagent/nhgorch.cpp` (同 ref)
- `fpmsyncd/fpmsyncd.cpp` (warm-restart 関連の補足)

## 検出した順序依存・タイミング依存

### 1. PortsOrch readiness ガード（NhgOrch のみ）

```cpp
// nhgorch.cpp:41-44 — NhgOrch::doTask 冒頭
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

`RouteOrch::doTask` 自体には `allPortsReady()` の直接ガードは無いが、`addRoute()` 内部で
`m_intfsOrch->getRouterIntfsId(alias)` が `SAI_NULL_OBJECT_ID` を返した時点で `return false`
（routeorch.cpp:2086-2090）になるため、PortsOrch / IntfsOrch 起動完了が結果として先行必須となる。
NHG ベースの経路では `NhgOrch::doTask` の早期 return で APPL_DB `NEXTHOP_GROUP_TABLE`
処理自体が止まる。

→ 順序依存: `PORT` 初期化 → `INTERFACE`/`VLAN_INTERFACE` の RIF 作成 → ROUTE_TABLE。

### 2. VRF 先行ガード（VRF-aware key）

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

`ROUTE_TABLE|Vrf<name>:<prefix>` 形式で VRFOrch に該当 VRF が未登録の場合、ログなしで
`it++` して `m_toSync` に残置。VrfOrch が CONFIG_DB `VRF` テーブルを消化して `isVRFexists`
が真を返すまで毎ループ retry し続ける（無限ポーリング）。

→ 順序依存: 非デフォルト VRF prefix では `CONFIG_DB:VRF|Vrf<name>` の VrfOrch 反映が
APPL_DB `ROUTE_TABLE` SET より先行必須。

### 3. NEXTHOP_GROUP 先行ガード（`nexthop_group` フィールド指定時）

```cpp
// routeorch.cpp:996-1015
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

`nexthop_group=<idx>` を持つ APPL_DB ROUTE エントリを処理するとき、`NhgOrch::m_syncdNextHopGroups`
に `<idx>` が未登録なら `ERROR` ログを出して `++it` 残置。NhgOrch が APPL_DB
`NEXTHOP_GROUP_TABLE` を消化するまで retry する。

→ 順序依存: `nexthop_group` 指定経路は `NEXTHOP_GROUP_TABLE|<idx>` の NhgOrch 反映が先行必須。
NhgOrch 自身が `allPortsReady()` ガード（項 1）を持つので、結局 PortsOrch 初期化完了が
連鎖的な前提となる。

### 4. NeighOrch（neighbor）先行 — single NH 経路

```cpp
// routeorch.cpp:2151-2155 (addRoute, single NH)
else
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s, resolving neighbor", ...);
    m_neighOrch->resolveNeighbor(nexthop);
    return false;
}
```

`m_neighOrch->hasNextHop(nexthop)` が false の場合、ARP/ND を投げて `addRoute` は false で抜ける
→ `it++` で `m_toSync` 残置。NEIGH_TABLE 反映後の次サイクルで成立する。

→ 順序依存: 各 nexthop IP の `NEIGH_TABLE` 解決が ROUTE_TABLE 確定より先行必須。

### 5. NeighOrch 先行 — ECMP 経路（部分縮退 + tempRoute）

```cpp
// routeorch.cpp:2194-2243 (addRoute, ECMP)
for (auto it = nextHops.getNextHops().begin(); ...)
{
    if (!m_neighOrch->hasNextHop(nextHop))
    {
        // overlay は createRemoteVtep/addTunnelNextHop, それ以外は resolveNeighbor
        m_neighOrch->resolveNeighbor(nextHop);
    }
}
...
addTempRoute(ctx, nextHops);   // L2240
return false;
```

未解決の NH は `resolveNeighbor` で ARP/ND をキックしつつ、`addTempRoute` (routeorch.cpp:1947-1989)
が **解決済み NH のみのサブセット** で一時経路を ASIC に install する。元 ECMP は `it++` で
m_toSync 残置、後続サイクルで本来の NHG に昇格する。SRv6 NHG では tempRoute を作らず
そのまま `return false` (L2188-L2200)。

→ 順序依存（縮退あり）: 全 NH の NEIGH_TABLE 解決が ECMP 完成の前提。1 個でも解決済みなら
部分縮退で疎通維持。

### 6. RIF（router interface）先行 — directly-connected

```cpp
// routeorch.cpp:2083-2090 (addRoute, intf NH)
next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s", ...);
    return false;
}
```

interface NH（directly-connected）で IntfsOrch が RIF を未作成の場合、`addRoute` は false を返し
m_toSync 残置 → `INTF_TABLE` 消化後の次サイクルで成立。

→ 順序依存: directly-connected 経路は CONFIG_DB `INTERFACE`/`VLAN_INTERFACE`/`PORTCHANNEL_INTERFACE`
の IntfsOrch 反映が先行必須。

### 7. SRv6 PIC `context_index` の RetryCache park

```cpp
// routeorch.cpp:2055-2060
if (!ctx.context_index.empty() && !m_srv6Orch->contextIdExists(ctx.context_index))
{
    SWSS_LOG_INFO("Context ID %s does not exist, move task entry to RetryCache", ...);
    ctx.retry_cst = make_constraint(RETRY_CST_PIC, ctx.context_index);
    return false;
}
```

```cpp
// routeorch.cpp:192
createRetryCache(APP_ROUTE_TABLE_NAME);
```

`pic_context_id` 指定で Srv6Orch に未登録の場合、`m_toSync` 上ポーリングではなく明示的に
`RetryCache` に park される。Srv6Orch が `PIC_CONTEXT` を消化して `notifyRetry(RETRY_CST_PIC+<id>)`
を呼ぶと再 enqueue される（無限ポーリング回避）。

→ 順序依存: SRv6 PIC 経路では `PIC_CONTEXT` 先行必須。retry-cache park で CPU 浪費を防ぐ。

### 8. doTask 内 bulk drain 順序

SET ループ（routeorch.cpp:1023-1101）→ `gRouteBulker.flush()` (L1117) → post-process ループ
（L1120-L1225）→ `m_publisher.flush()` (L1231) → NHG ref-count 整理 (L1234-) の 4 段で進む。
重要な点:

- **Bulker への積み込み** は SET ループの `addRoute()` 内 `gRouteBulker.create_entry()` / `set_entry_attribute()`
  （L2301 / L2318 / L2345 / L2354 / L2362 / L2371）で行われる。
- **flush 前は ASIC へ未反映**。同 doTask 内で同 prefix を 2 回 create しようとすると
  `SAI_STATUS_ITEM_ALREADY_EXISTS` が即時返り `ERROR + return false`（L2301-L2306）。
- **NHG 上限近傍での早期 break**（L1094-L1100）:

  ```cpp
  if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount &&
      gRouteBulker.removing_entries_count() > 0)
  {
      break;
  }
  ```

  SET ループを途中で抜けて先に削除を bulker flush → NHG 解放 → 次サイクルで残 SET を処理。

- **post-process は SET ループと同じ順序** で `it_prev` を進めるため、SET と post の状態整合は
  保証される。post で `addRoutePost` が false を返すと `it_prev++` で再評価される（既存ルートが
  bulker remove 待ちで競合する場合等）。
- **NHG member bulker は別**（`gNextHopGroupMemberBulker.flush()` が L1624 / L1732 で個別 flush）。

→ タイミング依存: 同一 doTask バッチ内では「SET 積込み → flush → SET post → DEL post → publisher flush →
NHG ref-count 整理」の順序が固定。バッチ間では SET/DEL の merge が ConsumerStateTable 側で
潰されるため、最後の op のみが orchagent に届く（L1088-L1091 のコメント参照）。

### 9. SAI race: `SAI_STATUS_ITEM_NOT_FOUND` on set（DualToR）

```cpp
// routeorch.cpp:2572-2581 — set 時の自動修復
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    SWSS_LOG_ERROR("Failed to set route ... not found");
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
```

DualToR で tunnel route が削除された直後に learned route が同 prefix を
`set_route_entry_attribute` しようとして race。内部 cache を補正して `return false` し、
次サイクルで「新規 create」として自動再投入される。

→ タイミング依存: 同一 prefix への DEL→SET 連続発生時の自動補正パス。

### 10. NHG 上限到達 → tempRoute サブセット install

`addNextHopGroup` (routeorch.cpp:1478-1485) が `m_nextHopGroupCount + NhgOrch::getSyncedNhgCount()
>= m_maxNextHopGroupCount` で false を返した場合、`addTempRoute(ctx, nextHops)` (L2240) が
解決済み 1 NH のサブセット tempRoute を ASIC に書き、元 ECMP は m_toSync 残置。
NhgOrch 側 (nhgorch.cpp:319-362) も同じ上限を見て temp NHG を保持し続け、
リソースが空くまで promotion を保留する。

→ タイミング依存: ASIC NHG リソース近傍では一時的に ECMP 縮退が観測される。

### 11. Warm reboot 順序（fpmsyncd 主導、routeorch は受動）

`routeorch.cpp` / `nhgorch.cpp` 自身には `warm` / `reconcile` の文字列は 0 件
（`grep -in warm` で確認）。warm reboot 時の順序は **fpmsyncd 側** が主導する:

```cpp
// fpmsyncd/fpmsyncd.cpp:153-172
bool warmStartEnabled = sync.getWarmStartHelper().checkAndStart();
if (warmStartEnabled)
{
    time_t warmRestartIval = sync.getWarmStartHelper().getRestartTimer();
    ...
    if (sync.getWarmStartHelper().runRestoration())
    {
        warmStartTimer.start();
        s.addSelectable(&warmStartTimer);
    }
}
```

- 起動時、fpmsyncd は `WarmStartHelper::checkAndStart()` で warm-restart モードに入り、
  既存 APPL_DB `ROUTE_TABLE` エントリを退避（restoration）。
- FRR (zebra) からの再 push を `warmStartTimer` 満了か `eoiuHoldTimer` 満了
  （fpmsyncd.cpp:196-238）まで集約し、`onWarmStartEnd(applStateDb)` (L212) で
  「APPL_DB に残った旧エントリ - FRR が再送した新エントリ」の差分のみを `DEL` として
  routeorch に流す。
- routeorch から見ると warm reboot は通常 SET/DEL イベントの連続でしかなく、特別なフックは無い。
  しかし「PortsOrch → IntfsOrch → NeighOrch → NhgOrch → RouteOrch」の起動順序が成立しないと、
  項 1-6 の retry / temp 縮退が連発するため、warm の reconcile 時間に影響する。

→ 順序依存: warm reboot 時は fpmsyncd の `WarmStartHelper` が「FRR 再接続 → restoration →
reconcile DEL flush」を順序づける。routeorch / nhgorch は通常時と同じ retry/temp ロジックで吸収。

## 影響範囲のまとめ

| 順序関係 | 必須先行 | 不成立時の挙動 |
|---|---|---|
| NHG 経路（`nexthop_group`） | PortsOrch readiness | `NhgOrch::doTask` 早期 return |
| 非デフォルト VRF prefix | VrfOrch (`CONFIG_DB:VRF`) | `it++` 残置ポーリング |
| `nexthop_group` 指定 | NhgOrch (`NEXTHOP_GROUP_TABLE`) | `ERROR` ログ + `++it` |
| directly-connected | IntfsOrch RIF (`INTERFACE`) | `return false` 残置 |
| single NH | NeighOrch (`NEIGH_TABLE`) | `resolveNeighbor` + 残置 |
| ECMP | 全 NH の NEIGH 解決 | tempRoute サブセット install + 残置 |
| SRv6 PIC | Srv6Orch (`PIC_CONTEXT`) | RetryCache park (constraint=`RETRY_CST_PIC`) |
| ASIC NHG 上限 | NHG 解放 | tempRoute install + bulker 早期 break で flush 優先 |
| 同一 prefix DEL→SET race | SAI 側完了 | `m_syncdRoutes` 補正 → 次サイクル create にフォールバック |
| 同一バッチ内重複 create | bulker flush 完了 | `SAI_STATUS_ITEM_ALREADY_EXISTS` で `return false` |
| warm reboot | fpmsyncd `WarmStartHelper` | restoration → timer → reconcile DEL flush |

## doTask バッチ内のフロー（要約）

1. `RouteOrch::doTask(Consumer&)` で `m_toSync` を順次評価し、各エントリで `addRoute()` か
   `removeRoute()` を呼ぶ。`addRoute()` 内では SAI bulker への積込みのみで ASIC 反映はしない。
2. SET ループ末尾で `gRouteBulker.flush()` を呼んで一括 ASIC 反映（routeorch.cpp:1117）。
3. post-process ループで bulker の戻り status を見ながら `addRoutePost` / `removeRoutePost` を
   呼び、`m_syncdRoutes` の更新と APPL_STATE_DB への `publishRouteState` を行う。
4. `m_publisher.flush()` で APPL_STATE_DB notification を即時送出（zebra への offload reply 遅延回避、
   routeorch.cpp:1227-1231）。
5. `m_bulkNhgReducedRefCnt` を巡回して参照数 0 の NHG を `removeNextHopGroup`（routeorch.cpp:1234-）。
6. NHG 上限近傍で削除待ちが溜まっている場合は SET ループを途中で `break` して flush と
   解放を優先する（routeorch.cpp:1094-1100）。

## 検出メソッド

grep targets:
- `routeorch.cpp`: `isVRFexists`, `getRouterIntfsId`, `hasNextHop`, `resolveNeighbor`, `getNhg`,
  `contextIdExists`, `addTempRoute`, `SAI_STATUS_ITEM_NOT_FOUND`, `SAI_STATUS_ITEM_ALREADY_EXISTS`,
  `RETRY_CST_PIC`, `gRouteBulker`, `flush`, `m_publisher`, `m_maxNextHopGroupCount`
- `nhgorch.cpp`: `allPortsReady`, `m_syncdNextHopGroups`, `gRouteOrch->getMaxNhgCount`, `isTemp`
- `routeorch.cpp` / `nhgorch.cpp`: `warm` / `reconcile` → **0 件**（warm 主導は fpmsyncd 側）
- `fpmsyncd/fpmsyncd.cpp`: `WarmStartHelper`, `checkAndStart`, `runRestoration`,
  `onWarmStartEnd`, `eoiuHoldTimer`

`ERROR_TABLE` 直接書込は routeorch / nhgorch に存在せず、順序違反は基本的に
`m_toSync` 残置ポーリングか明示的 RetryCache（PIC 限定）で吸収される。
