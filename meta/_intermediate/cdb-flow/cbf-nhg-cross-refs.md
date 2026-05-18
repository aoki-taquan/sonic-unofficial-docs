# CLASS_BASED_NEXT_HOP_GROUP テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/cbf-nhg.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/cbf/cbfnhgorch.cpp` および `cbfnhgorch.h`。

## スキャン手順

```
grep -n "gNhgOrch\|gNhgMapOrch\|gRouteOrch\|gCrmOrch\|incRefCount\|decRefCount\|incNhgRefCount\|decNhgRefCount\|incCrmResUsed\|decCrmResUsed" \
  sonic-swss/orchagent/cbf/cbfnhgorch.cpp
```

## 検出した依存関係

### 1. NEXT_HOP_GROUP_TABLE (NhgOrch) — 必須前提

`gNhgOrch` は `cbfnhgorch.cpp:11` で extern 宣言。以下のタイミングで参照される:

- `syncMembers()` 内: `gNhgOrch->hasNhg(key)` (L644), `gNhgOrch->getNhg(key)` (L651, L690)
- メンバー sync 時: `gNhgOrch->incNhgRefCount(m_key)` (L758)
- メンバー remove 時: `gNhgOrch->decNhgRefCount(m_key)` (L808)
- temp NHG 確認: `gNhgOrch->getNhg(member->first)` (L468, L690)

各 member NHG が `isSynced()` でなければ `syncMembers()` は `false` を返してタスクを保留する。

### 2. FC_TO_NHG_INDEX_MAP_TABLE (NhgMapOrch) — 必須前提

`gNhgMapOrch` は `cbfnhgorch.cpp:14` で extern 宣言。以下のタイミングで参照される:

- `sync()` 内: `gNhgMapOrch->getMapId(m_selection_map)` (L319) が `SAI_NULL_OBJECT_ID` なら即 `false` を返してタスク保留
- `sync()` 内: `gNhgMapOrch->getLargestNhIndex(m_selection_map)` (L327) で上限チェック
- `sync()` 内: `gNhgMapOrch->getMaxNumFcs()` (L311) で FC 数上限チェック
- sync 成功時: `gNhgMapOrch->incRefCount(m_selection_map)` (L354)
- remove 時: `gNhgMapOrch->decRefCount(m_selection_map)` (L396)
- update 時: `gNhgMapOrch->getMapId(selection_map)` (L561), `getLargestNhIndex(selection_map)` (L569), `incRefCount`/`decRefCount` (L587-589)

### 3. RouteOrch — NHG 上限管理

`gRouteOrch` は `cbfnhgorch.cpp:15` で extern 宣言。

- `doTask()` 内新規作成パス (L100): `gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` で作成を保留するかどうか判定

RouteOrch のエントリを書き換えることはなく、カウンタ参照のみ。

### 4. CrmOrch — CRM カウンタ管理

`gCrmOrch` は `cbfnhgorch.cpp:13` で extern 宣言。

- SAI NHG 作成成功直後 (L358): `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)`
- DEL 時の `decCrmResUsedCounter` は `NhgBase` 基底クラスが担当

## OrchList 配置

`orchdaemon.cpp:500` 付近で `NhgMapOrch → NhgOrch → CbfNhgOrch` の順で `m_orchList` に配置されており、同一タスクループ内で依存 Orch が先行して処理される設計。

## 逆参照（被参照）

現時点のコードベースでは CBF NHG テーブルを他 Orch が leafref や参照カウント経由で依存するケースは確認されない。
