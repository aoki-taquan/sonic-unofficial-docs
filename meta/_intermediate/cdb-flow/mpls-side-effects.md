# APPL_DB LABEL_ROUTE_TABLE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task q67-f Phase F / mpls-side-effects)
ソース: `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp` (961 行), `orchagent/nhgorch.cpp`

## 調査対象

`APPL_DB:LABEL_ROUTE_TABLE` の主購読者 `RouteOrch::doLabelTask()` 経路、および `NhgOrch` の
MPLS NH 分岐 (`isLabeled()`) で行われる副次 DB 書込・ASIC_DB 操作・CRM カウンタ更新を精査。

## 走査結果サマリ

| 副次 DB / リソース | 書込有無 | 根拠 |
|---|---|---|
| **ASIC_DB (SAI inseg_entry)** | **あり（主副作用）** | `gLabelRouteBulker.create_entry` / `set_entry_attribute` / `remove_entry` → syncd 経由で ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_INSEG_ENTRY` に反映 |
| **ASIC_DB (SAI next_hop / next_hop_group)** | **あり（NEXTHOP_GROUP 更新）** | `addNextHopGroup` / `removeNextHopGroup` → syncd 経由で `ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP` / `NEXT_HOP_GROUP_MEMBER` に反映 |
| **CRM カウンタ (CRM_MPLS_INSEG)** | **あり** | `gCrmOrch->incCrmResUsedCounter(CRM_MPLS_INSEG)` (L754), `decCrmResUsedCounter(CRM_MPLS_INSEG)` (L917) |
| **CRM カウンタ (CRM_MPLS_NEXTHOP)** | あり（NeighOrch 経由間接） | MPLS NH の addNextHop / removeMplsNextHop が `CRM_MPLS_NEXTHOP` を inc/dec |
| STATE_DB | **なし** | `mplsrouteorch.cpp` / `nhgorch.cpp` に `m_stateDb` / `STATE_DB` 参照 0 件 |
| COUNTERS_DB / FlexCounter | **なし** | `FlexCounter` / `COUNTERS_DB` 参照 0 件。SAI inseg_entry 統計収集は未統合 |
| APPL_STATE_DB | **なし** | `m_publisher` / `ResponsePublisher` 参照 0 件。MPLS パスは ack channel を持たない |

## 詳細: ASIC_DB SAI inseg_entry

### SET（新規作成）

```cpp
// mplsrouteorch.cpp:590-633
sai_inseg_entry_t inseg_entry;
inseg_entry.switch_id = gSwitchId;
inseg_entry.label = label;

// 新規: create_entry で SAI_OBJECT_TYPE_INSEG_ENTRY を ASIC_DB に書き込む
gLabelRouteBulker.create_entry(
    &object_statuses.back(), &inseg_entry,
    (uint32_t)inseg_attrs.size(), inseg_attrs.data()
);
// inseg_attrs に含まれる SAI 属性:
//   SAI_INSEG_ENTRY_ATTR_PACKET_ACTION (FORWARD / DROP)
//   SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID   (NHG or single NH OID)
//   SAI_INSEG_ENTRY_ATTR_NUM_OF_POP    (mpls_pop field の値)
```

### SET（既存更新）

```cpp
// mplsrouteorch.cpp:636-663
// ケース1: blackhole → non-blackhole 切替
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_PACKET_ACTION;
inseg_attr.value.s32 = SAI_PACKET_ACTION_FORWARD;
gLabelRouteBulker.set_entry_attribute(&object_statuses.back(), &inseg_entry, &inseg_attr);

// ケース2: non-blackhole → blackhole 切替
inseg_attr.id = SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION;  // MPLS orch のコピー誤りだが動作は同じ
inseg_attr.value.s32 = SAI_PACKET_ACTION_DROP;
gLabelRouteBulker.set_entry_attribute(&object_statuses.back(), &inseg_entry, &inseg_attr);

// ケース3: nexthop 変更
inseg_attr.id = SAI_INSEG_ENTRY_ATTR_NEXT_HOP_ID;
inseg_attr.value.oid = next_hop_id;
gLabelRouteBulker.set_entry_attribute(&object_statuses.back(), &inseg_entry, &inseg_attr);
```

### DEL

```cpp
// mplsrouteorch.cpp:866-884
sai_inseg_entry_t inseg_entry;
inseg_entry.switch_id = gSwitchId;
inseg_entry.label = label;
gLabelRouteBulker.remove_entry(&object_statuses.back(), &inseg_entry);
```

`gLabelRouteBulker.flush()` (`mplsrouteorch.cpp:335`) で一括 ASIC 反映。syncd が
`ASIC_STATE:SAI_OBJECT_TYPE_INSEG_ENTRY:{switch_id=...,label=<N>}` を更新する。

## 詳細: NEXTHOP_GROUP 更新

ECMP ルート（`nextHops.getSize() > 1`）の場合、RouteOrch 管理の内部 NHG を操作:

```cpp
// mplsrouteorch.cpp:550
if (!addNextHopGroup(nextHops)) {
    // ...一時ルート登録...
    addTempLabelRoute(ctx, nextHops);
    return false;
}

// mplsrouteorch.cpp:749 (Post 失敗時の巻き戻し)
removeNextHopGroup(nextHops);

// mplsrouteorch.cpp:408-415 (bulkNhgReducedRefCnt 巡回)
for (auto& it_nhg : m_bulkNhgReducedRefCnt) {
    removeNextHopGroup(it_nhg.first);
}
```

`addNextHopGroup` / `removeNextHopGroup` は syncd 経由で:
- `ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP` (グループ本体)
- `ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER` (メンバ各エントリ)

を作成・削除する。ref_count 管理は `m_syncdNextHopGroups[nextHops].ref_count` で追跡し、
0 になったグループを `m_bulkNhgReducedRefCnt` に積んで doLabelTask 末尾で一括削除。

`nexthop_group=<idx>` 指定の場合は NhgOrch / CbfNhgOrch が管理する NHG を流用し
`incNhgRefCount` / `decNhgRefCount` (`mplsrouteorch.cpp:763,814,824,946`) のみ。
RouteOrch 側での SAI NHG create/remove はしない。

## 詳細: CRM カウンタ

### CRM_MPLS_INSEG

```cpp
// mplsrouteorch.cpp:754 — addLabelRoutePost 成功時 (新規 inseg create)
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_MPLS_INSEG);

// mplsrouteorch.cpp:917 — removeLabelRoutePost 成功時
gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_MPLS_INSEG);
```

`CrmResourceType::CRM_MPLS_INSEG` は `crmorch.cpp:113` で `SAI_OBJECT_TYPE_INSEG_ENTRY` に
マップされ、COUNTERS_DB `CRM:STATS` の `crm_stats_mpls_inseg_used` を inc/dec する。
`available` は `sai_object_type_get_availability(SAI_OBJECT_TYPE_INSEG_ENTRY)` で別途取得。

### CRM_MPLS_NEXTHOP（NeighOrch 経由間接）

MPLS NH（`push<N>` / `swap<N>`）の create (`addNextHop`) / remove (`removeMplsNextHop`) は
NeighOrch 経由で `CRM_MPLS_NEXTHOP` を inc/dec する。直接の呼出元は:

- `mplsrouteorch.cpp:523-531` (`addNextHop(ctx)` — MPLS NH 新規)
- `mplsrouteorch.cpp:940` (`removeMplsNextHop(nexthop)` — ref_count == 0 時)
- `nhgorch.cpp:563-570` (`gNeighOrch->addNextHop(ctx)` — NHG メンバ MPLS NH)
- `nhgorch.cpp:677-682` (`removeMplsNextHop` — ~NextHopGroupMember destructor)

## 走査コマンドと結果

```bash
# 副次 DB 参照スキャン
grep -nE "STATE_DB|COUNTERS_DB|APPL_STATE_DB|FlexCounter|gStateDb|m_stateDb|m_countersDb|notificationProducer" \
  orchagent/mplsrouteorch.cpp orchagent/nhgorch.cpp
# => 0 件

# CRM スキャン
grep -nE "CrmResUsedCounter|CRM_MPLS" orchagent/mplsrouteorch.cpp
# => L754: incCrmResUsedCounter(CRM_MPLS_INSEG)
# => L917: decCrmResUsedCounter(CRM_MPLS_INSEG)

# ASIC SAI inseg スキャン
grep -n "gLabelRouteBulker\|inseg_entry\|create_entry\|remove_entry\|set_entry_attribute" \
  orchagent/mplsrouteorch.cpp
# => 多数ヒット (上記詳細参照)

# NEXTHOP_GROUP スキャン
grep -n "addNextHopGroup\|removeNextHopGroup\|incNhgRefCount\|decNhgRefCount\|increaseNextHopRefCount\|decreaseNextHopRefCount" \
  orchagent/mplsrouteorch.cpp
# => L414,550,749,759,763,804,814,820,824 など多数
```

## 結論

`APPL_DB:LABEL_ROUTE_TABLE` の SET / DEL は以下の副次リソースを更新する:

1. **ASIC_DB `SAI_OBJECT_TYPE_INSEG_ENTRY`**: label ルートの実体。bulker 経由で syncd に渡る
2. **ASIC_DB `SAI_OBJECT_TYPE_NEXT_HOP_GROUP` / `NEXT_HOP_GROUP_MEMBER`**: ECMP 時の NHG
3. **COUNTERS_DB `CRM:STATS.crm_stats_mpls_inseg_used`**: inseg 使用数カウンタ (inc/dec)
4. **COUNTERS_DB `CRM:STATS.crm_stats_mpls_nexthop_used`**: MPLS NH 使用数カウンタ (NeighOrch 経由)

STATE_DB / APPL_STATE_DB への書込は存在しない。FlexCounter 連携も未実装。
