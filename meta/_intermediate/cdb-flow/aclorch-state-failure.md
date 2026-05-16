# aclorch-state — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-aclorch-state)

ソース: `sonic-net/sonic-swss/orchagent/aclorch.cpp` (ref: `4305596156d70e9797e8a881b3d19b46de0bce0d`)
対象ページ: `docs/reference/config-db/aclorch-state.md`
対象 STATE_DB テーブル: `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`

<!-- failure -->
## Phase D: 失敗挙動マトリクス

本ページの STATE_DB 3 テーブルは `AclOrch` のみが書込み主体である。書込み API (`m_aclTableStateTable.set/del` / `m_aclRuleStateTable.set/del` / `m_aclStageCapabilityTable.set`) は `swss::Table` の SET/DEL ラッパで、戻り値を持たず Redis 側で失敗してもアプリ層に伝播しない。本マトリクスはその制約を踏まえ、(a) STATE_DB 書込みを呼び出すロジックの失敗経路、(b) SAI capability クエリ失敗時の retry / フォールバック経路、(c) `init()` 起動時クリアでの失敗挙動を整理する。

### A. SAI capability クエリ失敗 → フォールバック (`ACL_STAGE_CAPABILITY_TABLE`)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|---|
| `SAI_SWITCH_ATTR_MAX_ACL_ACTION_COUNT` 取得失敗 | `queryAclActionCapability()` L3984 | WARN ログ → 両 stage で `initDefaultAclActionCapabilities()` → `putAclActionCapabilityInDB()` を実行（retry なし、1 回で確定） | `ACL_STAGE_CAPABILITY_TABLE|INGRESS` / `|EGRESS` に `defaultAclActionsSupported` のフォールバック値を書込み | `aclorch.cpp:3984, 4028-4038, 4104-4118` |
| stage 別 `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `_EGRESS` 取得失敗 | `queryAclActionCapability()` L3999 | WARN ログ → 当該 stage のみ `initDefaultAclActionCapabilities(stage)` → `putAclActionCapabilityInDB(stage)`（retry なし） | 当該 stage キーにフォールバック値、もう片方は SAI 成功値 | `aclorch.cpp:3999, 4016-4022, 4104-4118` |
| `sai_query_attribute_capability(SAI_SWITCH_ATTR_ACL_USER_META_DATA_RANGE)` 失敗 | `queryAclMetaDataCapability` 系 L3590 | WARN ログ → `m_aclMetaDataSupported=false` で続行 | `putAclActionCapabilityInDB()` の `metadataActionLookup` 経路がスキップされ、`action_list` に DSCP metadata action が現れない | `aclorch.cpp:3590, 4069-4072` |
| `sai_query_attribute_capability(SAI_ACL_ENTRY_ATTR_FIELD_ACL_USER_META)` / `_ACTION_SET_ACL_META_DATA` 失敗 | L3634 / L3648 | WARN ログ → 関連 capability bit false で続行 | 同上、間接的に `action_list` 内容に反映 | `aclorch.cpp:3634, 3648` |

!!! note "retry なし・1 回限り確定"
    capability クエリは `AclOrch::init()` 内で 1 回しか呼ばれず、SAI が一時的に失敗してもオンライン再試行はしない。フォールバック (`defaultAclActionsSupported`) で確定する。よって `ACL_STAGE_CAPABILITY_TABLE` に書かれる値は orchagent プロセス寿命中で固定。

### B. `ACL_TABLE_TABLE` 書込みに至る失敗経路 (`doAclTableTask`)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|---|
| `addAclTable()` 失敗（SAI `create_acl_table` 失敗等） | `doAclTableTask()` L5474-5485 | ERROR ログ → `setAclTableStatus(PENDING_CREATION)` → `it++`（次サイクルで再試行） | `"Pending creation"` | `aclorch.cpp:5483` |
| `updateAclTable()` 失敗 | L5457-5470 | ERROR ログ → `setAclTableStatus` 呼ばれず → `it++`（既存ステータス保持のまま再試行） | （前値保持） | `aclorch.cpp:5467-5470` |
| バリデーション失敗（不正設定: 未定義 type / stage 不一致 / port 解決不能等） | `doAclTableTask()` L5488-5495 | ERROR ログ → `setAclTableStatus(INACTIVE)` → `erase(it)`（恒久スキップ） | `"Inactive"` | `aclorch.cpp:5491-5495` |
| `removeAclTable()` 失敗（配下ルール削除失敗 / SAI `remove_acl_table` 失敗） | `doAclTableTask()` L5505-5510 | `setAclTableStatus(PENDING_REMOVAL)` → `it++`（次サイクルで再試行） | `"Pending removal"` | `aclorch.cpp:5508` |
| 未知 op（SET/DEL 以外） | L5512-5516 | ERROR ログ → `erase(it)`（STATE_DB 触らず） | （前値保持） | `aclorch.cpp:5514-5516` |

### C. `ACL_RULE_TABLE` 書込みに至る失敗経路 (`doAclRuleTask`)

| 失敗条件 | 検出箇所 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|---|
| 親 `ACL_TABLE` 未作成 (`table_oid == SAI_NULL_OBJECT_ID`) | `doAclRuleTask()` L5563 | INFO ログ → `it++`（テーブル作成待機、再キュー） | （書込まれない） | `aclorch.cpp:5563-5565` |
| 属性検証失敗 (`bAllAttributesOk=false`) または `newRule->validate()` 失敗 | L5666, L5700-5705 | ERROR ログ → `setAclRuleStatus(INACTIVE)` → `erase(it)`（恒久スキップ） | `"Inactive"` | `aclorch.cpp:5704` |
| `addAclRule()` 失敗 + SAI リソース枯渇 (`isSaiStatusResourceFull()` 真) + retry cache 投入成功 | L5673-5685 | WARN ログ → `setAclRuleStatus(PENDING_CREATION)` → retry cache に park → `erase(it)`（他ルール DEL で `notifyRetry()` 再キュー） | `"Pending creation"` | `aclorch.cpp:5673-5685` |
| `addAclRule()` 失敗 + リソース枯渇だが retry cache 投入失敗 | L5686-5692 | ERROR ログ → `setAclRuleStatus(PENDING_CREATION)` → `it++`（通常リトライ） | `"Pending creation"` | `aclorch.cpp:5688-5692` |
| `addAclRule()` 失敗（リソース枯渇以外: SAI create_acl_entry 一般失敗） | L5694-5698 | `setAclRuleStatus(PENDING_CREATION)` → `it++`（次サイクル再試行） | `"Pending creation"` | `aclorch.cpp:5696` |
| `removeAclRule()` 失敗 | L5722-5728 | `setAclRuleStatus(PENDING_REMOVAL)` → `it++` | `"Pending removal"` | `aclorch.cpp:5726` |
| 未知 op | L5730-5734 | ERROR ログ → `erase(it)`（STATE_DB 触らず） | （前値保持） | `aclorch.cpp:5732-5734` |

### D. retry cache 解放契機 (`notifyRetry`)

| 契機 | 効果 | STATE_DB 観測 | evidence |
|---|---|---|---|
| 同一テーブル内の他ルールが `removeAclRule()` 成功 (`ruleExisted==true`) | `notifyRetry(this, tableName, RETRY_CST_SAI_RESOURCE+table_id)` → park 中ルールを `m_toSync` に再キュー | park ルールが再 `addAclRule()`、成功時 `"Pending creation"` → `"Active"` に上書き、失敗時 `"Pending creation"` 維持 | `aclorch.cpp:5716-5721, 5670` |
| `ruleExisted==false`（テーブルなし等で「実際は何も削除していない」） | `notifyRetry()` を呼ばない | park 中ルールはそのまま `"Pending creation"` で滞留 | `aclorch.cpp:5717-5721` |

### E. `init()` 起動時 STATE_DB クリアの失敗扱い

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `m_aclTableStateTable.getKeys()` が Redis I/O エラーで例外 | `removeAllAclTableStatus()` L6119 | swss::Table が `system_error` を投げる可能性。`AclOrch::init()` は try/catch しないため orchagent プロセス abort（systemd で再起動）。再起動後はクリア再試行 | `aclorch.cpp:3479-3481, 6116-6125` |
| 同上 (rule) | `removeAllAclRuleStatus()` L6131 | 同上 | `aclorch.cpp:6128-6135` |
| `m_aclTableStateTable.del(key)` が個別 I/O エラー | L6123 / L6134 | swss::Table の DEL は内部で hiredis エラー時に例外、それ以外は戻り値なしで黙殺。例外時は前項と同様にプロセス abort | `aclorch.cpp:6123, 6134` |

### F. STATE_DB 書込み自体の失敗

`setAclTableStatus()` / `setAclRuleStatus()` / `putAclActionCapabilityInDB()` は `swss::Table::set()` を呼び戻り値を受け取らない（void）。Redis 接続断や AUTH エラーは `swss::DBConnector` 側で例外送出されるが、`AclOrch` 内に catch はないため orchagent プロセスごとフォールトし systemd により再起動。再起動後の `init()` で `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` が走り、CONFIG_DB / APPL_DB からの再投入で STATE_DB が再構築される。よって書込み失敗が永続的に STATE_DB の不整合を残すことはない（自己回復系）。

### 検出ロジック補足

- **`status` 値 5 状態（"Active" / "Inactive" / "Pending creation" / "Pending removal" / エントリ削除）**: 失敗時の遷移は (b)(c) の表に集約。retry cache 経由の `"Pending creation"` → `"Active"` 上書きは **同一テーブル内の他ルール DEL** が契機で、当該ルール自体の操作ではない点に注意（`aclorch.cpp:5716-5721`）。
- **SAI capability フォールバックの不可逆性**: 一度フォールバック値で `ACL_STAGE_CAPABILITY_TABLE` が書かれると、SAI 側で capability が回復しても再クエリはされない。読み手 (`acl-loader` / `sonic-mgmt-common`) は orchagent 再起動まで古い値を参照し続ける。
- **`removeAclTableStatus` / `removeAclRuleStatus` の冪等性**: `swss::Table::del()` は対象キー不在でもエラーにならない。よって DEL 経路の再試行 (`it++`) で多重呼び出しされても害はない。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `setAclTableStatus(...ACTIVE)` | 2 | `aclorch.cpp:5462, 5477` |
| `setAclTableStatus(...INACTIVE)` | 1 | `aclorch.cpp:5492` |
| `setAclTableStatus(...PENDING_CREATION)` | 1 | `aclorch.cpp:5483` |
| `setAclTableStatus(...PENDING_REMOVAL)` | 1 | `aclorch.cpp:5508` |
| `setAclRuleStatus(...ACTIVE)` | 1 | `aclorch.cpp:5670` |
| `setAclRuleStatus(...INACTIVE)` | 1 | `aclorch.cpp:5704` |
| `setAclRuleStatus(...PENDING_CREATION)` | 3 | `aclorch.cpp:5683, 5690, 5696` |
| `setAclRuleStatus(...PENDING_REMOVAL)` | 1 | `aclorch.cpp:5726` |
| `isSaiStatusResourceFull` | 1 | `aclorch.cpp:5673` |
| `notifyRetry` (resource) | 1 | `aclorch.cpp:5720` |
| `initDefaultAclActionCapabilities` | 3 | `aclorch.cpp:4021, 4035, 4104` |
| `putAclActionCapabilityInDB` | 4 | `aclorch.cpp:4025, 4036, 4056, 4117` |
| `removeAllAclTableStatus` / `removeAllAclRuleStatus` | 各 1 | `aclorch.cpp:3480, 3481, 6116, 6128` |
| `sai_query_attribute_capability` (ACL meta data) | 3 | `aclorch.cpp:3590, 3634, 3648` |
| `m_aclTableStateTable.set/del` | 3 | `aclorch.cpp:6092, 6098, 6123` |
| `m_aclRuleStateTable.set/del` | 3 | `aclorch.cpp:6106, 6112, 6134` |
| `m_aclStageCapabilityTable.set` | 1 | `aclorch.cpp:4101` |

<!-- /failure -->
