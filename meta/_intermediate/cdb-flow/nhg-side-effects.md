# NEXTHOP_GROUP_TABLE 副次 DB 書込み スキャン結果 (Phase F)

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp`
- `sonic-swss/orchagent/nhgbase.h`（`NhgCommon::sync()` / `remove()`、`NhgMemberBase::sync()` / `remove()`）

## 副次 DB 書込み一覧

### COUNTERS_DB: CRM_NEXTHOP_GROUP

- **inc**: `NextHopGroup::sync()` → `nhgorch.cpp:795`
  `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)`
  NHG SAI グループオブジェクト (`create_next_hop_group`) 成功時に呼び出される
- **dec**: `NhgCommon::remove()` → `nhgbase.h:277`（`NhgCommon::remove` 経由）
  `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)`
  NHG SAI グループオブジェクト削除成功時に呼び出される

### COUNTERS_DB: CRM_NEXTHOP_GROUP_MEMBER

- **inc**: `NhgMemberBase::sync()` → `nhgbase.h:132`
  `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER)`
  NHG メンバー (`create_next_hop_group_member`) SAI エントリ作成成功時
- **dec**: `NhgMemberBase::remove()` → `nhgbase.h:151`
  `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER)`
  NHG メンバー SAI エントリ削除成功時

### ref_count (内部メモリのみ、DB 非書込み)

- `RouteOrch::incNhgRefCount()` / `decNhgRefCount()` が `gNhgOrch->incNhgRefCount()` を呼ぶ
- ルートエントリが NHG を参照するたびにカウントが増減する
- ref_count > 0 の NHG は DEL_COMMAND でブロックされる（`nhgorch.cpp:414`）
- **DB への書込みなし** — orchagent プロセス内のメモリカウンタのみ

## 不在確認

- STATE_DB への直接書込み: なし
- APPL_STATE_DB / ResponsePublisher: なし
- FLEX_COUNTER_DB: なし
- LOGLEVEL_DB: なし
- CONFIG_DB への書戻し: なし
- ASIC_DB は sai_next_hop_group_api 経由 (syncd) で書かれるが本テーブルの主作用のため除外
