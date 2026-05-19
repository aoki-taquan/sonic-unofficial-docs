# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE — 暗黙参照テーブル調査メモ (Phase C)

調査日: 2026-05-19
対象テーブル: APPL_DB `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE`

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp` (`NhgOrch::doTask`, `NextHopGroup::syncMembers`, `NextHopGroupMember::getNhId`)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (`CbfNhgOrch::doTask`, `CbfNhg::sync`, `CbfNhg::update`)
- `sonic-swss/orchagent/routeorch.cpp` (`RouteOrch::getNhg`, `incNhgRefCount`, `decNhgRefCount`)

---

## NEXTHOP_GROUP_TABLE の暗黙参照

### NeighOrch (NEIGH_TABLE)

`NextHopGroupMember::getNhId()` (`nhgorch.cpp:534-590`) が各メンバーの SAI next-hop ID を以下の優先順で解決:

1. `m_key.isIntfNextHop()` → `gIntfsOrch->getRouterIntfsId(alias)` （RIF 参照）
2. `gNeighOrch->hasNextHop(m_key)` → `gNeighOrch->getNextHopId(m_key)` （通常 NH 解決）
3. labeled NH かつ `gNeighOrch->isNeighborResolved()` → `gNeighOrch->addNextHop()` → `getNextHopId()`
4. 上記全て失敗 → SRv6 NH 作成試行 or `gNeighOrch->resolveNeighbor()` トリガ → NH ID = SAI_NULL_OBJECT_ID

NH ID が `SAI_NULL_OBJECT_ID` の場合 `syncMembers()` は `success = false` を返し、当該メンバーをスキップしたまま残りのメンバーのみ SAI に送出する (`nhgorch.cpp:938-944`)。

`sync` 成功後は `gNeighOrch->increaseNextHopRefCount(m_key)` (`nhgorch.cpp:633`)、remove 時は `decreaseNextHopRefCount` (`nhgorch.cpp:648`) で参照カウントを管理。

### IntfsOrch (INTF_TABLE)

`NextHopGroupMember::getNhId()` の分岐 1 (`m_key.isIntfNextHop()`) で `gIntfsOrch->getRouterIntfsId(alias)` を呼び出し、インターフェース NHG（VRF 接続先直接転送）の RIF OID を取得 (`nhgorch.cpp:542`)。

単一メンバー非再帰グループの remove 時は `gIntfsOrch->decreaseRouterIntfsRefCount(nh_key.alias)` (`nhgorch.cpp:885`) でカウントダウン。

### RouteOrch (ROUTE_TABLE / NHG カウンタ)

- `gRouteOrch->getNhgCount()` + `NextHopGroup::getSyncedCount()` を上限 `getMaxNhgCount()` と比較 (`nhgorch.cpp:252,320`)。上限到達時は temporary NHG 作成で対処。
- `RouteOrch::incNhgRefCount()` / `decNhgRefCount()` (`routeorch.cpp:3147-3176`) が `ROUTE_TABLE` エントリの追加/削除に連動して NHG の ref_count を増減。ref_count > 0 の NHG は DEL 保留（Phase B 依存 #8 参照）。

### gSrv6Orch

SRv6 NH（`m_key.isSrv6NextHop()` 真）の場合:
- `gSrv6Orch->createSrv6NexthopWithoutVpn()` でラベルなし SRv6 nexthop を SAI に作成 (`nhgorch.cpp:550-553`)。
- デストラクタ内で ref_count=0 時に `gSrv6Orch->removeSrv6NexthopWithoutVpn()` を呼び出し SAI から削除 (`nhgorch.cpp:665`)。

### gCrmOrch (CRM カウンタ)

`NextHopGroup::sync()` が SAI create 成功後 `gCrmOrch->incCrmResUsedCounter(CRM_NEXTHOP_GROUP)` (`nhgorch.cpp:795`)、削除時 `decCrmResUsedCounter` でリソース残量を更新。

---

## CLASS_BASED_NEXT_HOP_GROUP_TABLE の暗黙参照

### NhgMapOrch (FC_TO_NHG_INDEX_MAP_TABLE)

`CbfNhg::sync()` (`cbfnhgorch.cpp:295-360`) の参照:

1. `gNhgMapOrch->getMaxNumFcs()` — MAP が持つ最大 FC 数と SAI 能力比較 (`cbfnhgorch.cpp:311`)。超過で `SWSS_LOG_ERROR` + `return false`
2. `gNhgMapOrch->getLargestNhIndex()` — MAP 内の最大 NH インデックスがメンバー数以上なら `SWSS_LOG_ERROR` + `return false` (`cbfnhgorch.cpp:327`)
3. `gNhgMapOrch->getMapId(m_selection_map)` — MAP の SAI OID 取得。`SAI_NULL_OBJECT_ID` なら `SWSS_LOG_ERROR` + `return false` （MAP 未存在時の再試行トリガ）(`cbfnhgorch.cpp:319-324`)
4. sync 成功後 `gNhgMapOrch->incRefCount(m_selection_map)` / 削除時 `decRefCount` (`cbfnhgorch.cpp:354,396`)

### NhgOrch (NEXTHOP_GROUP_TABLE)

CBF NHG の `members` フィールドに列挙された子 NHG キーを `gNhgOrch` / `gCbfNhgOrch` で逆引きし、各メンバーの SAI NHG OID (`SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID`) を取得 (`cbfnhgorch.cpp:247-265`)。子 NHG が未 synced なら `return false` で再試行待ち。子 NHG が temporary または recursive の場合はエラー＋ループ継続。

### RouteOrch (NHG 上限カウンタ)

`CbfNhgOrch::doTask()` も `gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= getMaxNhgCount()` を確認し (`cbfnhgorch.cpp:100`)、上限超過時は `success = false` でキューに戻す（NhgOrch と同一ロジック）。

### gCrmOrch (CRM カウンタ)

`CbfNhg::sync()` 成功後 `gCrmOrch->incCrmResUsedCounter(CRM_NEXTHOP_GROUP)` (`cbfnhgorch.cpp:358`)、削除時 `decCrmResUsedCounter` でリソース残量を更新。

---

## 書き込み先 (side refs)

| 書き込み先 | 操作 | キー / フィールド | evidence |
|-----------|------|-----------------|----------|
| NeighOrch 内部状態 | ref_count +1 / -1 | `NextHopKey` | `nhgorch.cpp:633,648` |
| IntfsOrch 内部状態 | RIF ref_count +1 / -1 | `alias` | `nhgorch.cpp:757,885` |
| NhgMapOrch 内部状態 | ref_count +1 / -1 | `selection_map` | `cbfnhgorch.cpp:354,396` |
| CRM (COUNTERS_DB 系) | CRM_NEXTHOP_GROUP +1 / -1 | — | `nhgorch.cpp:795`, `cbfnhgorch.cpp:358` |
