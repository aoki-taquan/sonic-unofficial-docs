# ACL orch STATE_DB — Phase E: ハードコード定数 詳細トレース

生成日: 2026-05-15
対象ページ: `docs/reference/config-db/aclorch-state.md`

## 目的

`AclOrch` が STATE_DB の 3 テーブル (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`) で使用するハードコード定数 (テーブル名・フィールド名・状態文字列・ステージ文字列・デフォルト真偽値) をソースコードから抽出し、参照箇所と evidence 行を一覧化する。

## 訪問ファイル

| ファイル | 内容 |
|---------|------|
| `sonic-swss-common/common/schema.h` | STATE_DB テーブル名マクロ |
| `sonic-swss/orchagent/aclorch.cpp` | フィールド名マクロ・状態文字列ルックアップ・ステージ文字列リテラル・capability デフォルト |
| `sonic-swss/orchagent/acltable.h` | `STAGE_INGRESS` / `STAGE_EGRESS` マクロ |

## 1. STATE_DB テーブル名マクロ (`schema.h`)

| マクロ | 値 | 行 |
|--------|----|----|
| `STATE_ACL_TABLE_TABLE_NAME` | `"ACL_TABLE_TABLE"` | `sonic-swss-common/common/schema.h:514` |
| `STATE_ACL_RULE_TABLE_NAME` | `"ACL_RULE_TABLE"` | `sonic-swss-common/common/schema.h:515` |
| `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` | `"ACL_STAGE_CAPABILITY_TABLE"` | `sonic-swss-common/common/schema.h:418` |

参照箇所: `aclorch.cpp:4200-4202` (`AclOrch` コンストラクタの `m_aclStageCapabilityTable` / `m_aclTableStateTable` / `m_aclRuleStateTable` 初期化リスト)。

## 2. STATE_DB フィールド名マクロ (`aclorch.cpp` 冒頭)

| マクロ | 値 | 行 |
|--------|----|----|
| `STATE_DB_ACL_ACTION_FIELD_IS_ACTION_LIST_MANDATORY` | `"is_action_list_mandatory"` | `aclorch.cpp:42` |
| `STATE_DB_ACL_ACTION_FIELD_ACTION_LIST` | `"action_list"` | `aclorch.cpp:43` |
| `STATE_DB_ACL_L3V4V6_SUPPORTED` | `"supported_L3V4V6"` | `aclorch.cpp:44` |

参照箇所: `putAclActionCapabilityInDB()` (`aclorch.cpp:4089-4097`) で `ACL_STAGE_CAPABILITY_TABLE` のフィールド名として `emplace_back` される。

なお `status` (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` の唯一のフィールド) は `setAclTableStatus()` / `setAclRuleStatus()` 内で直接 `"status"` 文字列リテラルとして使用 (`aclorch.cpp:6088`, `6102` 付近; `fvVector.emplace_back("status", ...)` パターン)。

## 3. 状態文字列ルックアップ (`aclorch.cpp`)

`aclObjectStatusLookup` (`aclorch.cpp:521-527`) — `AclObjectStatus` enum 値を `status` フィールドに書き込む文字列にマッピング:

| enum 値 | 文字列リテラル | 行 |
|---------|---------------|----|
| `AclObjectStatus::ACTIVE` | `"Active"` | 523 |
| `AclObjectStatus::INACTIVE` | `"Inactive"` | 524 |
| `AclObjectStatus::PENDING_CREATION` | `"Pending creation"` | 525 |
| `AclObjectStatus::PENDING_REMOVAL` | `"Pending removal"` | 526 |

これら 4 値以外が `status` に出現することはない（`setAclTableStatus()` / `setAclRuleStatus()` は `aclObjectStatusLookup.at(...)` 経由でのみ書き込む）。

## 4. ステージ文字列マクロ (`acltable.h`)

| マクロ | 値 | 行 |
|--------|----|----|
| `STAGE_INGRESS` | `"INGRESS"` | `acltable.h:22` |
| `STAGE_EGRESS` | `"EGRESS"` | `acltable.h:23` |

利用箇所:

- `aclStageLookUp` (`aclorch.cpp:154-157`) — CONFIG_DB の `stage` 文字列 → `acl_stage_type_t` 変換キー。
- `putAclActionCapabilityInDB()` (`aclorch.cpp:4099`) — `m_aclStageCapabilityTable.set(stage_str, fvVector)` の key として使用。`stage_str` は `STAGE_INGRESS` / `STAGE_EGRESS` のいずれか。
- インラインリテラル `"INGRESS"` / `"EGRESS"` も同等用途で複数箇所に出現 (`aclorch.cpp:2599`, `4720`)。

なお `ACL_ACTIONS|INGRESS` / `ACL_ACTIONS|EGRESS` 形式のフィールド名は `putAclActionCapabilityInDB()` 内で `"ACL_ACTIONS|" + stage_str` として動的構築される（`aclorch.cpp` 該当ブロック）。

## 5. capability 構造体の真偽デフォルト

`AclActionCapabilities` (`aclorch.h:139-145` 近辺) — `isActionListMandatoryOnTableCreation{false}` がメンバ初期化子で `false` 固定。

SAI クエリ失敗時のフォールバック:

- `defaultAclActionsSupported` (`aclorch.cpp:168-196`) — INGRESS では `{PACKET_ACTION, MIRROR_INGRESS, NO_NAT}`、EGRESS では `{PACKET_ACTION}` の集合をハードコード。両ステージとも 2 番目のメンバ (`isActionListMandatoryOnTableCreation`) は `false`。
- `initDefaultAclActionCapabilities()` (`aclorch.cpp:4104-4118`) でこの値が `m_aclCapabilities[stage]` に代入され、`putAclActionCapabilityInDB()` を経由して STATE_DB に書き込まれる。

`boolalpha` 整数→文字列変換:

- `is_action_list_mandatory_stream << boolalpha << capabilities.isActionListMandatoryOnTableCreation;` (`aclorch.cpp:4087` 付近) — `bool` → `"true"` / `"false"` 文字列。
- `supported_L3V4V6` フィールドも同様に `it.second ? "true" : "false"` (`aclorch.cpp:4094`) で文字列化。

## 6. `m_L3V4V6Capability` プラットフォーム分岐デフォルト

`queryMirrorTableCapability()` (`aclorch.cpp:3489-3510` 付近) でプラットフォーム文字列 (`DEVICE_METADATA|localhost.platform`) により分岐:

| プラットフォーム文字列 | `m_L3V4V6Capability[stage]` |
|----------------------|-----------------------------|
| `MRVL_PRST_PLATFORM_SUBSTRING` 等 | `true` |
| `MRVL_TL_PLATFORM_SUBSTRING` | `true` |
| `VS_PLATFORM_SUBSTRING` | `true` |
| その他 (BRCM / MLNX / BFN 含む既定) | `false` |

STATE_DB 書込み時の文字列値は `it.second ? "true" : "false"` (`aclorch.cpp:4094`)。

## 7. その他関連定数

| 名前 | 値 | 行 | 用途 |
|------|----|----|------|
| `ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS` | `10000` (ms) | `aclorch.cpp:46` | カウンタポーリング既定。STATE_DB には書かれない (FlexCounter 系) |
| `ACL_COUNTER_DEFAULT_ENABLED_STATE` | `false` | `aclorch.cpp:47` | カウンタ既定無効 |
| `COUNTERS_ACL_COUNTER_RULE_MAP` | `"ACL_COUNTER_RULE_MAP"` | `aclorch.cpp:44` 付近 | COUNTERS_DB 側テーブル名 (STATE_DB 範囲外) |

これらは `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE` の値には直接寄与しないため、ページ本文 `<!-- constants -->` ブロックには含めない (参考としてのみ記録)。

## まとめ

ページ `aclorch-state.md` 本文の `<!-- constants -->` ブロックでは以下を網羅する:

1. STATE_DB テーブル名 3 種 (schema.h 由来)
2. capability フィールド名マクロ 3 種 (aclorch.cpp 由来)
3. `status` 文字列 4 値 (`aclObjectStatusLookup`)
4. ステージ文字列マクロ 2 種 (`STAGE_INGRESS` / `STAGE_EGRESS`) と `ACL_ACTIONS|<stage>` 動的構築
5. capability 真偽デフォルト (`isActionListMandatoryOnTableCreation = false`, `m_L3V4V6Capability` プラットフォーム分岐)
6. boolalpha による `"true"` / `"false"` 出力
