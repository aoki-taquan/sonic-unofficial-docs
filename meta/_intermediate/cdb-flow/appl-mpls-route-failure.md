# LABEL_ROUTE_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-appl-mpls-route)

ソース: `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp`, `sonic-net/sonic-swss/orchagent/nhgorch.cpp`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### SET (`doLabelTask` → `addLabelRoute` / `addLabelRoutePost`) における失敗・retry 経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `nexthop_group` と `nexthop`/`ifname` の同時指定 | `doLabelTask()` L165-171 | エントリを `m_toSync` から **erase** (drop)・retry なし | LOG_ERROR ("Route %s has both nexthop_group and ips/aliases") | `mplsrouteorch.cpp:167-170` |
| `ifname` が空かつ非 blackhole | `doLabelTask()` L193-198 | エントリを **erase** (drop)・retry なし | LOG_WARN ("Skip the route %s, for it has an empty ifname field.") | `mplsrouteorch.cpp:195-197` |
| `op` が `SET_COMMAND` / `DEL_COMMAND` 以外 | `doLabelTask()` L327-330 | LOG_ERROR・以降 erase | LOG_ERROR ("Unknown operation type %s") | `mplsrouteorch.cpp:329` |
| `nexthop_group` 指定だが NhgOrch に該当 NHG なし (doLabelTask) | `doLabelTask()` L256-267 `catch(out_of_range)` | LOG_ERROR・`++it` で **retry** (erase しない) | LOG_ERROR ("Next hop group %s does not exist") | `mplsrouteorch.cpp:262-266` |
| `nexthop_group` 指定で NHG が `addLabelRoute` 内で消失 | `addLabelRoute()` L481-490 `catch(out_of_range)` | `return false` → 呼び出し側 (L290-302) で `++it` **retry** | LOG_WARN ("Next hop group key %s does not exist") | `mplsrouteorch.cpp:486-490` |
| 単一 NH が intf NH で RIF 未作成 | `addLabelRoute()` L502-510 | `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for %u") | `mplsrouteorch.cpp:505-510` |
| 単一 NH の IP neighbor 未解決 | `addLabelRoute()` L534-540 | `resolveNeighbor()` 発火後 `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for %u") | `mplsrouteorch.cpp:536-540` |
| MPLS NH の `addNextHop()` 失敗 (`m_neighOrch->addNextHop` false) | `addLabelRoute()` L523-531 | `return false` → **retry** | (NeighOrch 側ログ) | `mplsrouteorch.cpp:528-531` |
| ECMP NHG (`getSize() > 1`) で `addNextHopGroup` 失敗 | `addLabelRoute()` L550-583 | 未解決メンバごとに `resolveNeighbor()` 発火・`addTempLabelRoute()` で一時ルート登録・`return false` → **retry** | LOG_INFO ("Failed to get next hop %s in %s, resolving neighbor") | `mplsrouteorch.cpp:550-583` |
| 一時ルート対象 NH が現在のルートと同じ単独 NH | `addLabelRoute()` L567-575 | 一時ルートを追加せず `return false` → **retry** | なし | `mplsrouteorch.cpp:567-574` |
| `gLabelRouteBulker.create_entry` が `SAI_STATUS_ITEM_ALREADY_EXISTS` | `addLabelRoute()` L628-633 | `return false` → **retry** (m_toSync は erase されない) | LOG_ERROR ("Failed to create label route %u with next hop(s) %s") | `mplsrouteorch.cpp:628-633` |
| `addLabelRoute` 正常パス末尾の `return false` (bulker pending) | `addLabelRoute()` L664 | bulker flush 後に `addLabelRoutePost` で確定するため erase せず `++it` で次サイクル待ち | なし | `mplsrouteorch.cpp:664` |
| Post: `object_statuses` 空 (bulker 前で異常) | `addLabelRoutePost()` L677-681 | `return false` → **retry** | なし | `mplsrouteorch.cpp:677-681` |
| Post: NhgOrch/CbfNhgOrch から NHG が消失 | `addLabelRoutePost()` L687-694 | `return false` → **retry** | LOG_WARN ("Failed to get next hop group with index %s") | `mplsrouteorch.cpp:689-693` |
| Post: 単一 intf NH の RIF が消失 | `addLabelRoutePost()` L704-714 | `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for label %u") | `mplsrouteorch.cpp:709-714` |
| Post: 単一 NH が NeighOrch に存在しない | `addLabelRoutePost()` L717-724 | `return false` → **retry** | LOG_INFO ("Failed to get next hop %s for label %u") | `mplsrouteorch.cpp:718-723` |
| Post: ECMP NHG が消失 → 一時ルートで再 Post | `addLabelRoutePost()` L727-735 | `addLabelRoutePost(ctx, tmp_next_hop)` 再帰呼出後 `return false` → **retry** | なし | `mplsrouteorch.cpp:729-735` |
| Post: SAI `create_entry` 失敗 (新規作成) | `addLabelRoutePost()` L742-752 | NHG > 1 のとき `removeNextHopGroup()` で巻き戻し・`return false` → **retry** | LOG_ERROR ("Failed to create label %u with next hop(s) %s") | `mplsrouteorch.cpp:742-752` |
| Post: SAI `set` (PACKET_ACTION forward) 失敗 | `addLabelRoutePost()` L777-786 | `handleSaiSetStatus(SAI_API_MPLS, status)` 結果が `task_success` 以外なら `parseHandleSaiStatusFailure(handle_status)` を `return` (task_need_retry 等) | LOG_ERROR ("Failed to set label %u with packet action forward, %d") | `mplsrouteorch.cpp:779-786` |
| Post: SAI `set` (NEXT_HOP_ID) 失敗 | `addLabelRoutePost()` L790-799 | `handleSaiSetStatus` で **retry / abort 振り分け** | LOG_ERROR ("Failed to set label %u with next hop(s) %s") | `mplsrouteorch.cpp:790-799` |
| Post: SAI `set` (blackhole PACKET_ACTION drop) 失敗 | `addLabelRoutePost()` L831-840 | `handleSaiSetStatus` で **retry / abort 振り分け** | LOG_ERROR ("Failed to set blackhole label %u with packet action drop, %d") | `mplsrouteorch.cpp:831-840` |

### DEL (`removeLabelRoute` / `removeLabelRoutePost`) における失敗・retry 経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| VRF に対応する route table が存在しない | `removeLabelRoute()` L859-864 | `return true` → erase (silent success) | LOG_INFO ("Failed to find route table, vrf_id 0x%...") | `mplsrouteorch.cpp:860-864` |
| 該当 label の inseg エントリが m_syncdLabelRoutes に存在しない | `removeLabelRoute()` L872-877 | `return true` → erase (silent success) | LOG_INFO ("Failed to find inseg entry, ...") | `mplsrouteorch.cpp:872-877` |
| `removeLabelRoute` 正常パス末尾の `return false` | `removeLabelRoute()` L884 | bulker pending → 次サイクルで `removeLabelRoutePost` 確定 | なし | `mplsrouteorch.cpp:884` |
| Post: `object_statuses` 空 (bulker 前で異常) | `removeLabelRoutePost()` L896-900 | `return false` → **retry** | なし | `mplsrouteorch.cpp:896-900` |
| Post: SAI `remove_entry` 失敗 | `removeLabelRoutePost()` L906-915 | `handleSaiRemoveStatus(SAI_API_MPLS, status)` で **retry / abort 振り分け** | LOG_ERROR ("Failed to remove label:%u") | `mplsrouteorch.cpp:907-915` |

### nhgorch (MPLS NH) における失敗経路 (`isLabeled()` 分岐)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 単一 NH 同期時、`isLabeled() && isNeighborResolved == false` | `NextHopGroupMember::createSaiObject()` L571-587 (else branch) | `resolveNeighbor()` 発火・`nh_id = SAI_NULL_OBJECT_ID` のまま返却 → 上位で **retry** | LOG_INFO ("Failed to get next hop %s, resolving neighbor") | `nhgorch.cpp:583-585` |
| `isLabeled() && isNeighborResolved` で `gNeighOrch->addNextHop(ctx)` false | `createSaiObject()` L563-570 | `nh_id` は更新されず `SAI_NULL_OBJECT_ID` → 上位呼出側で **retry** | (NeighOrch 側ログ) | `nhgorch.cpp:563-570` |
| NHG 全体の SAI create 失敗 | `NextHopGroup::sync()` L784 付近 | LOG_ERROR・`return false` → 呼出側 **retry** | LOG_ERROR ("Failed to create next hop group %s, rv:%d") | `nhgorch.cpp:782-786` |
| NHG メンバの SAI create 失敗 | `NextHopGroup::sync()` L805 付近 | LOG_WARN・`return false` → **retry** | LOG_WARN ("Failed to create next hop members of group %s") | `nhgorch.cpp:805-807` |
| MPLS NH のメンバ NeighOrch に存在しない | `NextHopGroup::sync()` L940 付近 | LOG_WARN・スキップ・retry 対象 | LOG_WARN ("Failed to get next hop %s in group %s") | `nhgorch.cpp:940` |
| MPLS NH メンバの interface が down | `NextHopGroup::sync()` L949 付近 | LOG_WARN・スキップ (down 状態の NH は除外) | LOG_WARN ("Skip next hop %s in group %s, interface is down") | `nhgorch.cpp:949` |
| MPLS NH ラベル付きメンバ SAI create 失敗 | `NextHopGroup::sync()` L975 付近 | LOG_ERROR・`return false` → **retry** | LOG_ERROR ("Failed to create next hop group %s's member %s") | `nhgorch.cpp:975` |
| MPLS NH ref_count 0 で destructor 発火 | `NextHopGroupMember::~NextHopGroupMember()` L677-682 | `gNeighOrch->removeMplsNextHop(m_key)` で MPLS NH を NeighOrch から除去 | なし | `nhgorch.cpp:677-682` |

### 検出ロジック補足

- **retry vs drop の判定**: `doLabelTask` のループは `addLabelRoute` / `removeLabelRoute` が `true` を返したときのみ `m_toSync.erase(it)` でエントリを除去する。`false` 戻り値は `++it` で次サイクルでの **retry** を意味する。例外: 入力バリデーション失敗 (両方指定・ifname 空) は即 erase。
- **bulker 越しの非同期確定**: `addLabelRoute` は SAI 呼び出しを `gLabelRouteBulker` に登録するだけで、結果の確定は `addLabelRoutePost` で行う。`addLabelRoute` 正常パスの末尾も `return false` (L664) になっているのは仕様で、`addLabelRoutePost` が真の成否を確定して `m_syncdLabelRoutes` に反映する。
- **`handleSaiSetStatus` / `handleSaiRemoveStatus`**: SAI ステータスから `task_process_status` (`task_success` / `task_need_retry` / `task_failed`) を導出する OrchAgent 共通ハンドラ。`task_success` 以外は `parseHandleSaiStatusFailure` で対応する戻り値に変換され、上位 `doLabelTask` でエントリの retry / 破棄が決まる。
- **一時ルート (addTempLabelRoute)**: ECMP NHG が一部メンバ未解決で作成できない場合、解決済みの単独 NH を指す一時 inseg エントリを登録する。全メンバ解決後の retry サイクルで本来の NHG に置換される。
- **neighbor 解決トリガ**: `addLabelRoute` の各 retry 経路は `m_neighOrch->resolveNeighbor()` を呼び、ARP/NDP リクエスト送信を促す。これにより retry が空回りせず、neighbor が解決されると次サイクルで成功する。
- **MPLS NH 専用パス**: `nhgorch::createSaiObject` の `isLabeled() && isNeighborResolved` 分岐 (L563-570) は、IP neighbor が既に存在する状況で MPLS ラベル付き NH を NeighOrch 上に追加するためのもの。失敗時は `nh_id` が `SAI_NULL_OBJECT_ID` のままで上位が retry する。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `SWSS_LOG_ERROR` (mplsrouteorch) | 7 | `mplsrouteorch.cpp:167, 264, 329, 630, 744, 779, 792, 833, 909` |
| `SWSS_LOG_WARN` (mplsrouteorch) | 2 | `mplsrouteorch.cpp:195, 488, 691` |
| `SWSS_LOG_INFO` (mplsrouteorch, retry hint) | 5+ | `mplsrouteorch.cpp:307, 507, 536, 711, 720, 766, 843, 862, 874` |
| `return false` (mplsrouteorch retry) | 12+ | `mplsrouteorch.cpp:489, 509, 530, 539, 573, 582, 632, 664, 680, 692, 713, 722, 734, 751, 884, 899` |
| `handleSaiSetStatus` | 3 | `mplsrouteorch.cpp:781, 794, 835` |
| `handleSaiRemoveStatus` | 1 | `mplsrouteorch.cpp:910` |
| `resolveNeighbor` (MPLS path) | 2 | `mplsrouteorch.cpp:538, 559; nhgorch.cpp:585` |
| `isLabeled()` (nhgorch MPLS NH) | 2 | `nhgorch.cpp:563, 677` |

<!-- /failure -->
