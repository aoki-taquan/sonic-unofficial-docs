# PBH_TABLE / PBH_RULE — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: sonic-swss/orchagent/pbhorch.cpp, pbhrule.cpp, aclorch.cpp (L6020-6053)

<!-- side-effects -->
## Phase F: 副次 DB 書込 (Side-Effects)

### ASIC_DB への書込

PBH エントリの設定は PbhOrch → AclOrch → SAI API 経路で ASIC_DB に反映される。直接の ASIC_DB 書込は syncd が行う。

| 操作 | SAI API | ASIC_DB オブジェクト型 | 契機 |
|---|---|---|---|
| PBH_TABLE ADD | `aclOrch->addAclTable()` → `sai_acl_api->create_acl_table()` | `SAI_OBJECT_TYPE_ACL_TABLE` | `PBH_TABLE` SET イベント |
| PBH_RULE ADD | `aclOrch->addAclRule()` → `sai_acl_api->create_acl_entry()` | `SAI_OBJECT_TYPE_ACL_ENTRY` | `PBH_RULE` SET イベント (依存 PBH_TABLE/PBH_HASH 作成済みのとき) |
| PBH_HASH ADD | `sai_hash_api->create_hash()` | `SAI_OBJECT_TYPE_HASH` | `PBH_HASH` SET イベント |
| PBH_HASH_FIELD ADD | `sai_hash_api->create_fine_grained_hash_field()` | `SAI_OBJECT_TYPE_FINE_GRAINED_HASH_FIELD` | `PBH_HASH_FIELD` SET イベント |
| flow_counter=ENABLED | `sai_acl_api->create_acl_counter()` | `SAI_OBJECT_TYPE_ACL_COUNTER` | `PBH_RULE` で `flow_counter=ENABLED` 時のみ |

証跡:
- `pbhorch.cpp:286` — `aclOrch->addAclTable(pbhTable)`
- `pbhorch.cpp:633` — `aclOrch->addAclRule(pbhRule, rule.table)`
- `pbhorch.cpp:1054` — `sai_hash_api->create_hash()`
- `aclorch.cpp:1937` — `sai_acl_api->create_acl_counter()`

### COUNTERS_DB への書込

`flow_counter=ENABLED` の PBH_RULE は AclOrch::registerFlexCounter() を通じて COUNTERS_DB に書き込む。

| COUNTERS_DB キー/ハッシュ | 内容 | 書込タイミング |
|---|---|---|
| `COUNTERS_DB:ACL_COUNTER_RULE_MAP` | `"<table_name>|<rule_name>"` → `<acl_counter_oid>` のマッピング | `flow_counter=ENABLED` の PBH_RULE が addAclRule() → createCounter() 成功後 |
| FlexCounter 登録 | `CounterType::ACL_COUNTER` として packet / byte カウンタ属性を flex_counter_manager に登録 | 同上 |

DEL (removePbhRule) 時: `aclOrch->deregisterFlexCounter()` が `COUNTERS_DB:ACL_COUNTER_RULE_MAP` からエントリを削除し、flex_counter 登録も解除する。

証跡:
- `aclorch.cpp:6041` — `m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr)`
- `aclorch.cpp:6047` — `m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier)` (DEL 時)
- `aclorch.cpp:6040` — `m_flex_counter_manager.setCounterIdList(..., CounterType::ACL_COUNTER, ...)`

### flow_counter=DISABLED (デフォルト) の場合

`AclRulePbh` は `createCounter=false` で構築される (`pbhorch.cpp:499`)。ACL_COUNTER SAI オブジェクトは作成されず、COUNTERS_DB への書込も発生しない。

### 副次書込サマリ

```
PBH_RULE (flow_counter=ENABLED)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_ENTRY (via sai_acl_api->create_acl_entry)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_COUNTER (via sai_acl_api->create_acl_counter)
  └─► COUNTERS_DB: ACL_COUNTER_RULE_MAP["<table>|<rule>"] = <counter_oid>
  └─► FlexCounter: CounterType::ACL_COUNTER 登録 (show pbh statistics に表示)

PBH_RULE (flow_counter=DISABLED / デフォルト)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_ENTRY のみ
  └─► COUNTERS_DB: 書込なし
```

<!-- /side-effects -->
