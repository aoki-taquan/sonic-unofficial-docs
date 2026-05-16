# aclorch-state — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/aclorch-state.md` Phase C 追加分。
本ページの主題は **STATE_DB の 3 テーブル**（`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`）で、いずれも `AclOrch` が**書き手 (producer only)** として書き込むテーブルである。
ここでの「暗黙参照」とは、これら STATE_DB テーブルのエントリ生成・キー値・タイミングが依存する**入力側テーブル**および**前提 Orch / プラットフォーム情報**を指す。
`sonic-swss/orchagent/aclorch.cpp` の STATE_DB 出力経路を精読し、暗黙依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/aclorch.cpp` | `AclOrch` コンストラクタ (L4197–), `putAclActionCapabilityInDB()` (L4056), `setAclTableStatus()` (L6088), `setAclRuleStatus()` (L6102), `removeAllAclTableStatus()` (L6116), `removeAllAclRuleStatus()` (L6128), `doAclTableTask()` (L5346), `doAclRuleTask()` (L5520), `init()` (L3475), `queryMirrorTableCapability()` (L3489–) |
| `sonic-swss/orchagent/aclorch.h` | `AclActionCapabilities` 構造体 (L143), STATE テーブル参照ハンドラ |
| `sonic-swss-common/common/schema.h` | `STATE_ACL_TABLE_TABLE_NAME` / `STATE_ACL_RULE_TABLE_NAME` / `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME`, `CFG_ACL_TABLE_TABLE_NAME` / `CFG_ACL_RULE_TABLE_NAME`, `APP_ACL_TABLE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME` |

## YANG leafref

`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE` は STATE_DB 専用のオペレーショナルテーブルであり、YANG モデル化されていない。leafref は存在せず、全依存が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `ACL_TABLE` (キー由来 + エントリ生成トリガ)

- **参照先テーブル**: `CONFIG_DB ACL_TABLE`
- **参照方向**: 読み取り（subscribe / Consumer 経由）+ キー転写
- **条件**: 常時。`AclOrch::doTask()` で `CFG_ACL_TABLE_TABLE_NAME` を受信し `doAclTableTask()` で処理 (`aclorch.cpp:4283–4285`)
- **意味**: `ACL_TABLE_TABLE|<table_name>` の `<table_name>` は CONFIG_DB `ACL_TABLE` のキーそのもの。`setAclTableStatus()` (L6088) が `m_aclTableStateTable.set(table_name, ...)` で書き込み、STATE_DB エントリの存在自体が CONFIG_DB `ACL_TABLE` への SET/DEL を起点とする。
- **evidence**: `aclorch.cpp:4283–4285`, `aclorch.cpp:5346` (`doAclTableTask`), `aclorch.cpp:6087–6092` (`setAclTableStatus`)

### 2. CONFIG_DB `ACL_RULE` (キー由来 + エントリ生成トリガ)

- **参照先テーブル**: `CONFIG_DB ACL_RULE`
- **参照方向**: 読み取り（subscribe / Consumer 経由）+ キー転写
- **条件**: 常時。`AclOrch::doTask()` で `CFG_ACL_RULE_TABLE_NAME` を受信し `doAclRuleTask()` で処理 (`aclorch.cpp:4287–4289`)
- **意味**: `ACL_RULE_TABLE|<table_name>|<rule_name>` の `<table_name>` と `<rule_name>` は CONFIG_DB `ACL_RULE` の複合キー要素。`setAclRuleStatus()` (L6102) が `m_aclRuleStateTable.set(table_name + "|" + rule_name, ...)` で書き込み。SAI 操作の成否に応じて `Active` / `Inactive` / `Pending creation` / `Pending removal` を反映。
- **evidence**: `aclorch.cpp:4287–4289`, `aclorch.cpp:5520–5570` (`doAclRuleTask`), `aclorch.cpp:6101–6106` (`setAclRuleStatus`)

### 3. APPL_DB `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` (もう一方の入力経路)

- **参照先テーブル**: `APPL_DB ACL_TABLE_TABLE`, `APPL_DB ACL_RULE_TABLE`
- **参照方向**: 読み取り（subscribe / Consumer 経由）
- **条件**: APPL_DB 経由で動的に設定される ACL（feature プロセスや動的 ACL 経路）
- **意味**: `AclOrch::doTask()` は `APP_ACL_TABLE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME` も `CFG_*` と同等に `doAclTableTask()` / `doAclRuleTask()` にディスパッチする (`aclorch.cpp:4283–4289`)。STATE_DB に書かれるエントリの起点が CONFIG_DB か APPL_DB かは透過的（`AclOrch` は区別しない）。
- **注意**: APPL_DB `ACL_RULE_TABLE` のリソース枯渇時は `createRetryCache(APP_ACL_RULE_TABLE_NAME)` (`aclorch.cpp:4222`) にパーク。
- **evidence**: `aclorch.cpp:4221–4222`, `aclorch.cpp:4283–4289`

### 4. CONFIG_DB `ACL_TABLE_TYPE` / APPL_DB `ACL_TABLE_TYPE_TABLE` (テーブル型定義)

- **参照先テーブル**: `CONFIG_DB ACL_TABLE_TYPE`, `APPL_DB ACL_TABLE_TYPE_TABLE`
- **参照方向**: 読み取り（subscribe / Consumer 経由）
- **条件**: `ACL_TABLE` の `type` フィールドがカスタム型を指すとき
- **意味**: `AclOrch::doTask()` の第 3 分岐で `CFG_ACL_TABLE_TYPE_TABLE_NAME` / `APP_ACL_TABLE_TYPE_TABLE_NAME` を処理 (`aclorch.cpp:4291`)。テーブル型が未定義のまま `ACL_TABLE` が来ると `addAclTable()` バリデーション失敗 → STATE_DB `ACL_TABLE_TABLE.status="Inactive"`。
- **evidence**: `aclorch.cpp:4291`

### 5. `PORT` テーブル (PortsOrch 初期化完了の前提)

- **参照先テーブル / Orch**: `PORT` (`PortsOrch::allPortsReady()`)
- **参照方向**: 起動順序ガード
- **条件**: 常時。`AclOrch::doTask()` 冒頭で `allPortsReady()` が false の間は ACL_RULE 処理を一切進めない
- **意味**: PortsOrch の初期化完了前は `doAclRuleTask()` に到達せず、STATE_DB `ACL_RULE_TABLE` には新規エントリが書かれない。`removeAllAclRuleStatus()` (L6128, init 時に呼ばれる L3481) のみが起動直後に走り、既存ステータスを一旦クリアする。
- **evidence**: `aclorch.cpp:4276` (`allPortsReady()` ブロック), `aclorch.cpp:3479–3481` (起動時 STATE_DB クリア)

### 6. SAI Switch capability (`ACL_STAGE_CAPABILITY_TABLE` の値ソース)

- **参照先**: SAI `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `SAI_SWITCH_ATTR_ACL_STAGE_EGRESS`
- **参照方向**: SAI クエリ（読み取り）
- **条件**: orchagent 起動時 1 回
- **意味**: SAI クエリ成功時は `attr.value.aclcapability.action_list` から動的にアクション集合を構築し、`is_action_list_mandatory` / `action_list` / `ACL_ACTIONS|<stage>` を STATE_DB に書き込む。失敗時は `initDefaultAclActionCapabilities()` (`aclorch.cpp:4104–4118`) が `defaultAclActionsSupported` (L168–196) のハードコード値でフォールバック。
- **evidence**: `aclorch.cpp:4025`, `aclorch.cpp:4036`, `aclorch.cpp:4056–4101` (`putAclActionCapabilityInDB`), `aclorch.cpp:4104–4118` (`initDefaultAclActionCapabilities`)

### 7. プラットフォーム情報 (`supported_L3V4V6` フィールドの分岐)

- **参照先**: 環境変数 / `DEVICE_METADATA|localhost.platform`（`platform` 文字列）
- **参照方向**: 読み取り（起動時）
- **条件**: `ACL_STAGE_CAPABILITY_TABLE` 書き込み時
- **意味**: `queryMirrorTableCapability()` (`aclorch.cpp:3489–3510`) がプラットフォーム文字列を判定し、`m_L3V4V6Capability[stage]` を `true`（MRVL_PRST / MRVL_TL / VS）または `false`（他）に設定。`putAclActionCapabilityInDB()` が `STATE_DB_ACL_L3V4V6_SUPPORTED` (`"supported_L3V4V6"`) として書き出す。
- **evidence**: `aclorch.cpp:3489–3510`, `aclorch.cpp:4093–4099`

### 8. SAI ACL 操作 (STATE_DB `status` 値の決定要因)

- **参照先**: SAI ACL API (`create_acl_table` / `create_acl_entry` / `remove_acl_table` / `remove_acl_entry`)
- **参照方向**: SAI 呼び出し（書き込み + 戻り値判定）
- **条件**: 常時。`doAclTableTask()` / `doAclRuleTask()` 内
- **意味**: SAI 戻り値が STATE_DB `status` フィールド値を決定する:
  - `addAclTable()` / `addAclRule()` 成功 → `"Active"`
  - SAI リソース枯渇 (`isSaiStatusResourceFull()`) → `"Pending creation"` + retry cache (`aclorch.cpp:5683–5692`)
  - バリデーション失敗 → `"Inactive"` (`aclorch.cpp:5492`, `aclorch.cpp:5704`)
  - `remove*()` 失敗 → `"Pending removal"` (`aclorch.cpp:5508`, `aclorch.cpp:5726`)
- **evidence**: `aclorch.cpp:5462`, `aclorch.cpp:5477–5508`, `aclorch.cpp:5670–5726`

## 参照関係サマリ

```
STATE_DB ACL_TABLE_TABLE / ACL_RULE_TABLE / ACL_STAGE_CAPABILITY_TABLE
  (書き手は AclOrch のみ。読み手は show acl table/rule、acl-loader、sonic-mgmt-common)

入力依存 (暗黙参照):
  ├─ [暗黙] CONFIG_DB ACL_TABLE                  (key 転写 + SET/DEL トリガ)
  ├─ [暗黙] CONFIG_DB ACL_RULE                   (key 転写 + SET/DEL トリガ)
  ├─ [暗黙] APPL_DB ACL_TABLE_TABLE              (同等の入力経路)
  ├─ [暗黙] APPL_DB ACL_RULE_TABLE               (同等の入力経路、retry cache 対象)
  ├─ [暗黙] CONFIG_DB ACL_TABLE_TYPE / APPL_DB ACL_TABLE_TYPE_TABLE
  │                                              (カスタム型解決失敗 → status="Inactive")
  ├─ [暗黙] PORT (PortsOrch::allPortsReady)      (起動順序ガード — false の間は ACL_RULE 処理停止)
  ├─ [暗黙] SAI Switch capability                (ACL_STAGE_CAPABILITY_TABLE の動的値ソース)
  ├─ [暗黙] platform 文字列 (DEVICE_METADATA)    (supported_L3V4V6 のプラットフォーム分岐)
  └─ [暗黙] SAI ACL API 戻り値                   (status フィールド Active/Inactive/Pending* の決定)
```

## evidence

- `aclorch.cpp`: L3479–3481 (起動時 STATE_DB クリア), L3489–3510 (`queryMirrorTableCapability` / L3V4V6), L4025–4118 (capability put + フォールバック), L4197–4225 (`AclOrch` コンストラクタ + retry cache 登録), L4276 (`allPortsReady()` ブロック), L4283–4291 (`doTask` ディスパッチ), L5346 (`doAclTableTask`), L5462–5508 (table status 設定), L5520 (`doAclRuleTask`), L5670–5726 (rule status 設定), L6087–6134 (`setAclTableStatus` / `setAclRuleStatus` / `removeAllAcl*Status`)
- `aclorch.h`: L143 (`AclActionCapabilities::isActionListMandatoryOnTableCreation {false}`)
- `schema.h`: `STATE_ACL_TABLE_TABLE_NAME`, `STATE_ACL_RULE_TABLE_NAME`, `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME`, `CFG_ACL_*` / `APP_ACL_*` 定義
