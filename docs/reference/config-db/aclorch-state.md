---
title: ACL orchagent STATE_DB テーブル
description: "STATE_DB の ACL 関連テーブル — AclOrch が SAI ACL 操作後に書き込む ACL_TABLE_TABLE / ACL_RULE_TABLE / ACL_STAGE_CAPABILITY_TABLE の構造とフィールド詳細。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.cpp
    ref: HEAD
  - repo: sonic-net/sonic-swss
    path: orchagent/aclorch.h
    ref: HEAD
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: HEAD
related:
  config_db:
    - ACL_TABLE
    - ACL_RULE
    - ACL_TABLE_TYPE
  cli:
    - show acl table
    - show acl rule
  yang: []
---

# ACL orchagent STATE_DB テーブル

## 概要

`sonic-swss` の `AclOrch` は [ACL](../../reference/glossary.md#term-acl) テーブル・ルールの [SAI](../../reference/glossary.md#term-sai) 操作結果を `STATE_DB` の 3 テーブルに書き込む[^1]。

| [STATE_DB](../../reference/glossary.md#term-state_db) テーブル | 役割 |
|-----------------|------|
| `ACL_TABLE_TABLE` | [ACL](../../reference/glossary.md#term-acl) テーブルの設定受付・動作ステータス |
| `ACL_RULE_TABLE` | [ACL](../../reference/glossary.md#term-acl) ルールの設定受付・動作ステータス |
| `ACL_STAGE_CAPABILITY_TABLE` | プラットフォームの ACL アクション対応能力 |

`ACL_TABLE_TABLE` と `ACL_RULE_TABLE` は書込み主体が [orchagent](../../reference/glossary.md#term-orchagent) のみであり、`show acl table` / `show acl rule` が参照する読み取り専用のステータスレジスタとして機能する。`ACL_STAGE_CAPABILITY_TABLE` は [orchagent](../../reference/glossary.md#term-orchagent) 起動時に一度書き込まれ、以降は変化しない。


## ACL_TABLE_TABLE

### key 構造

```text
ACL_TABLE_TABLE|<table_name>
```

- `<table_name>`: [CONFIG_DB](../../reference/glossary.md#term-config_db) `ACL_TABLE` のテーブル名と同一の文字列

### フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `status` | enum string | `AclOrch` | (起動時削除) | ACL テーブルの動作ステータス。`"Active"` / `"Inactive"` / `"Pending creation"` / `"Pending removal"` のいずれか |

### `status` フィールド詳細

`doAclTableTask()` がテーブル操作の結果に応じて以下の値を書き込む[^1]:

| 値 | 書込み条件 |
|----|-----------|
| `"Active"` | `addAclTable()` または `updateAclTable()` 成功時 |
| `"Inactive"` | バリデーション失敗（設定不正）時 |
| `"Pending creation"` | `addAclTable()` 失敗（リソース不足等）時 |
| `"Pending removal"` | `removeAclTable()` 失敗時 |
| (エントリ削除) | `removeAclTable()` 成功時、[orchagent](../../reference/glossary.md#term-orchagent) 起動時 |

<!-- defaults -->
**コード由来のデフォルト**:
- `AclOrch::init()` 起動時に `removeAllAclTableStatus()` で全エントリを削除する（`aclorch.cpp:3479-3481`）。
- ステータス文字列は `aclObjectStatusLookup` テーブルで定義 (`aclorch.cpp:521-527`)。
- 新しいエントリが最初に書き込まれる値は操作結果に依存する。正常フローでは `addAclTable()` 成功後 `"Active"` が最初の値となる。
<!-- /defaults -->

## ACL_RULE_TABLE

### key 構造

```text
ACL_RULE_TABLE|<table_name>|<rule_name>
```

- `<table_name>`: 所属する ACL テーブル名
- `<rule_name>`: [CONFIG_DB](../../reference/glossary.md#term-config_db) `ACL_RULE` のルール名と同一の文字列

### フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `status` | enum string | `AclOrch` | (起動時削除) | ACL ルールの動作ステータス。`"Active"` / `"Inactive"` / `"Pending creation"` / `"Pending removal"` のいずれか |

### `status` フィールド詳細

`doAclRuleTask()` がルール操作の結果に応じて以下の値を書き込む[^1]:

| 値 | 書込み条件 |
|----|-----------|
| `"Active"` | `addAclRule()` 成功時 |
| `"Inactive"` | バリデーション失敗（設定不正）時 |
| `"Pending creation"` | `addAclRule()` 失敗時（[SAI](../../reference/glossary.md#term-sai) リソース枯渇含む）。retry cache にパークされた場合も同値 |
| `"Pending removal"` | `removeAclRule()` 失敗時 |
| (エントリ削除) | `removeAclRule()` 成功時、orchagent 起動時 |

<!-- defaults -->
**コード由来のデフォルト**:
- `AclOrch::init()` 起動時に `removeAllAclRuleStatus()` で全エントリを削除する（`aclorch.cpp:3480-3481`）。
- [SAI](../../reference/glossary.md#term-sai) リソース枯渇 (`isSaiStatusResourceFull()` が真) の場合、`"Pending creation"` を設定して retry cache にルールをパーク。他ルールが削除されてリソースが解放されると `notifyRetry()` で再処理される (`aclorch.cpp:5673-5692`)。
<!-- /defaults -->

## ACL_STAGE_CAPABILITY_TABLE

### key 構造

```text
ACL_STAGE_CAPABILITY_TABLE|INGRESS
ACL_STAGE_CAPABILITY_TABLE|EGRESS
```

### フィールド一覧

| フィールド | 型 | 書込み主体 | デフォルト | 説明 |
|-----------|----|-----------|-----------|------|
| `ACL_ACTIONS\|INGRESS` | string | `AclOrch` (起動時) | プラットフォーム依存 | INGRESS ステージでサポートされるアクション名のカンマ区切りリスト |
| `ACL_ACTIONS\|EGRESS` | string | `AclOrch` (起動時) | プラットフォーム依存 | EGRESS ステージでサポートされるアクション名のカンマ区切りリスト |
| `is_action_list_mandatory` | boolean string | `AclOrch` (起動時) | `"false"` | テーブル作成時にアクションリストの指定が必須かどうか |
| `action_list` | string | `AclOrch` (起動時) | プラットフォーム依存 | サポートされるアクション名のカンマ区切りリスト |
| `supported_L3V4V6` | boolean string | `AclOrch` (起動時) | `"false"` (汎用) / `"true"` (BRCM, MLNX 等) | L3V4V6 統合テーブルのサポート有無 |

### フィールド詳細

**`is_action_list_mandatory`**:
- `putAclActionCapabilityInDB()` が `AclActionCapabilities::isActionListMandatoryOnTableCreation` の値を `boolalpha` 形式 (`"true"` / `"false"`) で書き込む。
- SAI から `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `SAI_SWITCH_ATTR_ACL_STAGE_EGRESS` クエリが成功した場合、`attr.value.aclcapability.action_list_mandatory` の値を使用。

<!-- defaults -->
**コード由来のデフォルト**:
- `AclActionCapabilities` 構造体の初期値: `isActionListMandatoryOnTableCreation {false}` (`aclorch.h:143`)。SAI クエリが失敗した場合は `initDefaultAclActionCapabilities()` が `defaultAclActionsSupported` のハードコード値でフォールバックする (`aclorch.cpp:4104-4118`)。
- `supported_L3V4V6` のデフォルトは `false`。BRCM・MLNX・BFN・MRVL 等の特定プラットフォームでは `queryMirrorTableCapability()` 内で `true` に設定される (`aclorch.cpp:3489-3510`)。
- `action_list` の内容はプラットフォーム SAI 実装に依存。フォールバック時は `defaultAclActionsSupported` テーブル (aclorch.cpp:168-196) のデフォルトアクションセットを使用。
<!-- /defaults -->

**`ACL_ACTIONS|INGRESS` / `ACL_ACTIONS|EGRESS`**:
- フィールド名は `"ACL_ACTIONS|" + stage_str`（`stage_str` = `"INGRESS"` または `"EGRESS"`）。
- 値はサポートされるアクション名（`PACKET_ACTION`, `REDIRECT_ACTION`, `MIRROR_INGRESS_ACTION` 等）をカンマ区切りで列挙した文字列。

<!-- ordering -->
## 書込み順依存 (Phase B)

`AclOrch` は [CONFIG_DB](../../reference/glossary.md#term-config_db) / APP_DB の `ACL_TABLE` / `ACL_RULE` を SAI に反映した後、結果ステータスを [STATE_DB](../../reference/glossary.md#term-state_db) 3 テーブルへ書き込む。SAI 操作の成否と親子関係（テーブル → ルール）に応じて、書込み順は orchagent 内部で自動調停されるが、consumer から観測しうる中間状態がいくつか存在する。

### 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `init()` での [STATE_DB](../../reference/glossary.md#term-state_db) クリア → capability 公開 | 強制先行（クリア優先） | 起動直後は capability が公開されるまでテーブル / ルールのステータスは未確定 |
| 2 | SAI capability クエリ成否に応じた 2 経路 → `ACL_STAGE_CAPABILITY_TABLE` 書込み | 1 回限り（init 内で確定） | クエリ失敗時は `defaultAclActionsSupported` のフォールバック値で公開 |
| 3 | `ACL_TABLE` が `Active` 登録 → `ACL_RULE_TABLE` ステータス書込み許可 | **強制先行** | rule は `m_toSync` で再キューされ、テーブル登録後に書込まれる |
| 4 | SAI 結果 → `ACL_TABLE_TABLE.status` 遷移 | 即時（中間状態あり） | consumer は `Pending creation` を一時的に観測しうる |
| 5 | 他ルール DEL → retry cache の `Pending creation` ルール再評価 | 操作依存（非自明） | `notifyRetry()` が自動再キュー、成功時 `Active` 上書き |
| 6 | SAI DEL 失敗 → `Pending removal` 滞留 | 即時（次回イテレーションで再試行） | 配下ルール削除後の再試行で自然解消 |
| 7 | INGRESS / EGRESS capability 書込み | 独立 | init 完了前の同時読み出しは中間状態あり |

### 主要な制約詳細

**ACL_TABLE → ACL_RULE 親子順序 (依存 #3)**: `doAclRuleTask()` は `getTableById(table_id)` が `SAI_NULL_OBJECT_ID` を返す間、ルールを `m_toSync` に残したまま `it++; continue;` で再キューする。このため `ACL_RULE_TABLE|<table>|<rule>` の STATE_DB ステータスは、対応する `ACL_TABLE` が `addAclTable()` 成功で内部マップ `m_AclTables` に登録された後まで**書き込まれない**。CONFIG_DB 側でルールを先に投入しても、consumer から見た STATE_DB の出現順は常に「テーブル `Active` → ルール `Active`」となる（evidence: `aclorch.cpp:5548-5566`, `aclorch.cpp:5665-5706`）。

**retry cache 経由の非自明な順序 (依存 #5)**: SAI リソース枯渇 (`isSaiStatusResourceFull()` が真) で `addAclRule()` が失敗した場合、`setAclRuleStatus(..., PENDING_CREATION)` を書いてから `consumer.addToRetry()` でルールを retry cache にパークし、`m_toSync` からは erase する。後続で**同一テーブル内の他ルールが** `removeAclRule()` 成功すると `notifyRetry()` が retry cache を再キューし、再度 `addAclRule()` が実行される。成功時に `setAclRuleStatus(..., ACTIVE)` で上書きされるため、操作者から見ると「無関係に見えるルール A の削除がルール B を `Pending creation` → `Active` に遷移させる」という非自明な順序関係が成立する（evidence: `aclorch.cpp:5673-5692`, `aclorch.cpp:5710-5721`）。

**init() でのクリア → capability の順 (依存 #1, #2)**: `AclOrch::init()` は冒頭で `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` を呼んで STATE_DB の旧テーブル/ルールステータスを全削除し、その後 `queryAclActionCapability()` を呼んで `ACL_STAGE_CAPABILITY_TABLE` を書き込む。SAI クエリが失敗した場合も `initDefaultAclActionCapabilities()` → `putAclActionCapabilityInDB()` の同 path でフォールバック値が公開されるため、`ACL_STAGE_CAPABILITY_TABLE` は init 完了時点で必ず 1 回書かれる（evidence: `aclorch.cpp:3479-3481`, `aclorch.cpp:3708`, `aclorch.cpp:4017-4037`, `aclorch.cpp:4104-4118`）。

<!-- /ordering -->

<!-- constants -->
## ハードコード定数 (Phase E)

本ページが扱う STATE_DB 3 テーブルでは、テーブル名・フィールド名・状態文字列・ステージ文字列・真偽デフォルトのほぼ全てがソースコード側の `#define` または静的データに固定されている。CONFIG_DB / [DEVICE_METADATA](../../reference/glossary.md#term-device_metadata) 等の外部入力で変わるのは `<table_name>` / `<rule_name>` の動的部分と、プラットフォーム分岐される `supported_L3V4V6` / `action_list` の値のみ。

### STATE_DB テーブル名（`sonic-swss-common/common/schema.h`）

| マクロ | 値 | evidence |
|--------|----|----------|
| `STATE_ACL_TABLE_TABLE_NAME` | `"ACL_TABLE_TABLE"` | `schema.h:514` |
| `STATE_ACL_RULE_TABLE_NAME` | `"ACL_RULE_TABLE"` | `schema.h:515` |
| `STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` | `"ACL_STAGE_CAPABILITY_TABLE"` | `schema.h:418` |

`AclOrch` コンストラクタの初期化子 (`aclorch.cpp:4200-4202`) でこの 3 マクロを直接 `Table` オブジェクトに渡しているため、STATE_DB 上の文字列キーは固定。

### フィールド名マクロ（`sonic-swss/orchagent/aclorch.cpp`）

| マクロ | 値 | evidence |
|--------|----|----------|
| `STATE_DB_ACL_ACTION_FIELD_IS_ACTION_LIST_MANDATORY` | `"is_action_list_mandatory"` | `aclorch.cpp:42` |
| `STATE_DB_ACL_ACTION_FIELD_ACTION_LIST` | `"action_list"` | `aclorch.cpp:43` |
| `STATE_DB_ACL_L3V4V6_SUPPORTED` | `"supported_L3V4V6"` | `aclorch.cpp:44` |

`putAclActionCapabilityInDB()` (`aclorch.cpp:4089-4097`) でこれらを `fvVector.emplace_back` する。`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` 側の `status` フィールド名はマクロ化されておらず、`setAclTableStatus()` / `setAclRuleStatus()` 内で直接 `"status"` リテラルが使われる。

### `status` 値ルックアップ（`aclObjectStatusLookup`）

`aclorch.cpp:521-527` の静的 `map<AclObjectStatus, string>` で 4 値固定:

| enum 値 | 書込み文字列 |
|---------|--------------|
| `AclObjectStatus::ACTIVE` | `"Active"` |
| `AclObjectStatus::INACTIVE` | `"Inactive"` |
| `AclObjectStatus::PENDING_CREATION` | `"Pending creation"` |
| `AclObjectStatus::PENDING_REMOVAL` | `"Pending removal"` |

`status` フィールドは `aclObjectStatusLookup.at(...)` 経由でしか書かれないため、これら 4 文字列以外が STATE_DB に出現することはない。

### ステージ文字列（`sonic-swss/orchagent/acltable.h`）

| マクロ | 値 | evidence |
|--------|----|----------|
| `STAGE_INGRESS` | `"INGRESS"` | `acltable.h:22` |
| `STAGE_EGRESS` | `"EGRESS"` | `acltable.h:23` |

`ACL_STAGE_CAPABILITY_TABLE` のキー (`m_aclStageCapabilityTable.set(stage_str, ...)`) と、`ACL_ACTIONS|<stage_str>` 形式の動的フィールド名構築 (`putAclActionCapabilityInDB()`) に使われる。インラインで `"INGRESS"` / `"EGRESS"` リテラルが書かれている箇所 (`aclorch.cpp:2599`, `4720`) も同値で意味的に等価。

### capability の真偽デフォルト

| 名前 | 値 | evidence | STATE_DB 反映先 |
|------|----|----------|-----------------|
| `AclActionCapabilities::isActionListMandatoryOnTableCreation` | `false` (メンバ初期化子) | `aclorch.h:143` 付近 | `is_action_list_mandatory` |
| `m_L3V4V6Capability[stage]`（汎用プラットフォーム） | `false` | `aclorch.cpp:3489-3510` | `supported_L3V4V6` |
| `m_L3V4V6Capability[stage]`（MRVL_PRST / MRVL_TL / [VS](../../reference/glossary.md#term-vs) 等） | `true` | 同上 | `supported_L3V4V6` |
| `defaultAclActionsSupported[INGRESS]` | `{PACKET_ACTION, MIRROR_INGRESS, NO_NAT}` + mandatory=`false` | `aclorch.cpp:168-184` | `action_list` (SAI クエリ失敗時のフォールバック) |
| `defaultAclActionsSupported[EGRESS]` | `{PACKET_ACTION}` + mandatory=`false` | `aclorch.cpp:185-196` | `action_list` (フォールバック) |

`bool` → 文字列化は `boolalpha` (`aclorch.cpp:4087` 付近) または三項演算 `it.second ? "true" : "false"` (`aclorch.cpp:4094`) で行われ、STATE_DB には小文字 `"true"` / `"false"` が書かれる（`"True"` / `"1"` 等は出現しない）。

### 起動時クリア対象テーブル名

`removeAllAclTableStatus()` / `removeAllAclRuleStatus()` (`aclorch.cpp:6116`, `6128`) は上記 `STATE_ACL_TABLE_TABLE_NAME` / `STATE_ACL_RULE_TABLE_NAME` のキーを列挙して `del()` する。`STATE_ACL_STAGE_CAPABILITY_TABLE_NAME` は起動時クリアの対象外で、`init()` の capability 公開フローで上書きされる。

!!! note "Pending creation の `c` は小文字固定"
    `"Pending creation"` / `"Pending removal"` はいずれも語頭のみ大文字で 2 語目は小文字。consumer 側（`show acl table` 等）はこの大小区別を前提に文字列比較しているため、ソース改変時は `aclObjectStatusLookup` を変更すると CLI 表示と乖離する。

<!-- /constants -->

## 購読者 (consumer)

| プロセス / CLI | 参照テーブル | 用途 |
|--------------|------------|------|
| `show acl table` ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)) | `STATE_DB ACL_TABLE_TABLE` | テーブルのステータス表示 |
| `show acl rule` ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)) | `STATE_DB ACL_RULE_TABLE` | ルールのステータス表示 |
| `acl-loader` | `STATE_DB ACL_STAGE_CAPABILITY_TABLE` | プラットフォーム対応能力の参照 |
| `sonic-mgmt-common` (translib) | `STATE_DB ACL_STAGE_CAPABILITY_TABLE` | REST/[gNMI](../../reference/glossary.md#term-gnmi) 経由の能力情報提供 |

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

本ページの STATE_DB 3 テーブル（`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`）はいずれも [YANG](../../reference/glossary.md#term-yang) 未モデル化のオペレーショナルテーブルで、`AclOrch` が**書き手 (producer only)** として書き込む。
ここでの暗黙参照は、これら STATE_DB エントリの**生成トリガ・キー値・フィールド値**が依存する入力側テーブルと前提 Orch / プラットフォーム情報を指す。

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `ACL_TABLE\|<table_name>` (CONFIG_DB) | キー転写 + SET/DEL トリガ | 常時。`<table_name>` は STATE_DB `ACL_TABLE_TABLE` キーに転写される | `aclorch.cpp` L4283–4285 (dispatch), L5346 (`doAclTableTask`), L6087–6092 (`setAclTableStatus`) |
| `ACL_RULE\|<table_name>\|<rule_name>` (CONFIG_DB) | キー転写 + SET/DEL トリガ | 常時。複合キーがそのまま STATE_DB `ACL_RULE_TABLE` キーへ | `aclorch.cpp` L4287–4289, L5520 (`doAclRuleTask`), L6101–6106 (`setAclRuleStatus`) |
| `ACL_TABLE_TABLE` ([APPL_DB](../../reference/glossary.md#term-appl_db)) | 同等の入力経路 | [APPL_DB](../../reference/glossary.md#term-appl_db) 経由の動的 ACL（feature プロセス等） | `aclorch.cpp` L4283 (`APP_ACL_TABLE_TABLE_NAME` も dispatch) |
| `ACL_RULE_TABLE` ([APPL_DB](../../reference/glossary.md#term-appl_db)) | 同等の入力経路、retry cache 対象 | APPL_DB 経由の動的 ACL ルール。SAI リソース枯渇時は retry cache にパーク | `aclorch.cpp` L4222 (`createRetryCache(APP_ACL_RULE_TABLE_NAME)`), L4287 |
| `ACL_TABLE_TYPE` (CONFIG_DB) / `ACL_TABLE_TYPE_TABLE` (APPL_DB) | カスタム型解決 | `ACL_TABLE` の `type` がカスタム型のとき。未定義なら `status="Inactive"` | `aclorch.cpp` L4291 |
| `PORT` (PortsOrch `allPortsReady()`) | 起動順序ガード | 常時。false の間は `doAclRuleTask()` に到達せず STATE_DB `ACL_RULE_TABLE` に新規エントリが書かれない | `aclorch.cpp` L4276 |
| SAI Switch capability (`SAI_SWITCH_ATTR_ACL_STAGE_*`) | SAI クエリ → STATE_DB 書込み | 起動時 1 回。`ACL_STAGE_CAPABILITY_TABLE` の動的値ソース。失敗時は `defaultAclActionsSupported` でフォールバック | `aclorch.cpp` L4025–4036, L4056–4101 (`putAclActionCapabilityInDB`), L4104–4118 |
| `DEVICE_METADATA\|localhost.platform`（platform 文字列） | プラットフォーム分岐 | `supported_L3V4V6` フィールド決定時 (MRVL_PRST / MRVL_TL / [VS](../../reference/glossary.md#term-vs) で `true`、他で `false`) | `aclorch.cpp` L3489–3510 (`queryMirrorTableCapability`), L4093–4099 |
| SAI ACL API 戻り値 (`create/remove_acl_table/entry`) | 戻り値判定 → `status` 値 | 常時。`Active` / `Inactive` / `Pending creation` / `Pending removal` を決定。リソース枯渇は retry cache にパーク | `aclorch.cpp` L5462–5508 (table), L5670–5726 (rule), `isSaiStatusResourceFull()` L5683–5692 |

!!! note "STATE_DB エントリは「書き出し専用」のステータスレジスタ"
    `AclOrch` 以外の書き手は存在しない。`show acl table` / `show acl rule` / `acl-loader` / `sonic-mgmt-common` (translib) は読み手のみ。
    `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` (`aclorch.cpp:6116`, `6128`) が orchagent 起動時 (`init()` L3479–3481) に一度全エントリを削除し、その後 CONFIG_DB / APPL_DB からの再 SET を契機に再構築される。

!!! note "`ACL_STAGE_CAPABILITY_TABLE` は起動時 1 回のみ更新"
    `putAclActionCapabilityInDB()` (`aclorch.cpp:4056`) は orchagent 起動時の capability 確定段階で呼ばれるのみで、CONFIG_DB / APPL_DB の動的変更による再書込みは発生しない。
    フィールド値はプラットフォーム SAI capability と `DEVICE_METADATA` の `platform` 文字列に静的に依存する。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

本ページの STATE_DB 3 テーブル (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`) は `AclOrch` のみが書き手で、`swss::Table::set/del` を直接呼ぶ（戻り値なし）。よって「STATE_DB 書込み自体の失敗」はアプリ層で観測できず、[Redis](../../reference/glossary.md#term-redis) 接続例外時は orchagent プロセスごと abort して systemd 再起動で自己回復する経路に集約される。本節は (A) SAI capability クエリ失敗時のフォールバック、(B/C) `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` ステータス書込みに至る失敗分岐、(D) SAI リソース枯渇時の retry cache 経由経路、(E) `init()` 起動時クリアの例外扱い、の 5 系統を整理する。

### A. SAI capability クエリ失敗 → フォールバック (`ACL_STAGE_CAPABILITY_TABLE`)

| 失敗条件 | 結果 | STATE_DB 反映 | evidence |
|---|---|---|---|
| `SAI_SWITCH_ATTR_MAX_ACL_ACTION_COUNT` 取得失敗 | WARN ログ → 両 stage で `initDefaultAclActionCapabilities()` → `putAclActionCapabilityInDB()`。retry なし、1 回で確定 | `ACL_STAGE_CAPABILITY_TABLE|INGRESS` / `|EGRESS` に `defaultAclActionsSupported` のフォールバック値 (`action_list` = INGRESS: `PACKET_ACTION,MIRROR_INGRESS,NO_NAT` / EGRESS: `PACKET_ACTION`、`is_action_list_mandatory="false"`) | `aclorch.cpp:3984, 4028-4038, 4104-4118, 168-196` |
| stage 別 `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS/_EGRESS` 取得失敗 | WARN ログ → 当該 stage のみフォールバック、他 stage は SAI 成功値 | 片側フォールバック、片側 SAI 動的値 | `aclorch.cpp:3999, 4016-4022` |
| `sai_query_attribute_capability(SAI_SWITCH_ATTR_ACL_USER_META_DATA_RANGE)` 失敗 | WARN ログ → `m_aclMetaDataSupported=false` で続行 | `action_list` から [DSCP](../../reference/glossary.md#term-dscp) metadata action が除外される | `aclorch.cpp:3590, 4069-4072` |
| `sai_query_attribute_capability` (`FIELD_ACL_USER_META` / `ACTION_SET_ACL_META_DATA`) 失敗 | WARN ログ → 関連 capability false で続行 | `action_list` 内容に間接反映 | `aclorch.cpp:3634, 3648` |

!!! note "capability クエリは retry なし・1 回限り確定"
    `AclOrch::init()` 内で 1 回しか呼ばれず、SAI 一時失敗時もオンライン再試行はしない。orchagent プロセス寿命中、`ACL_STAGE_CAPABILITY_TABLE` の値はフォールバック確定のまま固定される。読み手 (`acl-loader` / `sonic-mgmt-common`) は orchagent 再起動まで古い値を参照する。

### B. `ACL_TABLE_TABLE` 書込みに至る失敗分岐 (`doAclTableTask`)

| 失敗条件 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|
| `addAclTable()` 失敗（SAI `create_acl_table` 失敗等） | ERROR ログ → `setAclTableStatus(PENDING_CREATION)` → `it++`（次サイクル再試行） | `"Pending creation"` | `aclorch.cpp:5474-5485` |
| `updateAclTable()` 失敗 | ERROR ログ → `setAclTableStatus` 呼ばれず → `it++`（前ステータス保持） | （前値保持） | `aclorch.cpp:5457-5470` |
| バリデーション失敗（不正設定: 未定義 type / stage 不一致 / port 解決不能等） | ERROR ログ → `setAclTableStatus(INACTIVE)` → `erase(it)`（恒久スキップ） | `"Inactive"` | `aclorch.cpp:5488-5495` |
| `removeAclTable()` 失敗（配下ルール削除失敗 / SAI `remove_acl_table` 失敗） | `setAclTableStatus(PENDING_REMOVAL)` → `it++`（次サイクル再試行） | `"Pending removal"` | `aclorch.cpp:5505-5510` |
| 未知 op（SET/DEL 以外） | ERROR ログ → `erase(it)` | （前値保持） | `aclorch.cpp:5512-5516` |

### C. `ACL_RULE_TABLE` 書込みに至る失敗分岐 (`doAclRuleTask`)

| 失敗条件 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|
| 親 `ACL_TABLE` 未作成 (`table_oid == SAI_NULL_OBJECT_ID`) | INFO ログ → `it++`（テーブル作成待機、再キュー） | （書込まれない） | `aclorch.cpp:5563-5565` |
| 属性検証失敗 (`bAllAttributesOk=false`) または `newRule->validate()` 失敗 | ERROR ログ → `setAclRuleStatus(INACTIVE)` → `erase(it)`（恒久スキップ） | `"Inactive"` | `aclorch.cpp:5700-5705` |
| `addAclRule()` 失敗 + リソース枯渇 (`isSaiStatusResourceFull` 真) + retry cache 投入成功 | WARN ログ → `setAclRuleStatus(PENDING_CREATION)` → retry cache park → `erase(it)` | `"Pending creation"` | `aclorch.cpp:5673-5685` |
| `addAclRule()` 失敗 + リソース枯渇だが retry cache 投入失敗 | ERROR ログ → `setAclRuleStatus(PENDING_CREATION)` → `it++` | `"Pending creation"` | `aclorch.cpp:5686-5692` |
| `addAclRule()` 失敗（リソース枯渇以外、SAI `create_acl_entry` 一般失敗） | `setAclRuleStatus(PENDING_CREATION)` → `it++` | `"Pending creation"` | `aclorch.cpp:5694-5698` |
| `removeAclRule()` 失敗 | `setAclRuleStatus(PENDING_REMOVAL)` → `it++` | `"Pending removal"` | `aclorch.cpp:5722-5728` |

### D. retry cache 経由の遷移 (SAI リソース枯渇 → 解放)

`isSaiStatusResourceFull()` が真で `addAclRule()` が失敗したルールは `RETRY_CST_SAI_RESOURCE+table_id` 制約付きで retry cache に park される。**同一テーブル内の他ルール DEL** が成功 (`ruleExisted==true`) すると `notifyRetry(this, tableName, RETRY_CST_SAI_RESOURCE+table_id)` で park 中ルールが `m_toSync` に再キューされ、再度 `addAclRule()` が走る。成功時に `setAclRuleStatus(ACTIVE)` で `"Pending creation"` → `"Active"` 上書き、再失敗時は `"Pending creation"` 維持。`ruleExisted==false` の場合は `notifyRetry()` が呼ばれず park 滞留が継続する（evidence: `aclorch.cpp:5673-5692, 5710-5721, 5670`）。

### E. `init()` 起動時 STATE_DB クリアの例外扱い

`removeAllAclTableStatus()` / `removeAllAclRuleStatus()` は `m_aclTableStateTable.getKeys()` と `del(key)` を呼ぶ。[Redis](../../reference/glossary.md#term-redis) I/O エラー時、`swss::DBConnector` 系から `system_error` 例外が送出されうるが `AclOrch::init()` 側に try/catch はない。例外は orchdaemon まで伝播し orchagent プロセス abort、systemd で再起動 → 再 `init()` で再試行という自己回復経路を取る（evidence: `aclorch.cpp:3479-3481, 6116-6135`）。

### 検出ロジック補足

- **`status` 値は 5 状態** (`"Active"` / `"Inactive"` / `"Pending creation"` / `"Pending removal"` / エントリ削除)。失敗経路では `"Inactive"` が恒久スキップ、`"Pending creation"` / `"Pending removal"` が再試行ループに対応する。
- **`setAclTableStatus` / `setAclRuleStatus` / `putAclActionCapabilityInDB` の戻り値なし**: `swss::Table::set/del` は void。[Redis](../../reference/glossary.md#term-redis) 失敗は例外として伝播し、orchagent プロセス再起動でのみ回復する。STATE_DB 不整合が永続することは設計上ない（再起動後 CONFIG_DB / APPL_DB 再投入で再構築）。
- **capability フォールバックの不可逆性**: SAI が後から capability を返せるようになっても再クエリされない。`ACL_STAGE_CAPABILITY_TABLE` の値は orchagent プロセス寿命中固定。
- **retry cache の解放契機の非自明性**: 「無関係に見えるルール A の DEL がルール B を `Pending creation` → `Active` に遷移させる」順序がある。Phase B（順序依存 #5）と表裏。

> **証跡**: `queryAclActionCapability()` L3975-4054、`initDefaultAclActionCapabilities()` L4104-4118、`putAclActionCapabilityInDB()` L4056-4101、`doAclTableTask()` L5450-5518、`doAclRuleTask()` L5520-5734、`setAclTableStatus()` L6088-6093、`setAclRuleStatus()` L6102-6107、`removeAllAclTableStatus()` / `removeAllAclRuleStatus()` L6116-6135、`isSaiStatusResourceFull` L5673、`notifyRetry` L5720。詳細グレップ証跡は `meta/_intermediate/cdb-flow/aclorch-state-failure.md` を参照。

<!-- /failure -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

本ページが扱う STATE_DB 3 テーブル (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`) に加え、`AclOrch` は ACL ルールに対する SAI カウンタ統計を有効化する際に **[COUNTERS_DB](../../reference/glossary.md#term-counters_db)** および **[FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db)** へ副次的なエントリを書き込む。SAI ACL `entry`/`counter` 自体の書込み ([ASIC_DB](../../reference/glossary.md#term-asic_db) 経由) は主作用のため除外する。

| 副次 DB | テーブル / キー | 書込内容 | 根拠 |
|---|---|---|---|
| [COUNTERS_DB](../../reference/glossary.md#term-counters_db) | `COUNTERS:ACL_COUNTER_RULE_MAP` (hash) | `<table>:<rule>` → ACL counter SAI OID のマッピングを `hset` / `hdel` | `aclorch.cpp:25-26, 45, 6020-6048` `registerFlexCounter()` / `deregisterFlexCounter()` の `m_countersDb.hset(COUNTERS_ACL_COUNTER_RULE_MAP, ruleIdentifier, counterOidStr)` および `hdel` |
| [FLEX_COUNTER_DB](../../reference/glossary.md#term-flex_counter_db) | `FLEX_COUNTER_GROUP_TABLE` / `FLEX_COUNTER_TABLE` 配下 (`ACL_COUNTER_FLEX_COUNTER_GROUP`) | `FlexCounterManager` 経由で polling interval / stats mode と counter id list (`SAI_ACL_COUNTER_ATTR_PACKETS` / `_BYTES` 等) を `set` / `clear` | `aclorch.cpp:4208-4214` `m_flex_counter_manager(ACL_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ, ACL_COUNTER_DEFAULT_POLLING_INTERVAL_MS, ACL_COUNTER_DEFAULT_ENABLED_STATE)`、L6040 `setCounterIdList()`、L6048 `clearCounterIdList()` |

呼出しトリガは ACL ルール作成 (`registerFlexCounter` at L4982, L5153)、`updateAclRule` でのカウンタ有効/無効切替 (L5019, L5157)、テーブル / ルール削除時の deregister 連鎖 (L3001, L3095) など。APPL_DB / [ASIC_DB](../../reference/glossary.md#term-asic_db) / [LOGLEVEL_DB](../../reference/glossary.md#term-loglevel_db) / CONFIG_DB への直接書込みは検出されなかった (`ProducerStateTable` / `NotificationProducer` メンバは未保有)。

> **Evidence**: `sonic-swss/orchagent/aclorch.cpp` L25-26 (`m_countersDb` / `m_countersTable`), L45 (`COUNTERS_ACL_COUNTER_RULE_MAP`), L4208-4214 (`m_flex_counter_manager` 初期化), L6020-6048 (`registerFlexCounter` / `deregisterFlexCounter`); 詳細スキャンと grep 結果は `meta/_intermediate/cdb-flow/aclorch-state-side.md` を参照。
<!-- /side-effects -->

<!-- platform -->
## プラットフォーム差 (Phase H)

STATE_DB に書き出される 3 テーブル（`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`）は、[ASIC](../../reference/glossary.md#term-asic) / SAI capability および `platform` / `sub_platform` 環境変数によって書込み内容に差が出る。差は (a) `ACL_STAGE_CAPABILITY_TABLE` のフィールド値に直接現れる差、(b) `ACL_TABLE_TABLE.status` / `ACL_RULE_TABLE.status` の分布に間接的に現れる差、の 2 系統に整理できる。

### プラットフォーム識別文字列 (orch.h:40-50)

| 定数 | 値 |
|------|----|
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` |
| `BRCM_DNX_PLATFORM_SUBSTRING` | `"broadcom-dnx"` (sub_platform) |
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` |
| `VS_PLATFORM_SUBSTRING` | `"vs"` |
| `NPS_PLATFORM_SUBSTRING` | `"nephos"` |
| `CISCO_8000_PLATFORM_SUBSTRING` | `"cisco-8000"` |
| `XS_PLATFORM_SUBSTRING` | `"xsight"` |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` |

### A. `ACL_STAGE_CAPABILITY_TABLE` フィールド値に現れる platform 差

| フィールド | 決定経路 | プラットフォーム別の値 | evidence |
|------------|---------|----------------------|----------|
| `supported_L3V4V6` (INGRESS / EGRESS) | **静的比較** (`m_L3V4V6Capability`) | marvell-prestera / marvell-teralynx / vs → `"true"`、それ以外 → `"false"` | `aclorch.cpp:3515-3533, 4093-4099` |
| `action_list` (INGRESS / EGRESS) | **SAI 動的照会** (`sai_query_attribute_enum_values_capability`) | SAI 成功 → [ASIC](../../reference/glossary.md#term-asic) が返す enum リスト（broadcom / mellanox / barefoot / cisco-8000 等は SDK バージョン依存）。SAI 失敗 → `defaultAclActionsSupported[stage]` ハードコードフォールバック (`aclorch.cpp:168-196`) | `aclorch.cpp:4017-4101, 4104-4118` |
| `is_action_list_mandatory` (INGRESS / EGRESS) | SAI 動的照会 (`AclActionCapabilities::isActionListMandatoryOnTableCreation`) | SAI 戻り値の `boolalpha` 出力。フォールバック時は `"false"` 固定 (`aclorch.h:143` 初期値) | `aclorch.cpp:4056-4101`, `aclorch.h:138-148` |

!!! note "init() 完了時点で必ず 1 回書かれる"
    `AclOrch::init()` は SAI 照会の成否に関わらず、最終的に `putAclActionCapabilityInDB()` で `ACL_STAGE_CAPABILITY_TABLE|INGRESS` / `|EGRESS` の 2 キーを書く。SAI が capability を未実装 (VS / 一部 DPU SAI) でも `defaultAclActionsSupported` でフォールバックされるため、STATE_DB に 2 キー欠如することはない (`aclorch.cpp:3479-3481, 3708, 4017-4118`)。

### B. `ACL_TABLE_TABLE.status` / `ACL_RULE_TABLE.status` に間接的に現れる platform 差

`status` 値そのものは `"Active"` / `"Inactive"` / `"Pending creation"` / `"Pending removal"` の 4 種で platform に依存しないが、各値の発生条件は SAI capability で大きく変わる。代表例:

| platform 条件 | STATE_DB に観測される事象 | evidence |
|---------------|--------------------------|----------|
| `type=MIRRORV6` を未知 platform で作成 | `ACL_TABLE_TABLE|<name>:status="Inactive"` | `aclorch.cpp:3489-3513, 3500-3541` |
| `type=L3V4V6` を marvell-* / vs 以外で作成 | `ACL_TABLE_TABLE|<name>:status="Inactive"` (`validate()` reject) | `aclorch.cpp:2737-2745, 3515-3533` |
| broadcom (非 DNX) `stage=EGRESS` + L4 range match ルール | `ACL_TABLE_TABLE` は `"Active"` だが配下 `ACL_RULE_TABLE` の range match ルールが `"Inactive"` (range フィールド付加されず) | `aclorch.cpp:2608-2628` |
| mellanox / clounix で 17 個目以降の range オブジェクト | `ACL_RULE_TABLE|<table>|<rule>:status="Inactive"` (`return NULL`) | `aclorch.cpp:3370-3378`, `aclorch.h:109-110` |
| SAI リソース枯渇 (全 [ASIC](../../reference/glossary.md#term-asic) 共通だが density により頻度差) | `ACL_RULE_TABLE|...|status="Pending creation"` → retry cache → 他ルール DEL 後に `"Active"` 上書き | `aclorch.cpp:5673-5692, 5710-5721` |
| DTEL action ルールを barefoot / vs 以外で作成 | `DTelOrch` 非起動のため SAI 反映なし、`ACL_RULE_TABLE.status` は `"Inactive"` または該当 action 無視 | `orchdaemon.cpp:502-530` |
| broadcom-dnx `type=PFCWD` | `ACL_TABLE_TABLE|<pfcwd>:status="Active"` (CONFIG_DB `ports` 無視 / SWITCH 単位バインド) | `aclorch.cpp:3811-3830` |

### C. multi-asic / SmartSwitch 環境

- multi-asic 構成では `AclOrch` が namespace (`asic0` / `asic1` / ...) ごとに独立起動し、STATE_DB の 3 テーブルも namespace ごとに独立する。
- 同一 ASIC 種別が標準前提だが、heterogeneous Multi-[NPU](../../reference/glossary.md#term-npu) や [SmartSwitch](../../reference/glossary.md#term-smartswitch) [DPU](../../reference/glossary.md#term-dpu) では namespace 間で `platform` / `sub_platform` が異なる可能性があり、`ACL_STAGE_CAPABILITY_TABLE` の `supported_L3V4V6` / `action_list` が namespace 間で **食い違う** ケースがある。
- `sonic-mgmt-common` (translib) は default namespace を参照する一方、`acl-loader` は namespace 引数を取るため、capability 値の参照先が読み手側で異なる点に注意。

### D. 起動順序による中間状態 (`allPortsReady()` ガード)

`aclorch.cpp:4276` — `doTask()` 冒頭で `gPortsOrch->allPortsReady()` が false の間は `doAclRuleTask()` に到達せず、`ACL_RULE_TABLE` への新規エントリ書込みが発生しない。

- port 数が多い ASIC (broadcom-dnx 高密度シャーシ / cisco-8000 大規模ボード / mellanox 高 radix) では port enumeration に時間がかかり、`ACL_TABLE_TABLE` が `"Active"` を出した後も `ACL_RULE_TABLE` が空のままの中間状態が秒〜分続く。
- [VS](../../reference/glossary.md#term-vs) / 小規模 broadcom では即座に解消されるため、観測される平均待ち時間が ASIC 規模に比例する。

### platform 別 STATE_DB サマリ

| プラットフォーム | `supported_L3V4V6` | `action_list` 取得経路 | DTEL action 反映 | MIRRORV6 reject | range 上限 |
|----------------|--------------------|------------------------|------------------|-----------------|-----------|
| broadcom (非 DNX) | `"false"` | SAI 動的 | no | no | SAI 依存 |
| broadcom-dnx | `"false"` | SAI 動的 | no | no | SAI 依存 |
| mellanox | `"false"` | SAI 動的 | no | no | **16** |
| barefoot | `"false"` | SAI 動的 | **yes** | no | SAI 依存 |
| cisco-8000 | `"false"` | SAI 動的 | no | no | SAI 依存 |
| marvell-prestera | `"true"` | SAI 動的 | no | no | SAI 依存 |
| marvell-teralynx | `"true"` | SAI 動的 | no | no | SAI 依存 |
| nephos | `"false"` | SAI 動的 | no | no | SAI 依存 |
| xsight | `"false"` | SAI 動的 | no | no | SAI 依存 |
| clounix | `"false"` | SAI 動的 | no | no | **16** |
| vs (virtual) | `"true"` | SAI or フォールバック | **yes** | no | SAI 依存 |
| 未知 platform | `"false"` | フォールバック (`defaultAclActionsSupported`) | no | **yes** | SAI 依存 |

> **スキャン証跡**: `AclOrch::init()` L3475–3720 / `queryAclActionCapability()` L4017–4054 / `putAclActionCapabilityInDB()` L4056–4101 / `initDefaultAclActionCapabilities()` L4104–4118 / `defaultAclActionsSupported` L168–196 / `removeAllAcl*Status()` L6116, L6128 / `setAcl*Status()` L6088, L6102 / `orch.h:40-50` / `aclorch.h:109-110, 138-148` / `orchdaemon.cpp:502-530` 全行精読。中間ファイル: `meta/_intermediate/cdb-flow/aclorch-state-platform.md`
<!-- /platform -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

本ページが扱う STATE_DB 3 テーブル (`ACL_TABLE_TABLE` / `ACL_RULE_TABLE` / `ACL_STAGE_CAPABILITY_TABLE`) はいずれも `AclOrch` を**唯一の書き手**とする「書き出し専用のステータスレジスタ」であり、`ProducerStateTable` / `NotificationProducer` を介した PUBLISH 通知は発行されない。consumer 側 (`acl-loader` / `show acl table` / `show acl rule` / `sonic-mgmt-common` translib) は keyspace 通知を購読せず、CLI / REST/[gNMI](../../reference/glossary.md#term-gnmi) 起動契機の **オンデマンド polling** (`HGETALL` 相当) で読み出す。

### Producer/Consumer ペア

| 区間 | 方式 | チャンネル/API |
|------|------|----------------|
| `AclOrch` → STATE_DB `ACL_TABLE_TABLE` | `swss::Table::set()` / `del()` (素の HSET / HDEL / DEL) | なし (PUBLISH 非発行) |
| `AclOrch` → STATE_DB `ACL_RULE_TABLE` | `swss::Table::set()` / `del()` | なし |
| `AclOrch` → STATE_DB `ACL_STAGE_CAPABILITY_TABLE` | `swss::Table::set()` (init で 1 回) | なし |
| `acl-loader` ← STATE_DB `ACL_STAGE_CAPABILITY_TABLE` | `swsssdk.get_all()` (HGETALL polling) | CLI 起動毎 1 回 |
| `show acl table` / `show acl rule` ← STATE_DB | `swsssdk.get_table()` (HGETALL polling) | CLI 起動毎 1 回 |
| `sonic-mgmt-common` (translib) ← `ACL_STAGE_CAPABILITY_TABLE` | translib DB read (HGETALL) | REST/[gNMI](../../reference/glossary.md#term-gnmi) capability クエリ毎 |

### 書込 API: 素の `swss::Table` (Pub/Sub 非対応)

`AclOrch` は STATE_DB の 3 テーブルを `swss::Table` メンバとして保有する（`aclorch.h:706-709`）:

```cpp
// aclorch.h:706-709
Table m_aclStageCapabilityTable;
Table m_aclTableStateTable;
Table m_aclRuleStateTable;
```

初期化は `aclorch.cpp:4200-4202` で stateDb と STATE_DB スキーマ定数文字列を直結する。`ProducerStateTable` のような `_KEY_SET` + `PUBLISH <TABLE>_CHANNEL` 系の通知発行や、`NotificationProducer` 経由の ad-hoc channel `PUBLISH` は一切行わない。書込みは純粋な `HSET` / `HDEL` / `DEL` のみで、戻り値もない。

主な書込ポイント:

- `setAclTableStatus()` → `m_aclTableStateTable.set/del` (`aclorch.cpp:6092, 6098`)
- `setAclRuleStatus()` → `m_aclRuleStateTable.set/del` (`aclorch.cpp:6106, 6112`)
- `putAclActionCapabilityInDB()` → `m_aclStageCapabilityTable.set` (`aclorch.cpp:4101`, init 内で 1 回)
- `removeAllAclTableStatus()` / `removeAllAclRuleStatus()` → `getKeys()` → loop `del()` (`aclorch.cpp:6116-6137`, 起動時のクリア)

### 通知チャンネル

| 経路 | 状態 |
|------|------|
| `<TABLE>_CHANNEL` への `PUBLISH` | **発行されない** (`ProducerStateTable` を保有しない) |
| `NotificationProducer` (`PUBLISH` to ad-hoc channel) | なし (該当メンバ非保有) |
| `__keyspace@<dbId>__:...` keyspace 通知 | Redis サーバの `notify-keyspace-events` 設定次第で発火しうるが、STATE_DB ACL 系の正規 consumer はいずれも購読しない |

### 購読側はすべて polling

正規 consumer は keyspace 通知を購読せず、必要時にのみ `HGETALL` ベースで読み出す:

- `acl-loader` (`sonic-utilities/acl_loader/main.py:88, 533-536`): `statedb.get_all(STATE_DB, "ACL_STAGE_CAPABILITY_TABLE|<stage>")` を実行時に 1 回
- `show acl table` / `show acl rule`: CLI 起動時に sonic-py-swsssdk 経由で STATE_DB を読み出す（イベント駆動ではない）
- `sonic-mgmt-common` (translib): REST/gNMI の capability クエリ受信時に translib DB read 経由で読み出す

CONFIG_DB 側の `ACL_TABLE` / `ACL_RULE` が `AclOrch` 自身に `SubscriberStateTable` (keyspace 通知 + HGETALL) で受信される経路と異なり、STATE_DB 側は完全に非同期通知レス・polling 駆動。

### select() ループとの関係

`AclOrch` は STATE_DB 3 テーブルを**書き手としてのみ**保持し、`addConsumer()` / `addExecutor()` で consumer 登録しない（`orchdaemon.cpp:408-422` の `acl_table_connectors` には STATE_DB connector は含まれず CONFIG_DB 3 + APPL_DB 3 のみ）。`SELECT_TIMEOUT=1000ms` の orchdaemon select ループは STATE_DB 書込みには関与しない。CONFIG_DB / APPL_DB consumer 通知で wake した `doAclTableTask()` / `doAclRuleTask()` の末尾で `setAcl*Status()` が呼ばれる従属的な経路となる。

### retry とバッチ

- STATE_DB 書込み層自体に retry / バッチ機構はない。`swss::Table::set` が Redis 切断で例外送出した場合は orchagent プロセス abort → systemd restart → `init()` 再実行で再構築。
- ACL ルール側の retry cache (`createRetryCache(CFG_ACL_RULE_TABLE_NAME)` / `APP_ACL_RULE_TABLE_NAME`) は CONFIG_DB / APPL_DB consumer に対するもので、retry 後に成功すると `setAclRuleStatus(ACTIVE)` で `"Pending creation"` → `"Active"` を上書きする。

### データフロー図

```
CONFIG_DB / APPL_DB (ACL_TABLE / ACL_RULE)
  ↓ SubscriberStateTable / ConsumerStateTable
orchdaemon select() loop (SELECT_TIMEOUT=1000ms)
  ↓ Consumer::execute() → AclOrch::doTask()
  ↓   doAclTableTask() / doAclRuleTask() / doAclTableTypeTask()
  ↓     → SAI ACL API (create/remove_acl_table/entry)
  ↓     → setAclTableStatus() / setAclRuleStatus()
STATE_DB[ACL_TABLE_TABLE / ACL_RULE_TABLE / ACL_STAGE_CAPABILITY_TABLE]
  ← swss::Table::set/del() のみ (HSET/HDEL/DEL)
  × PUBLISH <TABLE>_CHANNEL なし
  × NotificationProducer なし

consumer 側 (on-demand polling)
  acl-loader / show acl table|rule / sonic-mgmt-common (translib)
    → swsssdk.get_all() / get_table()  ← HGETALL
    (keyspace 通知購読なし)
```

> **Evidence**: `sonic-swss/orchagent/aclorch.h` L706-709（`Table` メンバ宣言、`ProducerStateTable`/`NotificationProducer` 非保有）、`aclorch.cpp` L4200-4202（STATE_DB Table 初期化）、L4087-4101（`putAclActionCapabilityInDB`）、L6088-6098（`setAclTableStatus`）、L6102-6112（`setAclRuleStatus`）、L6116-6137（`removeAllAcl*Status`）。`sonic-swss/orchagent/orchdaemon.cpp` L408-422（`acl_table_connectors` に STATE_DB 側 connector 不在）。`sonic-utilities/acl_loader/main.py` L88, L533-536（`get_all` polling）。`sonic-swss-common/common/schema.h`（`STATE_ACL_*_TABLE_NAME` 定義）。詳細解析は `meta/_intermediate/cdb-flow/aclorch-state-pubsub.md` を参照。

<!-- /pubsub -->

## 引用元

[^1]: sonic-net/[sonic-swss](../../reference/glossary.md#term-sonic-swss) `orchagent/aclorch.cpp` — `setAclTableStatus()` L6088, `setAclRuleStatus()` L6102, `putAclActionCapabilityInDB()` L4056, `init()` L3475

<!-- glossary-links-injected: ca6bc30b1f0e -->
