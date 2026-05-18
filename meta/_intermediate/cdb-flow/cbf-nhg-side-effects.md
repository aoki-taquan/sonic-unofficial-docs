# cbf-nhg Phase F — CLASS_BASED_NEXT_HOP_GROUP 副次 DB 書込調査

## 調査対象

- テーブル: `CLASS_BASED_NEXT_HOP_GROUP` (APPL_DB)
- 処理デーモン: `CbfNhgOrch` (`sonic-swss/orchagent/cbf/cbfnhgorch.cpp`)
- 調査日: 2026-05-18

## 調査方針

`CbfNhgOrch::doTask()` および呼び出される全メソッド (`CbfNhg::sync()`, `CbfNhg::update()`, `CbfNhg::remove()`, `CbfNhg::syncMembers()`, `CbfNhgMember::sync()`, `CbfNhgMember::remove()`) を精読し、APPL_DB / STATE_DB / ASIC_DB / COUNTERS_DB / CRM / NhgMapOrch 内部カウンタへの副次書込を列挙する。

## 発見した副次書込

### 1. CRM カウンタ更新 (CrmOrch)

**`gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)`**
- 発生箇所: `CbfNhg::sync()` L358
- 契機: CBF NHG の SAI `create_next_hop_group` が成功したとき
- 書込先: `CrmOrch` 内部カウンタ (COUNTERS_DB `COUNTERS:CRM_STATS` テーブルに定期反映される)
- 逆方向: `NhgBase::decSyncedCount()` の中で `gCrmOrch->decCrmResUsedCounter(CRM_NEXTHOP_GROUP)` が呼ばれる (NHG 削除時)

### 2. NhgMapOrch 参照カウント更新

**`gNhgMapOrch->incRefCount(m_selection_map)`**
- 発生箇所: `CbfNhg::sync()` L354 (作成成功後)
- 契機: CBF NHG の sync 完了時に `FC_TO_NHG_INDEX_MAP_TABLE` エントリの ref_count を +1

**`gNhgMapOrch->decRefCount(m_selection_map)`**
- 発生箇所: `CbfNhg::remove()` L396 (削除成功後), `CbfNhg::update()` L587 (selection_map 変更時の旧マップ解放)
- 契機: CBF NHG 削除、または selection_map 変更時に旧マップの ref_count を -1

**`gNhgMapOrch->incRefCount(selection_map)`** (新マップ)
- 発生箇所: `CbfNhg::update()` L589 (selection_map 変更時の新マップ取得)

これらは `NhgMapEntry::ref_count` フィールドのインメモリ更新。`NhgMapOrch` は DEL 試行時に `ref_count > 0` の場合は削除ブロックするため (`nhgmaporch.cpp:199`)、CBF NHG が存在する間は参照先マップは削除できない。

### 3. NhgOrch 参照カウント更新

**`gNhgOrch->incNhgRefCount(m_key)`** / **`gNhgOrch->decNhgRefCount(m_key)`**
- 発生箇所: `CbfNhgMember::sync()` L758 / `CbfNhgMember::remove()` L808
- 契機: CBF NHG の各メンバー NHG が SAI member として作成/削除されるたびに NhgOrch 側の参照カウントを更新

`NhgOrch` は `ref_count > 0` の NHG を削除から保護する。CBF NHG のメンバーに含まれる NHG は自動的に削除ガードされる。

### 4. NhgBase::incSyncedCount() / decSyncedCount()

- 発生箇所: `CbfNhg::sync()` L359 / `NhgBase::remove()` (基底クラス: `nhgbase.h:278`)
- 効果: `NhgBase::m_syncdCount` (static カウンタ) を更新。この値は新規 NHG 作成時の上限チェック `gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` で参照される

## DB への直接書込

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB (他テーブル) | なし | `CbfNhgOrch` は `CLASS_BASED_NEXT_HOP_GROUP_TABLE` を読むのみ。他 APPL_DB テーブルへの書込なし |
| STATE_DB | なし | `cbfnhgorch.cpp` に `state_db` / `StateDBConnector` / `Table("STATE_DB"...)` の参照は存在しない |
| ASIC_DB | SAI 経由で間接書込 | `sai_next_hop_group_api->create_next_hop_group()` / `create_next_hop_group_member()` が内部で ASIC_DB を更新する (SAI Redis 実装) |
| COUNTERS_DB | CRM 経由で間接書込 | `gCrmOrch->incCrmResUsedCounter()` が定期的に COUNTERS_DB `COUNTERS:CRM_STATS` へ反映 |
| FLEX_COUNTER_DB | なし | CBF NHG に対する Flex カウンタ設定は存在しない |

## Phase F 結論

`CLASS_BASED_NEXT_HOP_GROUP_TABLE` エントリ処理に伴う直接 DB 副次書込は存在しない。
副次効果は以下の 4 点:
1. CRM カウンタ (`CRM_NEXTHOP_GROUP`) のインメモリ更新 → 定期的に COUNTERS_DB へ反映
2. `NhgMapOrch` 内部の `FC_TO_NHG_INDEX_MAP_TABLE` エントリ参照カウント更新
3. `NhgOrch` 内部のメンバー NHG 参照カウント更新
4. `NhgBase::m_syncdCount` 静的カウンタ更新（NHG 上限チェックに使用）

SAI 経由の ASIC_DB 書込は副次書込ではなくメイン処理の一部として扱う。
