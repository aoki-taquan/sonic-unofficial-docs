# APPL_DB ROUTE_TABLE 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/app-route.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/routeorch.cpp`
- `sonic-swss/orchagent/nhgorch.cpp`
- `sonic-swss/orchagent/crmorch.cpp`
- `sonic-swss/orchagent/saihelper.cpp`（SAI status → task_process_status 変換）

`routeorch` は `ConsumerStateTable` 経由で APPL_DB `ROUTE_TABLE` を購読し、各 SET/DEL を `m_toSync` に積んだ後 `doRouteTask()` で処理する。
失敗時のフロー制御は 2 軸:

- **`m_toSync` 残置 vs `erase`**: `it++` で残せば次サイクル (`doTask`) で自動再試行、`m_toSync.erase(it)` なら恒久スキップ
- **`handleSaiCreateStatus/handleSaiSetStatus/handleSaiRemoveStatus` の戻り値**: `task_need_retry` なら `parseHandleSaiStatusFailure` が `false` を返し呼び元 `addRoute()/addRoutePost()/removeRoute()` が false → `m_toSync` 残置。`task_failed` なら `true` 返却 → 恒久スキップ + ASIC_DB 同期失敗ログ。`task_success` なら通常パス（`saihelper.cpp:745-762`）

---

## 失敗パス一覧 (`doRouteTask`)

### 1. `nexthop_group` と `nexthop`/`ifname` の同時指定 → 恒久スキップ

`routeorch.cpp:810-814`:

```cpp
if (!nhg_index.empty() && (!ips.empty() || !aliases.empty()))
{
    SWSS_LOG_ERROR("Route %s has both nexthop_group and ips/aliases", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ログ: `LOG_ERROR "Route X has both nexthop_group and ips/aliases"`
- 効果: `m_toSync` から即削除。fpmsyncd が再書込しない限り SAI に届かない
- retry なし

### 2. VRF 未作成 → retry 維持

`routeorch.cpp:706-715`:

```cpp
if (!m_vrfOrch->isVRFexists(vrf_name))
{
    it++;
    continue;
}
```

- ログなし
- 効果: `m_toSync` に残置。次の `doTask` サイクルで再評価
- VRF 作成イベントで自動回復

### 3. ifname 空 (`unknown`) / 非 blackhole / 非 srv6 → 恒久スキップ

`routeorch.cpp:855-882`:

```cpp
if (alsv.size() == 0 && !blackhole && !srv6_nh)
{
    SWSS_LOG_WARN("Skip the route %s, for it has an empty ifname field.", key.c_str());
    if (m_syncdRoutes.find(vrf_id) != ...) {
        if (removeRoute(ctx))
            it = consumer.m_toSync.erase(it);
        else
            it++;
    } else {
        it = consumer.m_toSync.erase(it);
    }
}
```

- ログ: `LOG_WARN "Skip the route X, for it has an empty ifname field."`
- 効果: 既存ルートがあれば `removeRoute()` で削除→erase、なければ即 erase

### 4. 非 L3 VNI の overlay 受信 → 恒久スキップ

`routeorch.cpp:874, 918-920`:

```cpp
SWSS_LOG_WARN("Route %s is received on non L3 VNI %s", key.c_str(), vni_str.c_str());
... it = consumer.m_toSync.erase(it); ... else it++;
```

- 既存ルートがあれば `removeRoute()` を試み、成功時 erase / 失敗時 retain

### 5. SRv6 segment / source 数不整合 → 恒久スキップ

`routeorch.cpp:937-989`:

```cpp
SWSS_LOG_ERROR("inconsistent number of endpoints and srv6 vpn sids.");
it = consumer.m_toSync.erase(it);
```

同様に `inconsistent number of srv6_segv and srv6_srcs.`、不正な `router_mac`、不正な `vni_label` も `LOG_ERROR` → `erase`。retry なし。

### 6. NhgOrch 未登録の `nexthop_group` 参照 → retry 維持

`routeorch.cpp:1004-1015`:

```cpp
try { const NhgBase& nh_group = getNhg(nhg_index); ... }
catch (const std::out_of_range& e)
{
    SWSS_LOG_ERROR("Next hop group %s does not exist", nhg_index.c_str());
    ++it;
    continue;
}
```

- 効果: NhgOrch が当該 index を持つまで `m_toSync` に残置。NHG_TABLE 投入で自動回復
- backoff なし（`doTask` サイクル毎の polling）

### 7. 不明 op (SET/DEL 以外) → 恒久スキップ

`routeorch.cpp:1109-1112`:

```cpp
SWSS_LOG_ERROR("Unknown operation type %s\n", op.c_str());
it = consumer.m_toSync.erase(it);
```

---

## 失敗パス一覧 (`addRoute` / `addRoutePost`)

### 8. interface NH の RIF 未作成 → retry 維持

`routeorch.cpp:2083-2090, 2429-2436`:

```cpp
next_hop_id = m_intfsOrch->getRouterIntfsId(nexthop.alias);
if (next_hop_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Failed to get next hop %s for %s", ...);
    return false;
}
```

- `addRoute()` が false → 呼び元 `doRouteTask` で `it++`（`routeorch.cpp:1061, 1084`）
- IntfsOrch が当該 alias の RIF を作成すると次サイクルで成功

### 9. neighbor 未解決 (single NH) → resolveNeighbor 発火 + retry 維持

`routeorch.cpp:2149-2155`:

```cpp
SWSS_LOG_INFO("Failed to get next hop %s for %s, resolving neighbor",
        nextHops.to_string().c_str(), ipPrefix.to_string().c_str());
m_neighOrch->resolveNeighbor(nexthop);
return false;
```

- `resolveNeighbor()` で ARP/ND probe を発火させた上で false 返却
- 効果: NeighOrch が neighbor 学習を完了し APPL_DB `NEIGH_TABLE` 経由で `m_syncdNextHops` に登録されれば、次サイクル `addRoute` が成功する
- backoff なし、上限なし。学習しない限り永続 retry

### 10. neighbor 未解決 (ECMP) → 全 NH に resolveNeighbor + temp route + retry

`routeorch.cpp:2194-2243`:

```cpp
for(auto it = nextHops.getNextHops().begin(); ...)
{
    if(!m_neighOrch->hasNextHop(nextHop))
    {
        ... m_neighOrch->resolveNeighbor(nextHop);
    }
}
... addTempRoute(ctx, nextHops);
return false;
```

- 効果: 解決済み NH だけで構成された一時ルート (`addTempRoute`) を installし、未解決 NH には ARP/ND を撃つ。元ルートは false で `m_toSync` 残置
- 全 NH が解決すれば fullグループに昇格

### 11. interface DOWN (NHFLAGS_IFDOWN) → 一時的 skip

`routeorch.cpp:2106-2109, 1532-1535, 1707-1708`:

```cpp
if (m_neighOrch->isNextHopFlagSet(nexthop, NHFLAGS_IFDOWN))
{
    SWSS_LOG_INFO("Interface down for NH %s, skip this Route for programming", ...);
    return false;
}
```

- ECMP の場合は当該 NH だけ NHG membership から除外 (`L1531-1536`)、Route 全体は false → retry
- インタフェース UP イベントで NeighOrch が NHFLAGS_IFDOWN を解除し再評価

### 12. NHG メンバが 1 つも active でない → 一時的 skip

`routeorch.cpp:1548-1551`:

```cpp
if (!next_hop_ids.size())
{
    SWSS_LOG_INFO("Skipping creation of nexthop group as none of nexthop are active");
    return false;
}
```

- `addNextHopGroup` が false → `addRoute` も false → `m_toSync` 残置

### 13. SAI NHG 作成失敗 (`create_next_hop_group`) → handleSaiCreateStatus 経由

`routeorch.cpp:1566-1574, 1435-1442`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create next hop group %s, rv:%d", ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NEXT_HOP_GROUP, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- `task_need_retry` → false 返却 → `m_toSync` 残置
- `task_failed` → true 返却 → 上位 `addRoute` で false（NHG 作成失敗）→ `addTempRoute` 経由 retry
- SAI `SAI_STATUS_INSUFFICIENT_RESOURCES` / `TABLE_FULL` / `NO_MEMORY` / `NV_STORAGE_FULL` は `isSaiStatusResourceFull` 真（`saihelper.cpp:764-770`）。`handleSaiCreateStatus` の派生実装によっては `task_failed` を返し、orchagent abort + systemd 再起動経路に流れる

### 14. NHG 上限到達 (`m_maxNextHopGroupCount`) → addTempRoute + retry

`routeorch.cpp:1424-1429, 1478-1483`:

```cpp
if (m_nextHopGroupCount + NhgOrch::getSyncedNhgCount() >= m_maxNextHopGroupCount)
{
    SWSS_LOG_DEBUG("Failed to create new next hop group. \
                    Reaching maximum number of next hop groups.");
    return false;
}
```

- `addNextHopGroup` が false → `addRoute` → `addTempRoute` で単一 NH のサブセットを install、元 ECMP は `m_toSync` 残置
- bulker 内に削除待ち NHG があれば flush して空き作成 (`routeorch.cpp:1094-1100`)
- 別ルート DEL で NHG が解放されれば次サイクル成功

### 15. NHG メンバ SAI 作成失敗 → false 返却（ロールバックなし）

`routeorch.cpp:1629-1635`:

```cpp
if (nhgm_id == SAI_NULL_OBJECT_ID)
{
    // TODO: do we need to clean up?
    SWSS_LOG_ERROR("Failed to create next hop group %" PRIx64 " member %" PRIx64 ": %d\n", ...);
    return false;
}
```

- コメント `// TODO: do we need to clean up?` の通り NHG 自体は残ったまま、`addRoute` は false → retry
- 既知の cleanup 漏れ（leak の可能性）

### 16. SRv6 nexthop 作成失敗 → 恒久 false

`routeorch.cpp:2099-2147, 2168-2173`:

```cpp
if (!m_srv6Orch->srv6Nexthops(nextHops, next_hop_id))
{
    SWSS_LOG_ERROR("Failed to create SRV6 vpn %s", ...);
    return false;
}
```

- effect: SRv6 SID-LIST 未登録 / SAI capability NOT_SUPPORTED 時に発生

### 17. EVPN remote VTEP / Tunnel NH 作成失敗 → false (retry)

`routeorch.cpp:2126-2138, 2200-2213`:

```cpp
SWSS_LOG_ERROR("Failed to create remote vtep %s", ...);
return false;
... 
SWSS_LOG_ERROR("Failed to create Tunnel Nexthop %s", ...);
return false;
```

- effect: VxlanOrch / EvpnOrch の状態が揃ってから次サイクル再試行

### 18. PIC context_index 未登録 → RetryCache に park

`routeorch.cpp:2055-2060`:

```cpp
if (!ctx.context_index.empty() && !m_srv6Orch->contextIdExists(ctx.context_index))
{
    SWSS_LOG_INFO("Context ID %s does not exist, move task entry to RetryCache", ctx.context_index.c_str());
    ctx.retry_cst = make_constraint(RETRY_CST_PIC, ctx.context_index);
    return false;
}
```

- 効果: `RetryCache` (orch 基底クラスの仕組み、`routeorch.cpp:192` `createRetryCache(APP_ROUTE_TABLE_NAME)`) に park され、`notifyRetry(RETRY_CST_PIC + context_index)` が `m_srv6Orch` から呼ばれた時点で `m_toSync` に再 enqueue される
- backoff なし、context_id 解決契機ドリブン

### 19. SAI route create 失敗 → handleSaiCreateStatus 経由

`routeorch.cpp:2511-2528`:

```cpp
sai_status_t status = *it_status++;
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s", ...);
    if (ctx.nhg_index.empty() && nextHops.getSize() > 1)
    {
        removeNextHopGroup(nextHops);  // newly created NHG をロールバック
    }
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- effect: NHG ロールバックを実施したうえで `parseHandleSaiStatusFailure` 判定
  - `task_need_retry` → false → `m_toSync` 残置
  - `task_failed` → true → 失敗ログを残してスキップ、CRM `used` カウンタは increment されない（L2530-2537 はステータス成功時のみ通過）

### 20. SAI route set 失敗 (ITEM_NOT_FOUND) → cache 補正 + retry

`routeorch.cpp:2572-2581`:

```cpp
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    // Routeorch internal cache has an entry, but it has already been removed in sai.
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
```

- DualToR シナリオで tunnel route が消えた直後の learned route が踏むケース。`m_syncdRoutes` を補正し false 返却 → 次サイクルで「新規作成」パスへ流れる

### 21. SAI route set 失敗 (それ以外) → handleSaiSetStatus 経由

`routeorch.cpp:2583-2589, 2657-2660, 2849-2853`:

```cpp
SWSS_LOG_ERROR("Failed to set route %s with next hop(s) %s", ...);
task_process_status handle_status = handleSaiSetStatus(SAI_API_ROUTE, status);
if (handle_status != task_success)
{
    return parseHandleSaiStatusFailure(handle_status);
}
```

- 動作は SAI create 失敗と同じ判定

### 22. SAI route remove 失敗 → handleSaiRemoveStatus 経由

`routeorch.cpp:2871-2879`:

```cpp
SWSS_LOG_ERROR("Failed to remove route prefix:%s\n", ipPrefix.to_string().c_str());
task_process_status handle_status = handleSaiRemoveStatus(SAI_API_ROUTE, status);
if (handle_status != task_success)
{
    return parseHandleSaiStatusFailure(handle_status);
}
```

- 失敗時 CRM `used` カウンタは dec されない（L2882-2889 は成功時のみ通過）

### 23. addRoutePost: 何らかの理由で object_statuses 空 → retry

`routeorch.cpp:2388-2401`:

```cpp
if (object_statuses.empty())
{
    // Something went wrong before router bulker, will retry
    return false;
}
auto routeTableIter = m_syncdRoutes.find(vrf_id);
if (routeTableIter == m_syncdRoutes.end())
{
    SWSS_LOG_INFO("VRF 0x%" PRIx64 " doesn't exist in syncd routes for route %s, will retry later", ...);
    return false;
}
```

- VRF が race で消えた / bulker に積まれなかった等の異常時の retry path

### 24. nhg_index post check: NHG 未登録 / NH 未登録 / NHG 未作成 → false (retry)

`routeorch.cpp:2411-2459`:

```cpp
if (!gNhgOrch->hasNhg(ctx.nhg_index) && !gCbfNhgOrch->hasNhg(ctx.nhg_index))
{
    SWSS_LOG_INFO("Failed to get next hop group with index %s", ctx.nhg_index.c_str());
    return false;
}
... if (next_hop_id == SAI_NULL_OBJECT_ID) ... return false;
... if (!m_neighOrch->hasNextHop(nexthop)) ... return false;
... if (!hasNextHopGroup(nextHops)) ... return false;
```

- bulker flush 後の post-check で前提が崩れた場合の retry

### 25. ITEM_ALREADY_EXISTS in bulker → 恒久失敗 (return false; cleanup なし)

`routeorch.cpp:2301-2307`:

```cpp
sai_status_t status = gRouteBulker.create_entry(...);
if (status == SAI_STATUS_ITEM_ALREADY_EXISTS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s: already exists in bulker", ...);
    return false;
}
```

- bulker 内重複（同一バッチで同 prefix を 2 回 create）。`addRoute` が false → 上位 `doRouteTask` は `it++`（残置）。次サイクルで bulker をクリアしてから再評価

---

## NhgOrch (`nhgorch.cpp`) 側の失敗（APPL_DB ROUTE_TABLE が `nexthop_group` フィールド経由で間接依存）

### N1. NHG_TABLE 不整合 (`regular ip/alias と recursive 混在` 等) → 恒久スキップ

`nhgorch.cpp:100, 142, 177, 211`:

```
LOG_ERROR "Nexthop group X has both regular(ip/alias) and recursive fields"
LOG_ERROR "Invalid member nexthop group Y in parent nhg X"
LOG_ERROR "Inconsistent nexthop group type between X and Y"
LOG_ERROR "inconsistent number of endpoints and srv6_srcs."
```

- effect: NhgOrch が当該 NHG を登録しない → routeorch 側で「Next hop group X does not exist」(失敗パス #6) 経路へ

### N2. SAI create_next_hop_group 失敗 → handleSaiCreateStatus

`nhgorch.cpp:784-789`:

```cpp
SWSS_LOG_ERROR("Failed to create next hop group %s, rv:%d", ...);
task_process_status handle_status = handleSaiCreateStatus(SAI_API_NEXT_HOP_GROUP, status);
if (handle_status != task_success) ...
```

### N3. NHG メンバ作成失敗 → WARN ログのみ（部分成功許容）

`nhgorch.cpp:805, 940, 949, 975, 1044, 1059, 1082`:

```
LOG_WARN "Failed to create next hop members of group X"
LOG_WARN "Failed to get next hop X in group Y"
LOG_WARN "Skip next hop X in group Y, interface is down"
LOG_ERROR "Failed to create next hop group X's member Y"
LOG_WARN "Failed to update member X weight"
LOG_WARN "Failed to remove members from group X"
LOG_WARN "Failed to sync new members for group X"
```

- 一部メンバ失敗時もグループ自体は維持。後続 deps 変化（interface UP、neighbor 解決）で member 追加再試行

### N4. 不明 op → 恒久スキップ

`nhgorch.cpp:433`:

```cpp
SWSS_LOG_ERROR("Unknown operation type %s\n", op.c_str());
```

---

## CRM (`crmorch.cpp`) 側の関与（IPv4/IPv6 ROUTE の使用量監視）

CRM は route 失敗を「止める」側ではなく「観測する」側だが、threshold 超過時の挙動を整理。

### C1. SAI `_AVAILABLE_IPV4_ROUTE_ENTRY` / `_IPV6_ROUTE_ENTRY` クエリ失敗 → available カウンタ 0 (`crmorch.cpp:760-911`)

`getResAvailability()` が SAI 非対応属性で失敗した場合、`availableCounter` が 0 のまま COUNTERS_DB に publish される。VS/VPP/古い SDK ではこれが常態。

### C2. utilization 計算で div-by-zero → LOG_WARN のみ

`crmorch.cpp:1145-1147`:

```cpp
SWSS_LOG_WARN("%s Exception occurred (div by Zero): Used count %u free count %u", ...);
```

### C3. threshold 超過 → LOG_WARN + sonic-event 発火、最大 10 回まで

`crmorch.cpp:1168-1180`（`CRM_EXCEEDED_MSG_MAX=10`、`crmorch.cpp:16`）:

```cpp
if ((utilization >= res.highThreshold) && (cnt.exceededLogCounter < CRM_EXCEEDED_MSG_MAX))
{
    ...
    SWSS_LOG_WARN("%s THRESHOLD_EXCEEDED for %s %u%% Used count %u free count %u", ...);
    event_publish(g_events_handle, "chk_crm_threshold", &params);
    cnt.exceededLogCounter++;
}
else if ((utilization <= res.lowThreshold) ...)
{
    SWSS_LOG_WARN("%s THRESHOLD_CLEAR for %s %u%% Used count %u free count %u", ...);
    cnt.exceededLogCounter = 0;
}
```

- CRM 自体は SAI 操作をブロックしない。ASIC リソース不足は SAI が `SAI_STATUS_INSUFFICIENT_RESOURCES` / `TABLE_FULL` を返した時点で失敗パス #13 / #19 に流れる
- threshold 超過は運用監視向け通知のみ。high 超過後 10 回ログ → 沈黙、low 以下まで戻れば THRESHOLD_CLEAR を 1 回ログして counter リセット

---

## retry / replay 全体像

| 機構 | トリガ | 上限 | backoff |
|---|---|---|---|
| `m_toSync` (`it++` 残置) | `Orch::doTask` の次サイクル（イベント駆動 + select タイマ） | なし（永続 retry） | なし |
| `RetryCache` (`createRetryCache(APP_ROUTE_TABLE_NAME)`) | `notifyRetry(RETRY_CST_PIC + context_id)` 等の deps 変化 | なし | なし |
| `addTempRoute` | NHG 作成失敗時のサブセット fallback | 1 段 | 即時 |
| `m_neighOrch->resolveNeighbor` | route 投入時に neighbor 未解決のとき ARP/ND を発火 | なし | OS の ARP/ND タイマ |

「失敗 → orchagent abort → systemd restart」経路は `parseHandleSaiStatusFailure(task_failed)` 直後の上位 caller がさらに重大障害扱いした場合に限られる。一般的な `task_failed` は ASIC_DB 同期失敗ログを残して当該タスクをスキップする。

---

## STATE_DB / APPL_STATE_DB への失敗反映

| 失敗ケース | APPL_STATE_DB `ROUTE_TABLE\|<key>` | STATE_DB `ROUTE_TABLE\|<default>` |
|---|---|---|
| addRoute 成功 | `protocol=<v>` 書込 (`publishRouteState`, L3185-3201) | デフォルトルートのみ `state=ok` |
| addRoute SAI 失敗 (#19) | 書込まれない（成功時のみ `publishRouteState`）。`addRoutePost` false → next cycle で再試行成功時に publish | 影響なし |
| removeRoute 成功 | 空 fvs で del | デフォルトルートのみ `state=na` (`updateDefRouteState`, L287-295, L2856) |
| neighbor 未解決 (#9/#10) | 書込まれない。temp route が install されてもオリジナルは publish せず | 影響なし |
| NHG 上限到達 (#14) | 書込まれない。`addTempRoute` 内で publish される（L2729 `publishRouteState`） | 影響なし |
| Duplicate entry skip (`routeorch.cpp:1086-1092`) | `publishRouteState` 呼ばれる（DEL+SET consolidation 対策） | 影響なし |
| Subnet route が intf IP2ME と衝突 (`routeorch.cpp:1045-1052`) | `publishRouteState` 呼ばれる（一貫性維持） | 影響なし |

- `publishRouteState` は `ResponsePublisher m_publisher{"APPL_STATE_DB"}` (`orch.h:382`)。`m_directDbWrite=true` で `flush()` まで遅延する buffered 書込 (`routeorch.cpp:57-58, 1231`)。
- `ERROR_TABLE` への書き込みは routeorch / nhgorch / crmorch のいずれにもない（grep 結果）。

---

## 補足: 「失敗」と分類しない正常スキップ

以下は ERROR/WARN 相当のログを出さず erase される正常分岐（参考として）:

- `alsv[0] == "unknown"` (`routeorch.cpp:1025-1028`)
- `alsv[0] == "tun0"` (`routeorch.cpp:1030-1033`)
- VRF alias 経由の direct connected route (`routeorch.cpp:1035-1038`)
- non-global scope prefix (linklocal/multicast) (`routeorch.cpp:1040-1043`)
- fullmask subnet route と IP2ME 重複 (`routeorch.cpp:1045-1052`)
- Inband port 経由のリモートシステム neighbor 用 static route (`routeorch.cpp:2074-2081`)
