# MPLS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (chore/q67-f-phaseD-mpls)

ソース: `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp`, `sonic-net/sonic-swss/orchagent/nhgorch.cpp`

対象ページ: `docs/reference/config-db/appl-mpls-route.md` (APPL_DB `LABEL_ROUTE_TABLE`)

> 詳細な失敗マトリクスは `meta/_intermediate/cdb-flow/appl-mpls-route-failure.md` を参照。
> 本ファイルは Task F Phase D (mpls slug 向け) の走査証跡サマリ。

## 調査範囲

- `sonic-swss/orchagent/mplsrouteorch.cpp` 全行 (961行)
- `sonic-swss/orchagent/nhgorch.cpp` MPLS `isLabeled()` 分岐

## 主要失敗カテゴリ

### 1. NEXTHOP 未解決 → retry

`addLabelRoute()` (L514-540) は単一 NH が NeighOrch に未登録の場合 `resolveNeighbor()` を発火して `return false`。
ARP/NDP 解決後の次サイクルで成功する。ECMP パスでは `addTempLabelRoute()` で解決済み単独 NH を一時 inseg として ASIC に install し、全 NH 解決後に本来の ECMP に置換する (L550-583)。

```
addLabelRoute() L534-540:
  m_neighOrch->resolveNeighbor(nexthop);
  return false;  // → m_toSync 残置 = retry
```

### 2. SAI inseg 失敗

`addLabelRoutePost()` (L742-752) で `create_entry` が失敗した場合、NHG > 1 なら `removeNextHopGroup()` で作成済み NHG を巻き戻してから `return false` (retry)。`set_entry_attribute` 失敗 (L777-840) は `handleSaiSetStatus(SAI_API_MPLS, status)` で `task_need_retry` / `task_failed` に振り分け。`remove_entry` 失敗 (L906-915) は `handleSaiRemoveStatus(SAI_API_MPLS, status)` で同様に振り分け。

| SAI 操作 | 失敗時挙動 | ログ |
|---|---|---|
| `create_entry` (L742) | NHG巻き戻し + `return false` (retry) | LOG_ERROR "Failed to create label %u" |
| `set` PACKET_ACTION (L777) | `handleSaiSetStatus` → retry/abort | LOG_ERROR "Failed to set label %u with packet action forward" |
| `set` NEXT_HOP_ID (L790) | `handleSaiSetStatus` → retry/abort | LOG_ERROR "Failed to set label %u with next hop(s) %s" |
| `remove_entry` (L906) | `handleSaiRemoveStatus` → retry/abort | LOG_ERROR "Failed to remove label:%u" |

### 3. 不正ラベル入力 → drop (erase)

| 条件 | 検出箇所 | 結果 |
|---|---|---|
| `nexthop_group` と `nexthop`/`ifname` の同時指定 | `doLabelTask()` L165-171 | 即 `erase` (no retry) |
| `ifname` が空かつ非 blackhole | `doLabelTask()` L193-198 | 即 `erase` (no retry) |
| 未知 `op` | `doLabelTask()` L327-330 | LOG_ERROR + `erase` |

### 4. nhgorch MPLS NH 失敗

`NextHopGroupMember::createSaiObject()` の `isLabeled()` 分岐 (nhgorch.cpp L563-587) で:
- `isNeighborResolved == false` → `resolveNeighbor()` + `nh_id = SAI_NULL_OBJECT_ID` → 上位 retry
- `addNextHop()` 失敗 → `nh_id` 未更新 → 上位 retry
- interface down → LOG_WARN + NH メンバ除外 (NHG は残存メンバで継続)

## retry vs drop 判定ルール

- `addLabelRoute` / `removeLabelRoute` が `true` → `m_toSync.erase(it)` (完了)
- `false` → `++it` で次サイクル **retry** (m_toSync 残置)
- 入力バリデーション失敗 (両方指定・ifname 空) のみ即 erase (drop)
- `addLabelRoute` 正常パス末尾も `return false` (L664) — bulker flush 後に `addLabelRoutePost` で確定

## grep カバレッジ (mplsrouteorch.cpp)

| パターン | hit 数 | 主要行 |
|---|---|---|
| `SWSS_LOG_ERROR` | 9 | L167, 264, 329, 630, 744, 779, 792, 833, 909 |
| `SWSS_LOG_WARN` | 3 | L195, 488, 691 |
| `return false` (retry 経路) | 16+ | L489, 509, 530, 539, 573, 582, 632, 664, 680, 692, 713, 722, 734, 751, 884, 899 |
| `resolveNeighbor` | 2 | L538, 559 |
| `handleSaiSetStatus` | 3 | L781, 794, 835 |
| `handleSaiRemoveStatus` | 1 | L910 |
