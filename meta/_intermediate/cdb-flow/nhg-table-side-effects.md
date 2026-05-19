# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE 副次 DB 書込調査メモ

調査日: 2026-05-19
対象コード: `sonic-swss/orchagent/nhgorch.cpp`, `nhgbase.h`, `cbf/cbfnhgorch.cpp`, `orchagent/crmorch.cpp`

---

## 調査方針

`NhgOrch` / `CbfNhgOrch` が APPL_DB `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE` エントリを処理する際に、主作用（ASIC_DB への SAI 書込）以外に副次的に書き込む DB・テーブルを特定する。

対象 DB: COUNTERS_DB (CRM テーブル)、ASIC_DB (SAI 経由)、STATE_DB、FLEX_COUNTER_DB

---

## 1. COUNTERS_DB への CRM カウンタ書込

### NhgOrch (nhgorch.cpp / nhgbase.h)

`gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)` が呼ばれる箇所:

```cpp
// nhgorch.cpp:795  — NextHopGroup::sync() 内、SAI create_next_hop_group 成功時
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP);
```

`gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)` が呼ばれる箇所:

```cpp
// nhgbase.h:277  — NextHopGroupBase::remove() 内、SAI remove_next_hop_group 成功時
gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP);
```

`CRM_NEXTHOP_GROUP_MEMBER` カウンタ (nhgbase.h):

```cpp
// nhgbase.h:132  — NextHopGroupMemberBase::sync() — SAI member 作成成功時
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER);

// nhgbase.h:151  — NextHopGroupMemberBase::remove() — SAI member 削除成功時
gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER);
```

### CbfNhgOrch (cbfnhgorch.cpp)

```cpp
// cbfnhgorch.cpp:358  — CbfNhg::sync() 内、SAI create_next_hop_group (CLASS_BASED) 成功時
gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP);
```

`decCrmResUsedCounter` は `nhgbase.h:277` の共通実装が担う（`CbfNhg` も `NextHopGroupBase` を継承）。

### CRM カウンタが COUNTERS_DB に書き込まれるタイミング

`CrmOrch::updateCrmCountersTable()` が定期タイマー (CRM_COUNTERS_POLL) で呼ばれ、in-memory カウンタ (`m_resourcesMap`) を `COUNTERS_DB` の `CRM` テーブルに `set()` する:

```cpp
// crmorch.cpp:1067-1115
m_countersCrmTable->set(cnt.first, attrs);
// → COUNTERS_DB:CRM:STATS フィールド crm_stats_nexthop_group_used / crm_stats_nexthop_group_member_used 等
```

テーブル名: `COUNTERS_DB` / table `CRM` / key `STATS`

フィールド:
| フィールド | 対応 CRM リソース | 更新タイミング |
|-----------|-----------------|-------------|
| `crm_stats_nexthop_group_used` | `CRM_NEXTHOP_GROUP` | NHG 作成/削除 → 定期タイマー |
| `crm_stats_nexthop_group_available` | `CRM_NEXTHOP_GROUP` | SAI getAvailability → 定期タイマー |
| `crm_stats_nexthop_group_member_used` | `CRM_NEXTHOP_GROUP_MEMBER` | NHG メンバー作成/削除 → 定期タイマー |
| `crm_stats_nexthop_group_member_available` | `CRM_NEXTHOP_GROUP_MEMBER` | SAI getAvailability → 定期タイマー |

定数参照: `sonic-swss/orchagent/crmorch.cpp:360-361` (crmUsedCntsTableMap), `crmorch.cpp:314-315` (crmAvailCntsTableMap)。
COUNTERS_CRM_TABLE 定数: `sonic-swss-common/common/schema.h:237` (`"CRM"`).

---

## 2. ASIC_DB への SAI 経由書込（主作用 — 副次 DB 書込対象外）

NhgOrch / CbfNhgOrch の主目的は `sai_next_hop_group_api` を通じて ASIC にグループを反映することであり、syncd が ASIC_DB に `ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP:{oid}` / `ASIC_STATE:SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MEMBER:{oid}` を書き込む。これは主作用のため Phase F 対象外とする。

---

## 3. STATE_DB / FLEX_COUNTER_DB

NhgOrch / CbfNhgOrch のコンストラクタ・doTask 内に `StateTable` / `ProducerStateTable` / `FlexCounterManager` の生成・使用は確認されなかった。STATE_DB と FLEX_COUNTER_DB への直接書込みはない。

---

## 4. nhgmaporch (CBF NHG マップ)

`nhgmaporch.cpp` (FC_TO_NHG_INDEX_MAP_TABLE) は NhgOrch / CbfNhgOrch とは別テーブルを購読する独立 Orch であり、本ページのスコープ外。ただし参照カウント経由で `gNhgMapOrch->incRefCount()` / `decRefCount()` が呼ばれる（cbfnhgorch.cpp:362/413）。これは STATE_DB 書込みではなくメモリ上の参照管理。

---

## 結論

副次 DB 書込は **COUNTERS_DB** の `CRM` テーブルのみ。
- `CRM:STATS` に `crm_stats_nexthop_group_used` / `crm_stats_nexthop_group_member_used` (およびそれぞれの `_available`) を定期タイマーで書き込む
- 書込みトリガ: NHG / NHG メンバーの SAI 作成・削除に連動して in-memory カウンタを増減し、CRM ポーリングタイマー発火時に COUNTERS_DB へ反映
- FLEX_COUNTER_DB / STATE_DB への直接書込みは確認されず
