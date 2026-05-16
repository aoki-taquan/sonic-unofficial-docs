# ACL_RULE — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: `sonic-swss/orchagent/aclorch.cpp` (`AclOrch::registerFlexCounter`, `AclOrch::deregisterFlexCounter`, `AclOrch::setAclRuleStatus`, `AclOrch::removeAclRuleStatus`)

---

## 概要

`ACL_RULE` の SET/DEL 処理後に `AclOrch` が書き込む副次 DB は以下の 3 つ。

| DB | テーブル / キー | トリガ |
|----|----------------|--------|
| STATE_DB | `ACL_RULE_TABLE\|<table>\|<rule>` | SET/DEL でステータス管理 |
| COUNTERS_DB | `ACL_COUNTER_RULE_MAP` (hash field) | counter OID マッピング登録/削除 |
| FLEX_COUNTER_DB | `ACL_STAT_COUNTER:<counter_oid>` | ACL stat counter ポーリング登録/解除 |

---

## 1. STATE_DB / `ACL_RULE_TABLE`

`AclOrch::setAclRuleStatus()` / `removeAclRuleStatus()` が書き込む。

### SET トリガ

| 状態 | `status` 値 | evidence |
|------|------------|----------|
| `addAclRule()` 成功 | `"active"` | `aclorch.cpp:5670` |
| SAI リソース枯渇 (isSaiStatusResourceFull) | `"pending_creation"` | `aclorch.cpp:5683,5690` |
| その他 create 失敗 | `"pending_creation"` | `aclorch.cpp:5696` |
| `bAllAttributesOk=false` / `validate()` 失敗 | `"inactive"` | `aclorch.cpp:5704` |

### DEL トリガ

`removeAclRule()` 成功時に `m_aclRuleStateTable.del(...)` でエントリ削除。`aclorch.cpp:5713`

定数: `STATE_ACL_RULE_TABLE_NAME = "ACL_RULE_TABLE"` (`schema.h:515`)

---

## 2. COUNTERS_DB / `ACL_COUNTER_RULE_MAP`

`AclOrch::registerFlexCounter()` が `m_countersDb.hset()` で書き込む。

```cpp
// aclorch.cpp:6041
m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr);
```

- **hash フィールド形式**: `<table_name>:<rule_name>` (`generateAclRuleIdentifierInCountersDb()`, `aclorch.cpp:6051-6054`)
- **値**: SAI counter OID をシリアライズした文字列

### DEL

`deregisterFlexCounter()` が `m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier)` で削除。`aclorch.cpp:6047`

定数: `COUNTERS_ACL_COUNTER_RULE_MAP = "ACL_COUNTER_RULE_MAP"` (`aclorch.h:45`)

### createCounter フラグ

- `AclRulePacket` (L3/L3V6): `createCounter=true`（デフォルト）→ 登録される
- `AclRuleMirror` (MIRROR): `createCounter=false`（デフォルト）→ 登録されない (`aclorch.cpp:2295-2306`)

---

## 3. FLEX_COUNTER_DB / `ACL_STAT_COUNTER:<counter_oid>`

`AclOrch::registerFlexCounter()` → `FlexCounterManager::setCounterIdList()` → `startFlexCounterPolling()` → `gFlexCounterTable->set(key, fvTuples)` の経路で書き込まれる。

```cpp
// aclorch.cpp:6040
m_flex_counter_manager.setCounterIdList(rule.getCounterOid(), CounterType::ACL_COUNTER, serializedCounterStatAttrs);
```

- **キー**: `ACL_STAT_COUNTER:<oid>` (`ACL_COUNTER_FLEX_COUNTER_GROUP + ":" + sai_serialize_object_id(oid)`)
- **フィールド**: `ACL_COUNTER_ATTR_ID_LIST` = `SAI_ACL_COUNTER_ATTR_BYTES`, `SAI_ACL_COUNTER_ATTR_PACKETS`

### DEL

`deregisterFlexCounter()` → `FlexCounterManager::clearCounterIdList()` → `gFlexCounterTable->del(key)` で削除。`aclorch.cpp:6048`

定数: `ACL_COUNTER_FLEX_COUNTER_GROUP = "ACL_STAT_COUNTER"` (`aclorch.h:116`)
DB 番号: `FLEX_COUNTER_DB = 5` (`schema.h:18`)

### 初期状態

`ACL_COUNTER_DEFAULT_ENABLED_STATE = false` (`aclorch.cpp:48`) のため、起動直後はポーリング無効。
`counterpoll acl enable` で有効化するまで stats は収集されない。

---

## 副次書込なし（スコープ外）

- **APPL_DB**: `AclOrch` は CONFIG_DB を直接購読（cfgmgr 中間層なし）。APPL_DB 書き込みは発生しない。
- **ASIC_DB**: SAI 経由で syncd が書き込む（orchagent の直接書込なし）。

---

## 書込フロー図

```
ACL_RULE SET (CONFIG_DB)
  └─ AclOrch::doAclRuleTask()
       └─ addAclRule()
            ├─ SAI: sai_acl_api->create_acl_entry()      → ASIC_DB (syncd 経由)
            ├─ SAI: sai_acl_api->create_acl_counter()    → ASIC_DB (syncd 経由)
            ├─ setAclRuleStatus()                         → STATE_DB/ACL_RULE_TABLE
            └─ registerFlexCounter()
                 ├─ m_countersDb.hset()                   → COUNTERS_DB/ACL_COUNTER_RULE_MAP
                 └─ m_flex_counter_manager.setCounterIdList() → FLEX_COUNTER_DB/ACL_STAT_COUNTER:<oid>

ACL_RULE DEL (CONFIG_DB)
  └─ AclOrch::doAclRuleTask()
       └─ removeAclRule()
            ├─ SAI: sai_acl_api->remove_acl_entry()      → ASIC_DB (syncd 経由)
            ├─ SAI: sai_acl_api->remove_acl_counter()    → ASIC_DB (syncd 経由)
            ├─ removeAclRuleStatus()                      → STATE_DB/ACL_RULE_TABLE (del)
            └─ deregisterFlexCounter()
                 ├─ m_countersDb.hdel()                   → COUNTERS_DB/ACL_COUNTER_RULE_MAP (del)
                 └─ m_flex_counter_manager.clearCounterIdList() → FLEX_COUNTER_DB/ACL_STAT_COUNTER:<oid> (del)
```
