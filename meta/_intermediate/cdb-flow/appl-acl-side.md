# appl-acl: 副次 DB 書込（Task F Phase F）

対象ページ: `docs/reference/config-db/appl-acl.md`
ソース: `sonic-swss/orchagent/aclorch.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)、`sonic-swss-common/common/schema.h` (sha `158de8d3463ff4b841653f6d57190bb142b80d9c`)

APPL_DB 経路 (`ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE`) は CONFIG_DB 経路と同一の `AclOrch` インスタンスで処理されるため、副次 DB 書込みは CONFIG_DB 経路と共通である。本ドキュメントは APPL_DB SET / DEL が **実際に発火させる** 副次書込みのみを列挙する。

## 1. STATE_DB

`AclOrch` コンストラクタ (aclorch.cpp:4199-4202) が `stateDb` 上に 3 つの `swss::Table` を保持:

| メンバ | テーブル名 | スキーマ定数 |
|---|---|---|
| `m_aclStageCapabilityTable` | `ACL_STAGE_CAPABILITY_TABLE` | `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` (schema.h:418) |
| `m_aclTableStateTable` | `ACL_TABLE_TABLE` | `STATE_ACL_TABLE_TABLE_NAME` (schema.h:514) |
| `m_aclRuleStateTable` | `ACL_RULE_TABLE` | `STATE_ACL_RULE_TABLE_NAME` (schema.h:515) |

### 1.1 `STATE_DB|ACL_TABLE_TABLE|<table_name>`

書き込み関数: `setAclTableStatus()` (aclorch.cpp:6087-6093) / `removeAclTableStatus()` (aclorch.cpp:6096-6099)

呼出経路 (APPL_DB SET → 副次書込):

| トリガ | 呼出元 | status 値 |
|---|---|---|
| `addAclTable()` 成功 (新規) | aclorch.cpp:5462 | `ACTIVE` (`"Active"`) |
| `updateAclTable()` 成功 | aclorch.cpp:5477 | `ACTIVE` |
| `addAclTable()` SAI 失敗 | aclorch.cpp:5483 | `PENDING_CREATION` (`"Pending creation"`) |
| 属性 validate 失敗 (`bAllAttributesOk=false`) | aclorch.cpp:5492 | `INACTIVE` (`"Inactive"`) |
| APPL_DB DEL → `removeAclTable()` 成功 | aclorch.cpp:5501 (`removeAclTableStatus`) | (エントリ削除) |
| APPL_DB DEL → `removeAclTable()` 失敗 | aclorch.cpp:5508 | `PENDING_REMOVAL` (`"Pending removal"`) |

フィールド: `status` のみ。値は `aclObjectStatusLookup[]` で文字列化。

### 1.2 `STATE_DB|ACL_RULE_TABLE|<table_name>|<rule_name>`

書き込み関数: `setAclRuleStatus()` (aclorch.cpp:6102-6107) / `removeAclRuleStatus()` (aclorch.cpp:6110-6112)

呼出経路:

| トリガ | 呼出元 | status |
|---|---|---|
| `addAclRule()` 成功 | aclorch.cpp:5670 | `ACTIVE` |
| `addAclRule()` SAI resource full → retry park 成功 | aclorch.cpp:5683 | `PENDING_CREATION` |
| `addAclRule()` SAI resource full → retry park 失敗 | aclorch.cpp:5690 | `PENDING_CREATION` |
| `addAclRule()` その他失敗 (retry なし) | aclorch.cpp:5696 | `PENDING_CREATION` |
| ルール属性 validate 失敗 | aclorch.cpp:5704 | `INACTIVE` |
| APPL_DB DEL → `removeAclRule()` 失敗 | aclorch.cpp:5726 | `PENDING_REMOVAL` |

key 区切り: `setAclRuleStatus()` 内で `table_name + "|" + rule_name`（aclorch.cpp:6106）。

### 1.3 `STATE_DB|ACL_STAGE_CAPABILITY_TABLE|<stage>`

書込みは **`AclOrch::init()` 時点のみ**（起動時 1 回）で、APPL_DB SET/DEL ごとには発火しない。フィールド: `is_action_list_mandatory`, `action_list`, `supported_L3V4V6`（aclorch.cpp:4089-4097）。APPL_DB 書込みから見た副次効果ではないため本ページの副次書込み対象外。

## 2. COUNTERS_DB

`AclOrch` の static メンバ (aclorch.cpp:25-26):

```cpp
swss::DBConnector AclOrch::m_countersDb("COUNTERS_DB", 0);
swss::Table AclOrch::m_countersTable(&m_countersDb, "COUNTERS");
```

### 2.1 `COUNTERS_DB|ACL_COUNTER_RULE_MAP`

書込み関数: `registerFlexCounter()` (aclorch.cpp:6020-6042) / `deregisterFlexCounter()` (aclorch.cpp:6044-6049)

```cpp
// aclorch.cpp:6041
m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr);
// aclorch.cpp:6047
m_countersDb.hdel(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier);
```

- key: 固定文字列 `"ACL_COUNTER_RULE_MAP"` (aclorch.cpp:45)
- field: `ruleIdentifier = <table_id>:<rule_id>`（`m_countersTable.getTableNameSeparator()=":"`、aclorch.cpp:6053）
- value: SAI counter OID 文字列（`sai_serialize_object_id`）

発火経路 (APPL_DB SET 由来):

| トリガ | 呼出元 |
|---|---|
| ルール新規作成成功 (`addAclRule` 経由) | aclorch.cpp:4982 (`AclOrch::addAclRule` 内) |
| ルール更新で counter 追加 | aclorch.cpp:1515, 2444 |
| ルール削除 (`removeAclRule` 経由) | aclorch.cpp:5019, 5157, 3001, 3095 |
| ルール更新で counter 削除 | aclorch.cpp:1519 |

APPL_DB の各ルールは `m_createCounter=true` の場合のみ counter 登録される（`AclRule` コンストラクタ第 4 引数、`AclRule::createCounter()` で SAI counter OID 取得 aclorch.cpp:1911-1945）。`vnetorch` の VNET_TUNNEL_TERM ルール、`mclagsyncd` の port-isolate ルール、`dashenifwdorch` の ENI fwd ルールはいずれも `AclRulePacket` 等のデフォルト動作で counter を作成する経路に乗る（明示的 `RULE_COUNTER=false` 等の field を書かない限り）。

## 3. FLEX_COUNTER_DB

`AclOrch::m_flex_counter_manager` (aclorch.cpp:4208-4213) が `ACL_STAT_COUNTER` グループで初期化される:

```cpp
// aclorch.h:116
#define ACL_COUNTER_FLEX_COUNTER_GROUP "ACL_STAT_COUNTER"
// aclorch.cpp:47
#define ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS 10000 // ms
```

### 3.1 `FLEX_COUNTER_DB|FLEX_COUNTER_GROUP_TABLE|ACL_STAT_COUNTER`

起動時 (constructor) に `FlexCounterManager::applyGroupConfiguration()` で polling interval (10000ms) / stats mode (`READ`) / enable 状態を書込み。APPL_DB SET/DEL では発火しない（起動 1 回）。

### 3.2 `FLEX_COUNTER_DB|FLEX_COUNTER_TABLE|ACL_STAT_COUNTER:<counter_oid>`

書込み関数: `m_flex_counter_manager.setCounterIdList()` (`flex_counter_manager.cpp:205`) / `clearCounterIdList()` (`flex_counter_manager.cpp:235`)

aclorch から呼ばれる箇所:

```cpp
// aclorch.cpp:6040
m_flex_counter_manager.setCounterIdList(rule.getCounterOid(), CounterType::ACL_COUNTER, serializedCounterStatAttrs);
// aclorch.cpp:6048
m_flex_counter_manager.clearCounterIdList(rule.getCounterOid());
```

- key: `ACL_STAT_COUNTER:<sai_counter_oid>` (group + ":" + serialized OID)
- field: `ACL_COUNTER_ATTR_ID_LIST` = カンマ区切りの SAI attribute ID 文字列列（`PACKETS`, `BYTES` 等を `sai_metadata_get_attr_metadata` で serialize、aclorch.cpp:6030-6038）

APPL_DB SET (新規ルール counter 作成) → COUNTERS_DB hset と **同じタイミング** で FLEX_COUNTER_DB へも書込まれる。APPL_DB DEL → COUNTERS_DB hdel と同タイミングで FLEX_COUNTER_DB エントリも削除される。

## 4. 書込み元プロセス別 副次効果

| 書込み元 (APPL_DB) | STATE_DB | COUNTERS_DB | FLEX_COUNTER_DB | 備考 |
|---|---|---|---|---|
| `vnetorch` (VNET_TUNNEL_TERM_*) | ACL_TABLE_TABLE + ACL_RULE_TABLE status | ACL_COUNTER_RULE_MAP に rule 登録 | ACL_STAT_COUNTER グループに counter OID 登録 | counter 既定 ON |
| `mclagsyncd` (mclag-egress-port-isolate) | 同上 | 同上 | 同上 | counter 既定 ON |
| `dashenifwdorch` (ENI fwd ACL) | 同上 | 同上 | 同上 | DPU 側 (`gMySwitchType=="dpu"`) では `m_minPriority/m_maxPriority=0` で rule が INACTIVE になり STATE_DB のみ書込まれ COUNTERS/FLEX_COUNTER は発火しないケースあり |

## 5. CRM への副次効果（補足）

`AclRule::createCounter()` (aclorch.cpp:1939) で `gCrmOrch->incCrmAclTableUsedCounter(CrmResourceType::CRM_ACL_COUNTER, ...)`、`removeCounter()` (aclorch.cpp:1985) で対称な `decCrmAclTableUsedCounter()` が呼ばれる。CRM 自体は CONFIG_DB / STATE_DB / COUNTERS_DB 外の `CrmOrch` 内部状態だが、定期的に `CRM_USAGE_TABLE` 等を出力する点で間接的副次効果あり。本ページの副次書込みスコープ外。

## evidence サマリ

| DB | テーブル | 発火点 |
|---|---|---|
| STATE_DB | `ACL_TABLE_TABLE\|<table>` | aclorch.cpp:5462,5477,5483,5492,5501,5508 (`setAclTableStatus` / `removeAclTableStatus`) |
| STATE_DB | `ACL_RULE_TABLE\|<table>\|<rule>` | aclorch.cpp:5670,5683,5690,5696,5704,5726 (`setAclRuleStatus` / `removeAclRuleStatus`) |
| COUNTERS_DB | `ACL_COUNTER_RULE_MAP` (HSET/HDEL) | aclorch.cpp:6041,6047 |
| FLEX_COUNTER_DB | `ACL_STAT_COUNTER:<oid>` | aclorch.cpp:6040,6048 (via `FlexCounterManager`) |
