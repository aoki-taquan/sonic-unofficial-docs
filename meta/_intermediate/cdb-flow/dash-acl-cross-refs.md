# dash-acl cross-refs (Phase C) 調査トレース

## 調査対象

- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashaclgroupmgr.cpp`
- `sonic-swss/orchagent/dash/dashaclgroupmgr.h`

## 外部テーブル参照の洗い出し

### DASH_ENI_TABLE (DashOrch::getEni)

`dashaclgroupmgr.cpp:457` `bind()` 内:
```cpp
auto eni = m_dash_orch->getEni(eni_id);
if (!eni)
    return task_need_retry;
```

`dashaclgroupmgr.cpp:506` `unbind()` 内:
```cpp
auto eni_entry = m_dash_orch->getEni(eni_id);
```

→ DASH_ACL_IN/OUT_TABLE の SET 処理(バインド)は DASH_ENI_TABLE エントリの存在を必須とする。未登録なら `task_need_retry`。

### DASH_ACL_GROUP_TABLE (m_groups_table)

`dashaclgroupmgr.cpp:385-390` `createRule()` 内:
```cpp
auto group_it = m_groups_table.find(group_id);
if (group_it == m_groups_table.end())
    return task_need_retry;
```

`dashaclgroupmgr.cpp:442-446` `bind()` 内:
```cpp
auto group_it = m_groups_table.find(group_id);
if (group_it == m_groups_table.end())
    return task_failed;
```

→ DASH_ACL_RULE_TABLE のルール作成は対応グループが存在しなければ `task_need_retry`。
→ DASH_ACL_IN/OUT_TABLE のバインドは対応グループが存在しなければ `task_failed`。

### DASH_PREFIX_TAG_TABLE (DashAclTagMgr::exists)

`dashaclgroupmgr.cpp:393-408`:
```cpp
for (const auto& tag_id : rule.m_src_tags)
{
    if (!m_dash_acl_orch->getDashAclTagMgr().exists(tag_id))
        return task_need_retry;
}
for (const auto& tag_id : rule.m_dst_tags)
{
    if (!m_dash_acl_orch->getDashAclTagMgr().exists(tag_id))
        return task_need_retry;
}
```

→ DASH_ACL_RULE_TABLE で `src_tag` / `dst_tag` を指定した場合、対応する DASH_PREFIX_TAG_TABLE エントリが存在しなければ `task_need_retry`。

### CrmOrch (gCrmOrch)

`dashaclgroupmgr.cpp:372-376`:
```cpp
CrmResourceType crm_rtype = group.m_ip_version == DashAclGroupMgr::IpVersion::IPV4 ?
    CrmResourceType::CRM_DASH_IPV4_ACL_RULE : CrmResourceType::CRM_DASH_IPV6_ACL_RULE;
gCrmOrch->incCrmDashAclUsedCounter(crm_rtype, group.m_dash_acl_group_id);
```

→ ACL ルール作成成功時に CRM (Critical Resource Management) カウンタをインクリメント。
  CrmOrch はプロセス内グローバル (`extern CrmOrch *gCrmOrch`)。

### 被参照（他テーブルからの参照）

- `DASH_ACL_IN/OUT_TABLE` は `DASH_ENI_TABLE` の ENI に対してバインドするため、ENI 削除時に影響を受ける（ENI 削除前に ACL バインドを解除する必要がある）。
- `DashAclGroupMgr::isBound()` がバインド中チェックに使用される — `dashaclgroupmgr.cpp:234`。

## 結論

| 参照先テーブル / リソース | 方向 | 条件 | ソース |
|---|---|---|---|
| `DASH_ENI_TABLE` | OID 解決（必須） | `DASH_ACL_IN/OUT_TABLE` バインド時。ENI 未登録 → `task_need_retry` | `dashaclgroupmgr.cpp:457,461` |
| `DASH_ACL_GROUP_TABLE` | OID 解決（必須） | `DASH_ACL_RULE_TABLE` ルール作成時。グループ未作成 → `task_need_retry` | `dashaclgroupmgr.cpp:385-390` |
| `DASH_ACL_GROUP_TABLE` | OID 解決（必須） | `DASH_ACL_IN/OUT_TABLE` バインド時。グループ未作成 → `task_failed` | `dashaclgroupmgr.cpp:442-446` |
| `DASH_PREFIX_TAG_TABLE` | タグ存在確認（条件付き） | `DASH_ACL_RULE_TABLE` で `src_tag`/`dst_tag` 指定時。タグ未登録 → `task_need_retry` | `dashaclgroupmgr.cpp:393-408` |
| CrmOrch (`gCrmOrch`) | リソースカウンタ | ACL ルール SAI 作成成功時 (`incCrmDashAclUsedCounter`) | `dashaclgroupmgr.cpp:372-376` |
