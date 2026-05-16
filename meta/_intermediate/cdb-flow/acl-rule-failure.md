# ACL_RULE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-acl-rule)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/aclorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|---|
| `table_id` が空文字 | `doAclRuleTask()` L5537 | WARN ログ → `erase(it)` → 次 entry へ continue (恒久スキップ) | なし | `aclorch.cpp:5537-5541` |
| `table_oid == SAI_NULL_OBJECT_ID` かつコントロールプレーンテーブル | `doAclRuleTask()` L5554 | INFO ログ → `erase(it)` → 次 entry へ continue (恒久スキップ) | なし | `aclorch.cpp:5554-5561` |
| `table_oid == SAI_NULL_OBJECT_ID` かつ ACL_TABLE 未作成 | `doAclRuleTask()` L5563 | INFO ログ → `it++`（待機・リトライ）、ACL_TABLE 作成後に再処理 | なし | `aclorch.cpp:5563-5565` |
| `AclRule::makeShared()` が例外送出 | `doAclRuleTask()` L5578 | ERROR ログ → `erase(it)` → `return`（ループ全体を中断） | なし | `aclorch.cpp:5578-5582` |
| 未知/不正な属性名 (`validateAddMatch`/`validateAddAction` すべて false) | `doAclRuleTask()` L5628 | ERROR ログ → `bAllAttributesOk=false` → ループ break | `INACTIVE` | `aclorch.cpp:5628-5631` |
| IPv4 match (`SRC_IP`/`DST_IP`) と IPv6 match (`SRC_IPV6`/`DST_IPV6`) の同一ルール混在 (`type=L3V4V6`) | `doAclRuleTask()` L5656 | ERROR ログ → `bAllAttributesOk=false` | `INACTIVE` | `aclorch.cpp:5656-5663` |
| `newRule->validate()` 失敗 (`bAllAttributesOk=false` または validate 内部エラー) | `doAclRuleTask()` L5697 | ERROR ログ → `erase(it)` → rule 設定無効として恒久スキップ | `INACTIVE` | `aclorch.cpp:5697-5701` |
| `addAclRule()` 内 `table_oid == SAI_NULL_OBJECT_ID`（テーブル消失） | `addAclRule()` L4972 | ERROR ログ → `return false` | `PENDING_CREATION` (`it++`) | `aclorch.cpp:4972-4975` |
| `AclTable::add(newRule)` 失敗（SAI `create_acl_entry` 失敗 — SAI_STATUS_SUCCESS 以外） | `AclRule::create()` L1344 | ERROR ログ → `AclRange::remove()` + `decreaseNextHopRefCount()` → `return false` | `PENDING_CREATION` | `aclorch.cpp:1344-1364` |
| `AclRule::create()` → `SAI_STATUS_ITEM_ALREADY_EXISTS` | `AclRule::create()` L1348 | NOTICE ログ → `return true`（冪等処理、成功扱い） | `ACTIVE` | `aclorch.cpp:1348-1352` |
| SAI リソース枯渇 (`isSaiStatusResourceFull` = true) | `doAclRuleTask()` L5673 | WARN ログ → retry cache に `RETRY_CST_SAI_RESOURCE` 制約付きで退避 | `PENDING_CREATION` | `aclorch.cpp:5673-5693` |
| retry cache 投入自体が失敗 | `doAclRuleTask()` L5688 | ERROR ログ → `it++`（通常リトライキュー残留） | `PENDING_CREATION` | `aclorch.cpp:5688-5692` |
| `addAclRule()` 失敗（リソース枯渇以外） | `doAclRuleTask()` L5695 | `it++`（次サイクルまで待機） | `PENDING_CREATION` | `aclorch.cpp:5695-5697` |
| EGR_SET_DSCP 用ルール追加失敗 | `addAclRule()` L4962 | ERROR ログ → `return false`（メインルール追加前に中断） | `PENDING_CREATION` | `aclorch.cpp:4962-4964` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|---|
| `removeAclRule()` が false を返す（SAI 削除失敗） | `doAclRuleTask()` L5712 | `it++`（次サイクルまで待機） | `PENDING_REMOVAL` | `aclorch.cpp:5724-5727` |
| 削除対象 rule が既に存在しない (`rule == nullptr`) | `removeAclRule()` L5010 | NOTICE ログ → `return true`（冪等処理、成功扱い） | ステータス削除 | `aclorch.cpp:5010-5014` |
| DEL 時 `table_oid == SAI_NULL_OBJECT_ID` | `removeAclRule()` L5004 | WARN ログ → `return true`（テーブルなし → ルールも存在しないとみなし成功） | ステータス削除 | `aclorch.cpp:5004-5006` |

### 検出ロジック補足

- **`bAllAttributesOk` フラグ**: `doAclRuleTask()` 内で false になると、最終的に `setAclRuleStatus(INACTIVE)` + `erase(it)` で恒久スキップ。`it++` による再試行は一切行わない。
- **retry cache の解放契機**: DEL 成功時 (`ruleExisted == true`) に `notifyRetry()` → `RETRY_CST_SAI_RESOURCE` 制約が解除され、park 中のルールが再処理対象になる (`aclorch.cpp:5720`)。
- **STATE_DB への書き込み**: `setAclRuleStatus()` → `STATE_ACL_RULE_TABLE_NAME` (`"ACL_RULE_TABLE"`) に `status` フィールドとして反映 (`aclorch.cpp:3479`)。
- **`AclRule::makeShared()` 例外 → `return`**: 他の失敗は `it++` や `erase(it)` でループを継続するが、この経路のみ `return` でループ全体を即時中断する点に注意。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `bAllAttributesOk = false` | 3 | `aclorch.cpp:5406, 5418, 5657` |
| `setAclRuleStatus(...INACTIVE)` | 1 | `aclorch.cpp:5700` |
| `setAclRuleStatus(...PENDING_CREATION)` | 3 | `aclorch.cpp:5685, 5692, 5696` |
| `setAclRuleStatus(...PENDING_REMOVAL)` | 1 | `aclorch.cpp:5725` |
| `setAclRuleStatus(...ACTIVE)` | 1 | `aclorch.cpp:5669` |
| `notifyRetry` (SAI resource) | 1 | `aclorch.cpp:5720` |
| `isSaiStatusResourceFull` | 1 | `aclorch.cpp:5673` |
| `create_acl_entry` | 1 | `aclorch.cpp:1344` |
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | 1 | `aclorch.cpp:1348` |

<!-- /failure -->
