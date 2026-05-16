# ACL_TABLE SET/DEL 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/aclorch.cpp`, `sonic-swss/orchagent/aclorch.h`, `sonic-swss-common/common/schema.h`

## AclOrch (orchagent/aclorch.cpp)

CONFIG_DB の `ACL_TABLE` を直接購読し、`doAclTableTask()` で処理する。cfgmgr 中間層はない。

### SET — ACL_TABLE|<table_name>

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_aclTableStateTable.set(table_name, [{status}])` | STATE_DB / `ACL_TABLE_TABLE` | `<table_name>` field=`status` | addAclTable() 成功 → `"Active"` |
| `m_aclTableStateTable.set(table_name, [{status}])` | STATE_DB / `ACL_TABLE_TABLE` | `<table_name>` field=`status` | addAclTable() 失敗 (retry) → `"Pending creation"` |
| `m_aclTableStateTable.set(table_name, [{status}])` | STATE_DB / `ACL_TABLE_TABLE` | `<table_name>` field=`status` | bAllAttributesOk=false / validate()=false → `"Inactive"` |
| `m_aclStageCapabilityTable.set(stage_str, fvVector)` | STATE_DB / `ACL_STAGE_CAPABILITY_TABLE` | `"INGRESS"` または `"EGRESS"` | AclOrch 初期化時 SAI capability query 後 (常時: 起動時 1 回) |

STATE_DB `ACL_STAGE_CAPABILITY_TABLE` に書き込まれるフィールド:
- `is_action_list_mandatory` (string `"true"`/`"false"`) — SAI が action list mandatory を要求するか
- `action_list` (string, カンマ区切り SAI action type 名) — ASIC がサポートする ACL action 一覧
- `supported_L3V4V6` (string `"true"`/`"false"`) — L3V4V6 デュアルスタック ACL ASIC サポート有無

SAI 呼び出し (ASIC_DB へ反映):
- `sai_acl_api->create_acl_table(&m_oid, ...)` — ACL テーブル OID 生成
- `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS_ACL / EGRESS_ACL)` — ポートバインド

CRM カウンタ更新:
- `gCrmOrch->incCrmAclUsedCounter(CRM_ACL_TABLE, stage, bpointType)` — テーブル作成時 (`aclorch.cpp:2855`)

### DEL — ACL_TABLE|<table_name>

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_aclTableStateTable.del(table_name)` | STATE_DB / `ACL_TABLE_TABLE` | `<table_name>` | removeAclTable() 成功時 |
| `m_aclTableStateTable.set(table_name, [{status:"Pending removal"}])` | STATE_DB / `ACL_TABLE_TABLE` | `<table_name>` field=`status` | removeAclTable() 失敗 (retry) |

SAI 呼び出し:
- `sai_acl_api->remove_acl_table(m_oid)` — ACL テーブル削除

CRM カウンタ更新:
- `gCrmOrch->decCrmAclUsedCounter(CRM_ACL_TABLE, stage, bpointType, oid)` — テーブル削除時 (`aclorch.cpp:4877`)

### AclOrch 初期化時 (起動/再起動)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_aclTableStateTable.del(key)` (全件) | STATE_DB / `ACL_TABLE_TABLE` | 全キー | `init()` 冒頭の `removeAllAclTableStatus()` |
| `m_aclRuleStateTable.del(key)` (全件) | STATE_DB / `ACL_RULE_TABLE` | 全キー | `init()` 冒頭の `removeAllAclRuleStatus()` |
| `m_aclStageCapabilityTable.set(stage, fvVector)` | STATE_DB / `ACL_STAGE_CAPABILITY_TABLE` | `"INGRESS"`, `"EGRESS"` | SAI capability query 完了後 |

---

## ACL_RULE と COUNTERS_DB の連動

ACL_TABLE に紐づく ACL_RULE が SAI ACL エントリとして登録される際に COUNTERS_DB への書込みが発生する。
ACL_TABLE 自体の SET/DEL が間接的にトリガーとなる (table 削除時はルールも削除)。

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_countersDb.hset(ACL_COUNTER_RULE_MAP, ruleId, counterOidStr)` | COUNTERS_DB / `ACL_COUNTER_RULE_MAP` | `<table_name>:<rule_name>` → counter OID | ACL_RULE 作成時 `registerFlexCounter()` |
| `m_countersDb.hdel(ACL_COUNTER_RULE_MAP, ruleId)` | COUNTERS_DB / `ACL_COUNTER_RULE_MAP` | `<table_name>:<rule_name>` | ACL_RULE 削除時 `deregisterFlexCounter()` |
| FlexCounter 登録 `m_flex_counter_manager.setCounterIdList(counterOid, ACL_COUNTER, ...)` | FLEX_COUNTER_DB / `ACL_STAT_COUNTER` | counter OID | ACL_RULE 作成時 |
| FlexCounter 解除 `m_flex_counter_manager.clearCounterIdList(counterOid)` | FLEX_COUNTER_DB / `ACL_STAT_COUNTER` | counter OID | ACL_RULE 削除時 |
| `gCrmOrch->incCrmAclTableUsedCounter(CRM_ACL_ENTRY, table_oid)` | COUNTERS_DB / CRM | テーブル OID 配下 | ACL_RULE 作成時 (`aclorch.cpp:1361`) |
| `gCrmOrch->decCrmAclTableUsedCounter(CRM_ACL_ENTRY, table_oid)` | COUNTERS_DB / CRM | テーブル OID 配下 | ACL_RULE 削除時 (`aclorch.cpp:1434`) |
| `gCrmOrch->incCrmAclTableUsedCounter(CRM_ACL_COUNTER, table_oid)` | COUNTERS_DB / CRM | テーブル OID 配下 | ACL counter 生成時 (`aclorch.cpp:1940`) |
| `gCrmOrch->decCrmAclTableUsedCounter(CRM_ACL_COUNTER, table_oid)` | COUNTERS_DB / CRM | テーブル OID 配下 | ACL counter 削除時 (`aclorch.cpp:1982`) |

---

## STATE_DB スキーマまとめ

| テーブル名定数 | 実テーブル名 | スキーマ定義箇所 |
|---|---|---|
| `STATE_ACL_TABLE_TABLE_NAME` | `ACL_TABLE_TABLE` | `sonic-swss-common/common/schema.h:514` |
| `STATE_ACL_RULE_TABLE_NAME` | `ACL_RULE_TABLE` | `sonic-swss-common/common/schema.h:515` |
| `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` | `ACL_STAGE_CAPABILITY_TABLE` | `sonic-swss-common/common/schema.h:418` |

COUNTERS_DB:
| 定数 | 実テーブル名 | スキーマ定義箇所 |
|---|---|---|
| `COUNTERS_ACL_COUNTER_RULE_MAP` | `ACL_COUNTER_RULE_MAP` | `sonic-swss/orchagent/aclorch.cpp:45` |
| `ACL_COUNTER_FLEX_COUNTER_GROUP` | `ACL_STAT_COUNTER` (FlexCounter グループ名) | `sonic-swss/orchagent/aclorch.h:116` |

確認コマンド:
```bash
sonic-db-cli STATE_DB hgetall 'ACL_TABLE_TABLE|<table_name>'
sonic-db-cli STATE_DB hgetall 'ACL_STAGE_CAPABILITY_TABLE|INGRESS'
sonic-db-cli COUNTERS_DB hgetall ACL_COUNTER_RULE_MAP
```
