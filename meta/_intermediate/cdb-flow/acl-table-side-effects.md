# ACL_TABLE — 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/aclorch.cpp`, `sonic-swss/orchagent/aclorch.h`, `sonic-swss-common/common/schema.h`

## AclOrch (orchagent/aclorch.cpp)

CONFIG_DB の `ACL_TABLE` を直接購読し、`doAclTableTask()` で処理する。cfgmgr 中間層はない。

---

## ASIC_DB 書込み (SAI 経由)

ACL_TABLE の SET は SAI ACL table 作成を引き起こし、syncd が ASIC_DB に OID を記録する。

| タイミング | SAI API | ASIC_DB への反映 |
|---|---|---|
| `addAclTable()` 成功 | `sai_acl_api->create_acl_table(&m_oid, ...)` | `ASIC_DB:ASIC_STATE:SAI_OBJECT_TYPE_ACL_TABLE:<oid>` 生成 |
| ポートバインド (`AclTable::bind()`) | `gPortsOrch->bindAclTable(portOid, m_oid, ...)` → `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS_ACL / EGRESS_ACL)` | `ASIC_DB:ASIC_STATE:SAI_OBJECT_TYPE_PORT:<port_oid>` の ACL 属性更新 |
| ポートアンバインド (`AclTable::unbind()`) | `gPortsOrch->unbindAclTable(portOid, m_oid, ...)` | 対応 PORT OID の ACL 属性クリア |
| `removeAclTable()` 成功 | `sai_acl_api->remove_acl_table(m_oid)` | `ASIC_DB:ASIC_STATE:SAI_OBJECT_TYPE_ACL_TABLE:<oid>` 削除 |

証跡: `aclorch.cpp:2847` (`create_acl_table`), `aclorch.cpp:2920` (`bindAclTable`), `aclorch.cpp:2938` (`unbindAclTable`)

---

## STATE_DB 書込み

### ACL_TABLE_TABLE (テーブル status)

テーブル名定数: `STATE_ACL_TABLE_TABLE_NAME` = `"ACL_TABLE_TABLE"` (`schema.h:514`)

| タイミング | キー | フィールド | 値 |
|---|---|---|---|
| SET → `addAclTable()` 成功 | `<table_name>` | `status` | `"Active"` |
| SET → `addAclTable()` 失敗 (retry) | `<table_name>` | `status` | `"Pending creation"` |
| SET → `bAllAttributesOk=false` or `validate()=false` | `<table_name>` | `status` | `"Inactive"` |
| DEL → `removeAclTable()` 失敗 (retry) | `<table_name>` | `status` | `"Pending removal"` |
| DEL → `removeAclTable()` 成功 | `<table_name>` | — | エントリ削除 (`m_aclTableStateTable.del()`) |
| AclOrch 起動時 `init()` | 全キー | — | 全エントリ一括削除 (`removeAllAclTableStatus()`) |

証跡: `setAclTableStatus()` L6088-6093, `removeAclTableStatus()` L6096-6099, `removeAllAclTableStatus()` L6119-6125

### ACL_STAGE_CAPABILITY_TABLE (ASIC 能力)

テーブル名定数: `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` = `"ACL_STAGE_CAPABILITY_TABLE"` (`schema.h:418`)

| タイミング | キー | フィールド | 値 |
|---|---|---|---|
| AclOrch 起動時 SAI capability query 後 (`putAclActionCapabilityInDB()`) | `"INGRESS"` / `"EGRESS"` | `is_action_list_mandatory` | `"true"` / `"false"` |
| 同上 | `"INGRESS"` / `"EGRESS"` | `action_list` | カンマ区切り SAI action type 名 |
| 同上 | `"INGRESS"` / `"EGRESS"` | `supported_L3V4V6` | `"true"` / `"false"` |

証跡: `putAclActionCapabilityInDB()` L4056-4101, `m_aclStageCapabilityTable.set()` L4101

```bash
# 確認コマンド
sonic-db-cli STATE_DB hgetall 'ACL_TABLE_TABLE|<table_name>'
sonic-db-cli STATE_DB hgetall 'ACL_STAGE_CAPABILITY_TABLE|INGRESS'
```

---

## COUNTERS_DB 書込み

### ACL_COUNTER_RULE_MAP (ルール OID マッピング)

定数: `COUNTERS_ACL_COUNTER_RULE_MAP` = `"ACL_COUNTER_RULE_MAP"` (`aclorch.cpp:45`)

ACL_TABLE 自体は COUNTERS_DB に直接書き込まない。ただし ACL_TABLE に紐づく ACL_RULE の作成/削除時に連動する。

| タイミング | 操作 | キー | 値 |
|---|---|---|---|
| ACL_RULE 作成 (`registerFlexCounter()`) | `m_countersDb.hset(ACL_COUNTER_RULE_MAP, ruleId, counterOidStr)` | `<table_name>:<rule_name>` | SAI counter OID (hex 文字列) |
| ACL_RULE 削除 (`deregisterFlexCounter()`) | `m_countersDb.hdel(ACL_COUNTER_RULE_MAP, ruleId)` | `<table_name>:<rule_name>` | — (削除) |

証跡: `registerFlexCounter()` L6020-6042, `deregisterFlexCounter()` L6044-6048

### CRM カウンタ (COUNTERS_DB 経由)

| タイミング | CRM 操作 | ソース行 |
|---|---|---|
| ACL テーブル作成 (`addAclTable()` 成功) | `gCrmOrch->incCrmAclUsedCounter(CRM_ACL_TABLE, stage, bpointType)` | `aclorch.cpp:2855` |
| ACL テーブル削除 (`removeAclTable()` 成功) | `gCrmOrch->decCrmAclUsedCounter(CRM_ACL_TABLE, stage, bpointType, oid)` | `aclorch.cpp:4877` |
| ACL_RULE 作成 | `gCrmOrch->incCrmAclTableUsedCounter(CRM_ACL_ENTRY, table_oid)` | `aclorch.cpp:1361` |
| ACL_RULE 削除 | `gCrmOrch->decCrmAclTableUsedCounter(CRM_ACL_ENTRY, table_oid)` | `aclorch.cpp:1434` |
| ACL counter 生成 (`createCounter()`) | `gCrmOrch->incCrmAclTableUsedCounter(CRM_ACL_COUNTER, table_oid)` | `aclorch.cpp:1940` |
| ACL counter 削除 (`removeCounter()`) | `gCrmOrch->decCrmAclTableUsedCounter(CRM_ACL_COUNTER, table_oid)` | `aclorch.cpp:1982` |

### FlexCounter (ACL stats ポーリング)

| タイミング | 操作 | 対象 |
|---|---|---|
| ACL_RULE 作成 | `m_flex_counter_manager.setCounterIdList(counterOid, ACL_COUNTER, ...)` | `FLEX_COUNTER_DB / ACL_STAT_COUNTER` グループへ counter OID 登録 |
| ACL_RULE 削除 | `m_flex_counter_manager.clearCounterIdList(counterOid)` | `FLEX_COUNTER_DB / ACL_STAT_COUNTER` からエントリ削除 |

FlexCounter デーモンが定期的に SAI ACL カウンタをポーリングし、`COUNTERS_DB / COUNTERS` に統計値を書き込む。

定数: `ACL_COUNTER_FLEX_COUNTER_GROUP` = `"ACL_STAT_COUNTER"` (`aclorch.h:116`)

```bash
# 確認コマンド
sonic-db-cli COUNTERS_DB hgetall ACL_COUNTER_RULE_MAP
```

---

## スキーマまとめ

| DB | テーブル名 | 定数 | 定義箇所 |
|---|---|---|---|
| STATE_DB | `ACL_TABLE_TABLE` | `STATE_ACL_TABLE_TABLE_NAME` | `schema.h:514` |
| STATE_DB | `ACL_RULE_TABLE` | `STATE_ACL_RULE_TABLE_NAME` | `schema.h:515` |
| STATE_DB | `ACL_STAGE_CAPABILITY_TABLE` | `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` | `schema.h:418` |
| COUNTERS_DB | `ACL_COUNTER_RULE_MAP` | `COUNTERS_ACL_COUNTER_RULE_MAP` | `aclorch.cpp:45` |
| FLEX_COUNTER_DB | `ACL_STAT_COUNTER` | `ACL_COUNTER_FLEX_COUNTER_GROUP` | `aclorch.h:116` |
