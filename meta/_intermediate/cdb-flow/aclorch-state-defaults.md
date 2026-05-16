# ACL orch STATE_DB — Phase A: コード由来の暗黙デフォルト 詳細トレース

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/aclorch-state.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/orchagent/aclorch.cpp` | `aclObjectStatusLookup` L521-527 | status 文字列マッピング |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::setAclTableStatus()` L6088-6093 | ACL_TABLE_TABLE status field 書き込み |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::setAclRuleStatus()` L6102-6107 | ACL_RULE_TABLE status field 書き込み |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::doAclTableTask()` L5462-5517 | TABLE status 遷移ロジック |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::doAclRuleTask()` L5670-5735 | RULE status 遷移ロジック |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::putAclActionCapabilityInDB()` L4056-4101 | ACL_STAGE_CAPABILITY_TABLE 書き込み |
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch::init()` L3475-3481 | 起動時に全 status エントリを削除 |
| `sonic-swss/orchagent/aclorch.h` | `AclObjectStatus` enum L124-130 | status 値定義 |
| `sonic-swss-common/common/schema.h` | L418, L514-515 | STATE_DB テーブル名定義 |

## STATE_DB に書き込まれるテーブル

AclOrch は以下の 3 テーブルを STATE_DB に書き込む:

1. `ACL_TABLE_TABLE` — ACL テーブルの設定・動作ステータス
2. `ACL_RULE_TABLE` — ACL ルールの設定・動作ステータス
3. `ACL_STAGE_CAPABILITY_TABLE` — プラットフォームの ACL アクション対応能力

## field 別 fallback 詳細

### ACL_TABLE_TABLE / ACL_RULE_TABLE の `status` フィールド

**フィールド名**: `status`
**型**: string (enum)

`aclObjectStatusLookup` テーブル (aclorch.cpp:521-527) で定義:

```cpp
static map<AclObjectStatus, string> aclObjectStatusLookup =
{
    {AclObjectStatus::ACTIVE, "Active"},
    {AclObjectStatus::INACTIVE, "Inactive"},
    {AclObjectStatus::PENDING_CREATION, "Pending creation"},
    {AclObjectStatus::PENDING_REMOVAL, "Pending removal"}
};
```

**書き込みタイミングと遷移**:

ACL テーブル (`doAclTableTask()`):
- `addAclTable()` 成功 → `"Active"` (L5477)
- `updateAclTable()` 成功 → `"Active"` (L5462)
- `addAclTable()` 失敗 → `"Pending creation"` (L5483)
- バリデーション失敗 → `"Inactive"` (L5492)
- `removeAclTable()` 成功 → エントリ削除 (L5502)
- `removeAclTable()` 失敗 → `"Pending removal"` (L5508)

ACL ルール (`doAclRuleTask()`):
- `addAclRule()` 成功 → `"Active"` (L5670)
- `addAclRule()` 失敗 (SAI リソース枯渇) → `"Pending creation"` (L5683, L5690)
- その他 `addAclRule()` 失敗 → `"Pending creation"` (L5696)
- バリデーション失敗 → `"Inactive"` (L5704)
- `removeAclRule()` 成功 → エントリ削除 (L5713)
- `removeAclRule()` 失敗 → `"Pending removal"` (L5726)

**初期値 (コード由来のデフォルト)**:
- `hard=0` のためデフォルトなし。エントリは AclOrch 起動時 (`init()`) に全削除され、その後テーブル/ルールが処理されるたびに書き込まれる。
- ユーザが CONFIG_DB / APP_DB に ACL テーブルを書いた時点では `"Pending creation"` が最初に設定され得るが、通常は成功すれば即 `"Active"` になる。

### ACL_STAGE_CAPABILITY_TABLE のフィールド

key 構造: `ACL_STAGE_CAPABILITY_TABLE|INGRESS` または `ACL_STAGE_CAPABILITY_TABLE|EGRESS`

**フィールド `ACL_ACTIONS|INGRESS` / `ACL_ACTIONS|EGRESS`** (`putAclActionCapabilityInDB()` L4059-4101):

- フィールド名パターン: `"ACL_ACTIONS|" + stage_str` (`stage_str` = `"INGRESS"` or `"EGRESS"`)
- 値: カンマ区切りのアクション名リスト (例: `PACKET_ACTION,REDIRECT_ACTION,MIRROR_INGRESS_ACTION,...`)
- SAI から `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `SAI_SWITCH_ATTR_ACL_STAGE_EGRESS` クエリで取得。失敗時は `defaultAclActionsSupported` のハードコード値を使用 (L4033-4037)。

**フィールド `is_action_list_mandatory`** (L4087-4089):
- 値: `"true"` または `"false"` (C++ `boolalpha` 形式)
- `AclActionCapabilities::isActionListMandatoryOnTableCreation` の値 (デフォルト `false`、struct 初期化: aclorch.h:143)
- SAI クエリ成功時: `attr.value.aclcapability.action_list_mandatory` の値を使用

**フィールド `action_list`** (L4089-4090):
- 値: サポートされるアクション名のカンマ区切り文字列
- 内容: `aclL3ActionLookup`, `aclMirrorStageLookup`, `aclDTelActionLookup`, `aclMetadataDscpActionLookup`, `aclInnerActionLookup` の各マップを走査し、SAI でサポートされるアクションのみ列挙

**フィールド `supported_L3V4V6`** (L4092-4098):
- 値: `"true"` または `"false"`
- `m_L3V4V6Capability[stage]` の値。`queryMirrorTableCapability()` で設定
- 特定プラットフォーム (BRCM, MLNX, BFN, MRVL 等) は `true`、その他 `false`

## デフォルト値サマリ

| テーブル | フィールド | デフォルト値 | コード根拠 |
|---------|-----------|------------|-----------|
| `ACL_TABLE_TABLE` | `status` | (起動時削除) → 処理後 `"Active"` or `"Inactive"` or `"Pending creation"` | `aclObjectStatusLookup`, `doAclTableTask()` |
| `ACL_RULE_TABLE` | `status` | (起動時削除) → 処理後 `"Active"` or `"Inactive"` or `"Pending creation"` | `aclObjectStatusLookup`, `doAclRuleTask()` |
| `ACL_STAGE_CAPABILITY_TABLE` | `is_action_list_mandatory` | `"false"` | `isActionListMandatoryOnTableCreation {false}` (aclorch.h:143) |
| `ACL_STAGE_CAPABILITY_TABLE` | `supported_L3V4V6` | `"false"` (汎用) / `"true"` (BRCM, MLNX 等) | `queryMirrorTableCapability()` |
| `ACL_STAGE_CAPABILITY_TABLE` | `action_list` | プラットフォーム依存 (SAI クエリ) | `putAclActionCapabilityInDB()` |

## YANG との対比

STATE_DB の ACL 関連テーブルは YANG 未定義。全フィールドは C++ コードレベルで決まる。
