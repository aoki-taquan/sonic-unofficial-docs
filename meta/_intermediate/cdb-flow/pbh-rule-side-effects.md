# Phase F: PBH_RULE 副次 DB 書込スキャン

`docs/reference/config-db/pbh-rule.md` の Phase F (副次 DB 書込) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/pbhorch.cpp`、`sonic-net/sonic-swss/orchagent/aclorch.cpp`、`sonic-net/sonic-swss/orchagent/pbh/pbhrule.h`。

## スキャン手順

```bash
# pbhorch の createPbhRule / updatePbhRule / removePbhRule を確認
grep -n "addAclRule\|removeAclRule\|setAclRuleStatus\|STATE\|COUNTERS\|FLEX" \
    .cache/sonic-sources/sonic-swss/orchagent/pbhorch.cpp

# aclorch の addAclRule / registerFlexCounter / setAclRuleStatus を確認
grep -n "registerFlexCounter\|m_countersDb\|m_aclRuleStateTable\|setAclRuleStatus" \
    .cache/sonic-sources/sonic-swss/orchagent/aclorch.cpp

# AclRulePbh のデフォルト createCounter 値を確認
grep -n "AclRulePbh(" \
    .cache/sonic-sources/sonic-swss/orchagent/pbh/pbhrule.h
```

## スキャン結果

### STATE_DB / ACL_RULE_TABLE — PBH では書き込まれない

`setAclRuleStatus()` (`aclorch.cpp:6102`) は `AclOrch::doTask()` の汎用 ACL_RULE 処理経路 (`aclorch.cpp:5668-5726`) からのみ呼ばれる。`PBH_RULE` は `PbhOrch` の独立した処理経路を使い (`pbhorch.cpp:479-654`)、`addAclRule()` を直接呼ぶが `setAclRuleStatus()` は呼ばない。

→ **STATE_DB への書き込みなし**。

### COUNTERS_DB / ACL_COUNTER_RULE_MAP — flow_counter=ENABLED 時のみ

`AclRulePbh` のデフォルト `createCounter = false` (`pbhrule.h:8`)。

`flow_counter=ENABLED` が CONFIG_DB に設定されている場合:
```cpp
// pbhorch.cpp:493-495
if (rule.flow_counter.is_set) {
    pbhRule = std::make_shared<AclRulePbh>(
        this->aclOrch, rule.name, rule.table, rule.flow_counter.value);
    // flow_counter.value が "ENABLED" → createCounter=true
}
```

`addAclRule()` (`aclorch.cpp:4980-4983`) が `newRule->hasCounter()` を確認し、`createCounter=true` なら `registerFlexCounter()` を呼ぶ:
```cpp
// aclorch.cpp:6041
m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr);
```
- `COUNTERS_ACL_COUNTER_RULE_MAP = "ACL_COUNTER_RULE_MAP"` (`aclorch.h:45`)
- `ruleIdentifier = rule.table + ":" + rule.name` (`aclorch.cpp:6053`)
- DEL 時: `m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier)` (`aclorch.cpp:6047`)

### FLEX_COUNTER_DB / ACL_STAT_COUNTER — flow_counter=ENABLED 時のみ

`registerFlexCounter()` → `m_flex_counter_manager.setCounterIdList(oid, CounterType::ACL_COUNTER, attrs)` → FLEX_COUNTER_DB に書き込み。

- グループ名: `ACL_COUNTER_FLEX_COUNTER_GROUP = "ACL_STAT_COUNTER"` (`aclorch.h:116`)
- キー形式: `ACL_STAT_COUNTER:<counter_oid>`
- フィールド: `ACL_COUNTER_ATTR_ID_LIST=<SAI_ACL_COUNTER attrs>`
- DEL 時: `m_flex_counter_manager.clearCounterIdList(oid)` (`aclorch.cpp:6048`)

## 検出まとめ

| DB | テーブル名 | 条件 | 操作 | evidence |
|-----|---------|------|------|---------|
| STATE_DB | `ACL_RULE_TABLE` | — | **書き込みなし** (PBH_RULE は汎用 ACL_RULE パスを通らない) | pbhorch.cpp:633, aclorch.cpp:5668-5726 |
| COUNTERS_DB | `ACL_COUNTER_RULE_MAP` | `flow_counter=ENABLED` | `hset` (SET 時) / `hdel` (DEL 時) | aclorch.cpp:6041,6047 |
| FLEX_COUNTER_DB | `ACL_STAT_COUNTER` | `flow_counter=ENABLED` | `set` (SET 時) / `del` (DEL 時) | aclorch.cpp:6040,6048 |
| APPL_DB | — | — | **書き込みなし** | — |
| ASIC_DB | — | SAI 経由のみ | syncd が書き込む（orchagent 直接書込なし） | — |

このスキャン結果から派生して `docs/reference/config-db/pbh-rule.md` の `<!-- side-effects -->` ブロックを生成する。
