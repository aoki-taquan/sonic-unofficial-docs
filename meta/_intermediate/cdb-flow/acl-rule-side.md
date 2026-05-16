# ACL_RULE SET/DEL 副次 DB 書込 分析 (Phase F)

生成日: 2026-05-15
ソース:
- `sonic-swss/orchagent/aclorch.cpp` — `AclOrch::doAclRuleTask()`, `AclOrch::setAclRuleStatus()`, `AclOrch::removeAclRuleStatus()`, `AclOrch::registerFlexCounter()`, `AclOrch::deregisterFlexCounter()`
- `sonic-swss/orchagent/aclorch.h` — 定数定義
- `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp` — `FlexCounterManager::setCounterIdList()`, `clearCounterIdList()`
- `sonic-swss/orchagent/saihelper.cpp` — `startFlexCounterPolling()` / `stopFlexCounterPolling()`
- `sonic-swss-common/common/schema.h` — `STATE_ACL_RULE_TABLE_NAME`, `FLEX_COUNTER_DB` 定義

---

## AclOrch (orchagent/aclorch.cpp)

`AclOrch` は CONFIG_DB の `ACL_RULE` テーブルを直接購読する（cfgmgr 中間層なし）。
SAI 呼び出し後、3 種類の DB に副次書き込みが発生する。

### SET (ACL_RULE|<table>|<rule>)

#### 1. STATE_DB / `ACL_RULE_TABLE`

ルール作成 / 検証ステータスを `STATE_DB` の `ACL_RULE_TABLE` テーブルに書き込む。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_aclRuleStateTable.set(table_name + "\|" + rule_name, {{"status", value}})` | STATE_DB / `ACL_RULE_TABLE` | `<table_name>\|<rule_name>` field=`status` | `"active"` | `addAclRule()` 成功時 |
| 同上 | STATE_DB / `ACL_RULE_TABLE` | `<table_name>\|<rule_name>` field=`status` | `"pending_creation"` | SAI リソース枯渇 (`isSaiStatusResourceFull`) または その他の create 失敗 |
| 同上 | STATE_DB / `ACL_RULE_TABLE` | `<table_name>\|<rule_name>` field=`status` | `"inactive"` | `bAllAttributesOk=false` / `validate()` 失敗 |

コード証跡:
- `aclorch.cpp:5670` — `setAclRuleStatus(table_id, rule_id, AclObjectStatus::ACTIVE)`
- `aclorch.cpp:5683,5690,5696` — `setAclRuleStatus(... AclObjectStatus::PENDING_CREATION)`
- `aclorch.cpp:5704` — `setAclRuleStatus(... AclObjectStatus::INACTIVE)`
- `aclorch.cpp:6101-6107` — `setAclRuleStatus()` 実装: `m_aclRuleStateTable.set(...)`
- `schema.h:515` — `#define STATE_ACL_RULE_TABLE_NAME "ACL_RULE_TABLE"`

#### 2. COUNTERS_DB / `ACL_COUNTER_RULE_MAP`

ルール用 SAI ACL counter OID を `COUNTERS_DB` のルールマップに登録する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr)` | COUNTERS_DB / `ACL_COUNTER_RULE_MAP` | `""` (hash field=`<table_name>:<rule_name>`) | counter OID 文字列 | `registerFlexCounter()` 呼び出し時（createCounter 有効かつ SAI counter 作成成功時） |

コード証跡:
- `aclorch.cpp:6040-6041` — `registerFlexCounter()` 内: `m_countersDb.hset(...)`
- `aclorch.h:45` — `#define COUNTERS_ACL_COUNTER_RULE_MAP "ACL_COUNTER_RULE_MAP"`
- `aclorch.cpp:4982` — `registerFlexCounter(*newRule)` — addAclRule 成功後に呼び出し

キー形式: `<table_name>:<rule_name>`（`generateAclRuleIdentifierInCountersDb()`, `aclorch.cpp:6051-6054`）

#### 3. FLEX_COUNTER_DB / `ACL_STAT_COUNTER:<counter_oid>`

ACL stat counter の flex counter ポーリングを登録する。

| 操作 | 対象 DB / テーブル | キー / フィールド | 値 | 条件 |
|------|--------------------|-----------------|-----|------|
| `m_flex_counter_manager.setCounterIdList(counter_oid, CounterType::ACL_COUNTER, attrs)` → `startFlexCounterPolling()` → `gFlexCounterTable->set(key, fvTuples)` | FLEX_COUNTER_DB / `ACL_STAT_COUNTER:<counter_oid>` | `<oid>` | `ACL_COUNTER_ATTR_ID_LIST=<attr_list>` | createCounter 有効かつ SAI counter 作成成功時 |

コード証跡:
- `aclorch.cpp:6040` — `m_flex_counter_manager.setCounterIdList(rule.getCounterOid(), CounterType::ACL_COUNTER, ...)`
- `aclorch.h:116` — `#define ACL_COUNTER_FLEX_COUNTER_GROUP "ACL_STAT_COUNTER"`
- `flex_counter_manager.cpp:50` — `{ CounterType::ACL_COUNTER, ACL_COUNTER_ATTR_ID_LIST }`
- `saihelper.cpp:1047` — `gFlexCounterTable->set(key, fvTuples)`
- `schema.h:18` — `#define FLEX_COUNTER_DB 5`

キー形式: `ACL_STAT_COUNTER:<oid>` (`getFlexCounterTableKey()`: `group_name + ":" + sai_serialize_object_id(object_id)`)

#### createCounter の条件

- `AclRulePacket` (L3/L3V6 テーブルの通常ルール): `createCounter=true`（デフォルト）
- `AclRuleMirror` (MIRROR テーブル): `createCounter=false`（デフォルト）— `AclRuleMirror::createCounter()` は `getCreateCounter()` が false の場合は SAI counter を作らず、`registerFlexCounter` も呼ばれない

コード証跡:
- `aclorch.cpp:2295-2306` — `AclRuleMirror::createCounter()`
- `aclorch.cpp:275` (デフォルト値)

---

### DEL (ACL_RULE|<table>|<rule>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|--------------------|-----------------|------|
| `m_aclRuleStateTable.del(table_name + "\|" + rule_name)` | STATE_DB / `ACL_RULE_TABLE` | `<table_name>\|<rule_name>` | `removeAclRule()` 成功時 |
| `m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier)` | COUNTERS_DB / `ACL_COUNTER_RULE_MAP` | field=`<table_name>:<rule_name>` | `deregisterFlexCounter()` 呼び出し時 |
| `m_flex_counter_manager.clearCounterIdList(counter_oid)` → `stopFlexCounterPolling()` → `gFlexCounterTable->del(key)` | FLEX_COUNTER_DB / `ACL_STAT_COUNTER:<counter_oid>` | `<oid>` | `deregisterFlexCounter()` 呼び出し時 |

コード証跡:
- `aclorch.cpp:5713` — `removeAclRuleStatus(table_id, rule_id)`
- `aclorch.cpp:6109-6113` — `removeAclRuleStatus()` 実装
- `aclorch.cpp:5019` — `deregisterFlexCounter(*rule)` — removeAclRule 成功後
- `aclorch.cpp:6044-6048` — `deregisterFlexCounter()` 実装

---

## 副次 DB 書込なし（スコープ外）

- **APPL_DB**: `ACL_RULE` は cfgmgr 中間層がなく、CONFIG_DB を `AclOrch` が直接購読する。APPL_DB への書き込みは発生しない（`runtime-trace` ブロック参照）。
- **ASIC_DB**: SAI 呼び出し経由で syncd が書き込む（orchagent の直接 DB 書込ではない）。

---

## 全体サマリ

| 副次書込先 DB | テーブル | トリガ |
|---|---|---|
| STATE_DB | `ACL_RULE_TABLE` | SET/DEL 操作でステータス管理（active / pending_creation / inactive / 削除） |
| COUNTERS_DB | `ACL_COUNTER_RULE_MAP` | ルール作成時に counter OID マッピングを登録、削除時にクリア |
| FLEX_COUNTER_DB | `ACL_STAT_COUNTER:<oid>` | ルール作成時に ACL stat counter ポーリング登録、削除時にクリア |
