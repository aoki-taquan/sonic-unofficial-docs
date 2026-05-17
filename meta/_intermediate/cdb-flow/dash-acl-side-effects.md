# DASH_ACL_* — 副次 DB 書込み分析 (Phase F)

ソース:
- `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/dash/dashaclorch.cpp` (同上)
- `sonic-swss/orchagent/dash/dashtagmgr.cpp` (同上)

---

## ASIC_DB 書込み (SAI 経由)

DASH ACL 系の SAI 呼び出しは `sai_dash_acl_api` と `sai_dash_eni_api` を通じて syncd → ASIC_DB に反映される。

| 操作 | SAI API | ASIC_DB への反映 |
|------|---------|-----------------|
| `DASH_ACL_GROUP_TABLE` SET 成功 | `sai_dash_acl_api->create_dash_acl_group(&group.m_dash_acl_group_id, gSwitchId, ...)` | `ASIC_STATE:SAI_OBJECT_TYPE_DASH_ACL_GROUP:<oid>` 生成 |
| `DASH_ACL_GROUP_TABLE` DEL 成功 | `sai_dash_acl_api->remove_dash_acl_group(group.m_dash_acl_group_id)` | 対応 OID エントリ削除 |
| `DASH_ACL_RULE_TABLE` SET 成功 | `sai_dash_acl_api->create_dash_acl_rule(&rule_info.m_dash_acl_rule_id, gSwitchId, ...)` | `ASIC_STATE:SAI_OBJECT_TYPE_DASH_ACL_RULE:<oid>` 生成 |
| `DASH_ACL_IN/OUT_TABLE` SET（バインド）成功 | `sai_dash_eni_api->set_eni_attribute(eni.eni_id, &attr)` | `ASIC_STATE:SAI_OBJECT_TYPE_ENI:<eni_oid>` のステージ ACL グループ属性更新 |
| `DASH_ACL_IN/OUT_TABLE` DEL（アンバインド）成功 | `sai_dash_eni_api->set_eni_attribute(eni.eni_id, &attr)` (`attr.value.oid = SAI_NULL_OBJECT_ID`) | 対応 ENI OID のステージ属性を NULL にクリア |

証跡:
- `dashaclgroupmgr.cpp:167` (`create_dash_acl_group`)
- `dashaclgroupmgr.cpp:206` (`remove_dash_acl_group`)
- `dashaclgroupmgr.cpp:367` (`create_dash_acl_rule`)
- `dashaclgroupmgr.cpp:430` (`set_eni_attribute` バインド)
- `dashaclgroupmgr.cpp:485` (`set_eni_attribute` アンバインド)

---

## STATE_DB 書込み

**DASH ACL テーブルは STATE_DB に一切書き込まない。**

通常の `ACL_TABLE` / `ACL_RULE` は `STATE_ACL_TABLE_TABLE_NAME` へのステータス書込みを行うが、`DashAclOrch` / `DashAclGroupMgr` にはその実装が存在しない。`DashAclOrch` のコンストラクタ引数に `app_state_db` が渡されるが、コンストラクタ本体では使用されておらず、メンバー変数にも格納されない。

---

## CRM カウンタ書込み (COUNTERS_DB 経由)

`gCrmOrch` 経由で COUNTERS_DB の DASH ACL 使用カウンタを更新する。

| タイミング | CRM 操作 | CRM リソースタイプ |
|-----------|---------|------------------|
| `DASH_ACL_GROUP_TABLE` SET 成功（グループ作成） | `gCrmOrch->incCrmDashAclUsedCounter(crm_rtype, group.m_dash_acl_group_id)` | `CRM_DASH_IPV4_ACL_GROUP` または `CRM_DASH_IPV6_ACL_GROUP` |
| `DASH_ACL_GROUP_TABLE` DEL 成功（グループ削除） | `gCrmOrch->decCrmDashAclUsedCounter(crm_rtype, group.m_dash_acl_group_id)` | 同上（ルールカウンタも一括リセット） |
| `DASH_ACL_RULE_TABLE` SET 成功（ルール作成） | `gCrmOrch->incCrmDashAclUsedCounter(crm_rtype, group.m_dash_acl_group_id)` | `CRM_DASH_IPV4_ACL_RULE` または `CRM_DASH_IPV6_ACL_RULE` |

**注意**: ルール削除時の `decCrmDashAclUsedCounter` はルール個別には呼ばれない。グループ削除時の `decCrmDashAclUsedCounter(GROUP, ...)` が配下のルールカウンタも一括リセットする実装となっている (`dashaclgroupmgr.cpp:215` のコメント: `"Will also delete/zero out ACL rule count for this group, no need to do so separately"`)。

証跡:
- `dashaclgroupmgr.cpp:174-176` (グループ作成時 inc)
- `dashaclgroupmgr.cpp:213-216` (グループ削除時 dec)
- `dashaclgroupmgr.cpp:374-376` (ルール作成時 inc)

---

## インメモリ状態変化（m_groups_table / DashTagMgr）

APP_DB / STATE_DB / ASIC_DB 以外に、orchagent プロセス内のインメモリ構造体が更新される。

| 操作 | インメモリ変化 | 実装箇所 |
|------|-------------|---------|
| グループ作成 | `m_groups_table.emplace(group_id, group)` | `dashaclgroupmgr.cpp:190` |
| グループ削除 | `m_groups_table.erase(group_id)` + `detachTags(...)` | `dashaclgroupmgr.cpp:242-243` |
| ルール作成 | `group.m_rule_count++` + `group.m_tags.insert(tag)` + `attachTags(group_id, group.m_tags)` | `dashaclgroupmgr.cpp:413-414` |
| バインド | `group.m_in_tables[eni_id].insert(stage)` または `group.m_out_tables[eni_id].insert(stage)` | `dashaclgroupmgr.cpp:466-469` |
| アンバインド | `group.m_in/out_tables[eni_id].erase(stage)`、空になれば `table.erase(eni_it)` | `dashaclgroupmgr.cpp:530-534` |

### タグ attach/detach の連鎖

ルール作成時に `attachTags()` が `DashTagMgr::attach()` を呼び、タグの `m_groups` セットにグループ ID を追加する。グループ削除時に `detachTags()` が `DashTagMgr::detach()` を呼び、`m_groups` からグループ ID を除去する。`m_groups` が非空のタグへの DEL は `task_need_retry` となる。

```
ルール作成
  → attachTags(group_id, tags)
    → DashTagMgr::attach(tag_id, group_id)
      → tag.m_groups.insert(group_id)

グループ削除
  → detachTags(group_id, tags)
    → DashTagMgr::detach(tag_id, group_id)
      → tag.m_groups.erase(group_id)
```

証跡:
- `dashaclgroupmgr.cpp:558-566` (`attachTags`)
- `dashaclgroupmgr.cpp:568-576` (`detachTags`)
- `dashtagmgr.cpp:84-88` (タグ削除時の `m_groups` 非空チェック)

---

## APP_DB 書込み

`DashAclGroupMgr` は `m_dash_acl_rules_table`（`Table` オブジェクト、`APP_DASH_ACL_RULE_TABLE_NAME` 指し）をメンバーとして保持するが、コード中でこのオブジェクトへの読み書きは一切行われていない（デッドフィールド）。

DASH ACL 系のデータは APP_DB からの **読み取り専用**（ZmqOrch 経由購読）であり、APP_DB への書き戻しはない。

---

## FLEX_COUNTER_DB / COUNTERS_DB 統計

`DashAclOrch` は FlexCounter を登録しない。DASH ACL ルールの統計カウンタ（パケット数・バイト数等）ポーリングは実装されていないため、`FLEX_COUNTER_DB` および `COUNTERS_DB:COUNTERS` への書込みは発生しない。

---

## 副次書込みまとめ

| DB | 書込みの有無 | 備考 |
|----|-----------|------|
| ASIC_DB | あり（syncd 経由） | SAI DASH ACL / ENI 属性 |
| STATE_DB | **なし** | DASH ACL 固有のステータステーブルは未実装 |
| COUNTERS_DB | あり（CRM カウンタ） | `CRM_DASH_IPV{4,6}_ACL_{GROUP,RULE}` |
| FLEX_COUNTER_DB | **なし** | FlexCounter 未登録 |
| APP_DB | **なし**（書き戻し不要） | 購読のみ |
