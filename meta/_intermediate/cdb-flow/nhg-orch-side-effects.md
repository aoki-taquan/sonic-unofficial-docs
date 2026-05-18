# nhg-orch 副次 DB 書込み スキャン結果 (Phase F)

## 調査対象ファイル

- `sonic-swss/orchagent/nhgorch.cpp`
- `sonic-swss/orchagent/nhgbase.h`
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp`
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp`

## 副次 DB 書込み一覧

### COUNTERS_DB: CRM_NEXTHOP_GROUP (NhgOrch / CbfNhgOrch)

- **inc**: `NhgBase::sync()` → `nhgbase.h:795` / `cbfnhgorch.cpp:358`  
  `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)` 
  グループ SAI 作成成功時に呼び出される
- **dec**: `NhgBase::remove()` → `nhgbase.h:277`  
  `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP)`  
  グループ SAI 削除成功時に呼び出される

### COUNTERS_DB: CRM_NEXTHOP_GROUP_MEMBER (NhgBase member sync/remove)

- **inc**: `NhgMemberBase::sync()` → `nhgbase.h:132`  
  `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER)`  
  各 NHG メンバー SAI エントリ作成成功時
- **dec**: `NhgMemberBase::remove()` → `nhgbase.h:151`  
  `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MEMBER)`  
  各 NHG メンバー SAI エントリ削除成功時

### COUNTERS_DB: CRM_NEXTHOP_GROUP_MAP (NhgMapOrch)

- **inc**: `NhgMapOrch::doTask()` → `nhgmaporch.cpp:146`  
  `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MAP)`  
  FC_TO_NHG_INDEX_MAP_TABLE エントリ SAI 作成成功時
- **dec**: `NhgMapOrch::doTask()` → `nhgmaporch.cpp:211`  
  `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_NEXTHOP_GROUP_MAP)`  
  FC_TO_NHG_INDEX_MAP_TABLE エントリ SAI 削除成功時

### ref_count (内部メモリ、DB 非書込み)

- `RouteOrch::incNhgRefCount()` / `decNhgRefCount()` が `gNhgOrch->incNhgRefCount()` / `gCbfNhgOrch->incNhgRefCount()` を呼び出す
- ルートエントリが NHG を参照する際にカウントが増減する (`routeorch.cpp:2546, 2646, 2672, 2900, 3147-3176`)
- ref_count > 0 の NHG はオーケストレータ内部でブロック (DEL 拒否)
- **DB への書込みなし** — 内部メモリ上のカウンタのみ

## 不在確認

- STATE_DB への直接書込み: なし
- APPL_STATE_DB / ResponsePublisher: なし
- FLEX_COUNTER_DB: なし
- LOGLEVEL_DB: なし
- CONFIG_DB への書戻し: なし
- ASIC_DB は sai_next_hop_group_api 経由 (syncd) で書かれるが本ページの主作用のため除外
