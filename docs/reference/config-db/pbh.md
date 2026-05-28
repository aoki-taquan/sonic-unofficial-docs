---
title: PBH_TABLE / PBH_RULE テーブル
description: "PBH_TABLE / PBH_RULE テーブル — Policy Based Hashing (PBH) は、packet match 条件ごとに ECMP / LAG hash profile を切り替えるための CONFIG_DB テーブル群。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pbh.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - PBH_TABLE
    - PBH_RULE
    - PBH_HASH
    - PBH_HASH_FIELD
  cli:
    - config pbh
  yang:
    - sonic-pbh
---

# PBH_TABLE / PBH_RULE テーブル

## 概要

Policy Based Hashing (PBH) は、packet match 条件ごとに [ECMP](../../reference/glossary.md#term-ecmp) / [LAG](../../reference/glossary.md#term-lag) hash profile を切り替えるための [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル群。`PBH_TABLE` が適用 interface の集合を定義し、`PBH_RULE` が table 内の match 条件、priority、適用する `PBH_HASH` を持つ[^1]。hash profile と hash field は同じ [YANG](../../reference/glossary.md#term-yang) モジュールの `PBH_HASH` / `PBH_HASH_FIELD` で定義され、実装側のテーブル名定数は `schema.h` も参照する[^2]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>PBH_TABLE")]
  DM["PbhOrch"]
  CDB --> DM
  SAI["SAI<br/>sai_acl_api"]
  DM --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。
<!-- /cdb-mermaid -->

## key 構造

```text
PBH_TABLE|<table_name>
PBH_RULE|<table_name>|<rule_name>
PBH_HASH|<hash_name>
PBH_HASH_FIELD|<hash_field_name>
```

`PBH_RULE.table_name` は `PBH_TABLE.table_name` への leafref。

## 主要フィールド

### PBH_TABLE

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `interface_list` | ordered leaf-list `PORT` / `PORTCHANNEL` leafref | yes | PBH table を適用する interface 群 |
| `description` | string 1..255 | yes | table の説明 |

### PBH_RULE

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `priority` | uint32 | - | rule priority。mandatory |
| `gre_key` | hex value/mask | - | GRE key match |
| `ether_type` | hex uint16 string | - | EtherType match |
| `ip_protocol` | hex uint8 string | - | IPv4 protocol match |
| `ipv6_next_header` | hex uint8 string | - | IPv6 next-header match |
| `l4_dst_port` | hex uint16 string | - | L4 destination port match |
| `inner_ether_type` | hex uint16 string | - | inner EtherType match |
| `hash` | leafref `PBH_HASH.hash_name` | - | 適用する hash。mandatory |
| `packet_action` | enum | `SET_ECMP_HASH` | rule action |
| `flow_counter` | enum | `DISABLED` | packet / byte counter の有効化 |

## 制約

- `PBH_TABLE.interface_list` は 1 要素以上で、`PORT` または `PORTCHANNEL` への leafref。
- `PBH_TABLE.description`、`PBH_RULE.priority`、`PBH_RULE.hash` は mandatory。
- match field の多くは `0x...` 形式、または `0x.../0x...` 形式の文字列 pattern で検証される。
- `PBH_RULE.hash` は `PBH_HASH`、`PBH_HASH.hash_field_list` は `PBH_HASH_FIELD` への leafref。

## 購読者

- `sonic-utilities/scripts/pbh`（CLI 側スクリプト）: [CONFIG_DB](../../reference/glossary.md#term-config_db) の PBH table / rule / hash / hash-field を読み取り、ユーザ向け CLI を提供する（独立した `pbhmgrd` プロセスは master には存在しない）。
- `orchagent` の `PbhOrch` (`sonic-swss/orchagent/pbhorch.cpp`): [CONFIG_DB](../../reference/glossary.md#term-config_db) の PBH 設定を直接 subscribe して [SAI](../../reference/glossary.md#term-sai) hash / [ACL](../../reference/glossary.md#term-acl) 相当のオブジェクトへ反映する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `PBH_HASH`、`PBH_HASH_FIELD`、`PORT`、`PORTCHANNEL`
- 関連 CLI: `config pbh`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-pbh`

<!-- value-behavior -->
## 値依存挙動マトリクス

### PBH_RULE.packet_action

| 値 | [SAI](../../reference/glossary.md#term-sai) 挙動 |
|----|---------|
| `SET_ECMP_HASH` (デフォルト) | マッチパケットに [ECMP](../../reference/glossary.md#term-ecmp) hash profile を適用 |
| `SET_LAG_HASH` | マッチパケットに [LAG](../../reference/glossary.md#term-lag) hash profile を適用 |

### PBH_RULE.flow_counter

| 値 | 挙動 |
|----|------|
| `DISABLED` (デフォルト) | カウンタ無効 |
| `ENABLED` | [ACL](../../reference/glossary.md#term-acl) の packet / byte カウンタを有効化 |

### PBH_HASH_FIELD.hash_field

| 値 | 抽出フィールド |
|----|-------------|
| `INNER_IP_PROTOCOL` | inner IP プロトコル番号 |
| `INNER_L4_DST_PORT` | inner L4 宛先ポート |
| `INNER_L4_SRC_PORT` | inner L4 送信元ポート |
| `INNER_DST_IPV4` | inner 宛先 IPv4 アドレス |
| `INNER_SRC_IPV4` | inner 送信元 IPv4 アドレス |
| `INNER_DST_IPV6` | inner 宛先 IPv6 アドレス |
| `INNER_SRC_IPV6` | inner 送信元 IPv6 アドレス |

ip_mask は IPv4 フィールドの場合 `.` 含む、IPv6 フィールドの場合 `:` 含むアドレスのみ受理 (must 条件)。

<!-- /value-behavior -->

<!-- cdb-exceptions -->
## 例外条件・特殊挙動

<!-- evidence: meta/_intermediate/cdb-flow/pbh.md -->

### YANG スキーマ検証
- `PBH_HASH_FIELD.hash_field`、`sequence_id`、`PBH_RULE.priority`、`PBH_RULE.hash`、`PBH_TABLE.description` は mandatory。
- `ip_mask` は `when` + `must` 条件: IPv4 フィールドに `:` を含む address や IPv6 フィールドに `.` を含む address は reject。
- `PBH_HASH.hash_field_list` は `min-elements 1`。`PBH_TABLE.interface_list` は `min-elements 1`。
- `PBH_RULE.table_name` / `hash` は leafref 参照整合性チェックあり。

### consumer (pbhorch) 例外動作
- 重複 SET: `Failed to create PBH table(%s) in SAI: object already exists` → `return false`。
- type / stage / ports / validate 失敗: 各 `SWSS_LOG_ERROR` + `return false`。
- [SAI](../../reference/glossary.md#term-sai) 能力チェック失敗 (ADD/UPDATE/REMOVE 不対応): `unsupported capabilities` → `return false`。
- DEL で存在しない table: `object doesn't exist` → `return false`。
- `packet_action` 未指定時 default: `SET_ECMP_HASH`。`flow_counter` 未指定時 default: `DISABLED`。

<!-- /cdb-exceptions -->

<!-- failure -->
## 失敗挙動 (Phase D)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-phaseD-failure.md -->

### 不正 match field（`pbhrule.cpp:validateAddMatch`）

`AclRulePbh::validateAddMatch()` は受け付ける SAI attribute を 6 種のみに制限する（`GRE_KEY` / `ETHER_TYPE` / `IP_PROTOCOL` / `IPV6_NEXT_HEADER` / `L4_DST_PORT` / `INNER_ETHER_TYPE`）。それ以外の attribute が渡されると:

```
SWSS_LOG_ERROR("Failed to validate match field: invalid attribute %s", attrName.c_str())
→ return false
```

YANG はこれら match field を optional と定義しており YANG 検証は通過するが、実装ホワイトリストで拒否される（YANG-実装 discrepancy）。

### match field ゼロ / action 数異常（`pbhrule.cpp:validate`）

```cpp
if (m_matches.size() == 0 || m_actions.size() != 1)
    SWSS_LOG_ERROR("Failed to validate rule: invalid parameters")
    → return false
```

match field が 1 つも指定されない PBH_RULE、または action が 1 個でない場合は SAI バリデーション段で reject される。YANG は全 match field を optional として定義するため YANG 検証を通過してしまう。

### SAI create / update 失敗（`pbhorch.cpp`）

| 操作 | 条件 | ログメッセージ |
|------|------|--------------|
| CREATE | 重複 key | `Failed to create PBH rule(%s) in SAI: object already exists` |
| CREATE | priority 設定失敗 | `Failed to configure PBH rule(%s) priority` |
| CREATE | match 設定失敗 | `Failed to configure PBH rule(%s) match: <FIELD>` |
| CREATE | action 設定失敗 | `Failed to configure PBH rule(%s) action` |
| CREATE | validate() 失敗 | `Failed to validate PBH rule(%s)` |
| CREATE | SAI `create_acl_entry` 失敗 | `Failed to create PBH rule(%s) in SAI` |
| UPDATE | key 不在 | `Failed to update PBH rule(%s) in SAI: object doesn't exist` |
| UPDATE | Mellanox action disable 失敗 | `Failed to disable PBH rule(%s) action` |
| UPDATE | SAI set_acl_entry 失敗 | `Failed to update PBH rule(%s) in SAI` |

全ケースで `return false`。エントリは CONFIG_DB に残るが SAI には反映されない。

### SAI capability 超過（`pbhcap.cpp:validatePbhRuleCap`）

プラットフォームが特定フィールドの ADD / UPDATE / REMOVE をサポートしない場合:

```
SWSS_LOG_ERROR("Failed to validate field(%s): capability(%s) is not supported", ...)
→ return false
```

対象フィールド: `priority`, `gre_key`, `ether_type`, `ip_protocol`, `ipv6_next_header`, `l4_dst_port`, `inner_ether_type`, `hash`, `packet_action`, `flow_counter`。ASIC_VENDOR 未設定時は GENERIC へ fallback（`pbhcap.cpp:297-318`）。

### 依存関係未解決（`pbhmgr.cpp:validateDependencies`）

参照先の `PBH_TABLE` または `PBH_HASH` が CONFIG_DB に存在しない場合、`validateDependencies()` が `false` を返し、RULE は `pendingSetupMap` に留まって retry loop に入る（サイレント待機、エラーログなし）。依存が解決されるまで SAI への反映はされない。

### parse 失敗（`pbhmgr.cpp`）

| 条件 | ログメッセージ |
|------|--------------|
| 空文字列 | `Failed to parse field(%s): empty value is prohibited` |
| 不正 hex 文字列 | `Failed to parse field(%s): invalid value(%s)` |
| 数値変換例外 | `Failed to parse field(%s): <exception message>` |
| `gre_key` フォーマット不正 | `invalid_argument` 例外（`0x.../0x...` 形式必須） |

<!-- /failure -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [YANG](../../reference/glossary.md#term-yang): [`sonic-pbh`](../yang/sonic-pbh.md)
- CLI: `config pbh`

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-pbh.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-pbh.yang>
[^2]: テーブル名定数参照: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `PBH_TABLE|<name>`、`PBH_RULE|<table>|<rule>`、`PBH_HASH|<hash>`、`PBH_HASH_FIELD|<field>`。
- match field は `0x...` / `0x.../0x...` (mask 付) の hex 文字列。
- `packet_action=SET_ECMP_HASH` が一般的。

### よくある誤設定

- `priority` が他 rule と衝突して評価順序が予測不能。
- `hash` フィールドに未定義の `PBH_HASH` を指定し leafref エラー。
- `interface_list` に未登録の `PORTCHANNEL` を入れる。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'PBH_*'
show pbh table
show pbh rule
show pbh statistics
```
<!-- /ops-hint -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **[orchagent](../../reference/glossary.md#term-orchagent) / PbhOrch** (`sonic-swss/orchagent/pbhorch.cpp`): `PBH_TABLE`, `PBH_RULE`, `PBH_HASH`, `PBH_HASH_FIELD` を `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL 翻訳

- PbhOrch が各テーブルのエントリを内部データ構造に格納し、依存関係 (HASH_FIELD → HASH → TABLE → RULE) を解決。
- APP_DB への書き込みなし ([orchagent](../../reference/glossary.md#term-orchagent) から直接 SAI)。

### 段階 3: APPL → SAI

- PbhOrch が `sai_hash_api->create_hash()` / `sai_acl_api->create_acl_entry()` を呼び出してポリシーベースハッシュを設定。
- 依存する HASH オブジェクトが未作成の場合は `task_need_retry`。

### 段階 4: タイミング + 副作用

- 依存関係が揃ったエントリから順次 SAI に反映。HASH_FIELD → HASH → RULE の順で処理。
- 副作用: PBH RULE が [ACL](../../reference/glossary.md#term-acl) テーブルと競合する場合 SAI が resource 不足エラーを返す可能性。

<!-- /runtime-trace -->
<!-- entry-points -->
## 書き込み入り口 (Direction A)

PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config pbh table/rule/hash/hash-field add/del/update ...` — `config/plugins/pbh.py` が `set_entry()` を呼ぶ ([sonic-utilities](../../reference/glossary.md#term-sonic-utilities)/config/plugins/pbh.py)

### minigraph / sonic-cfggen

minigraph.py に PBH テーブル生成なし

### REST / gNMI

REST/[gNMI](../../reference/glossary.md#term-gnmi) 書き込み経路なし

### db_migrator

db_migrator.py での PBH マイグレーションなし

### ビルド時デフォルト (build-time default)

なし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

なし
<!-- /entry-points -->

<!-- defaults -->
## 暗黙デフォルト・ハードコード挙動 (Phase A)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-table-defaults.md -->
<!-- evidence: meta/_intermediate/cdb-flow/pbh-rule-defaults.md -->
<!-- evidence: meta/_intermediate/cdb-flow/pbh-hash-defaults.md -->

### PBH_TABLE フィールド別デフォルト

| フィールド | YANG 定義 | 実装デフォルト | 備考 |
|---|---|---|---|
| `interface_list` | `leaf-list; min-elements 1; leafref PORT\|PORTCHANNEL` | **なし** (mandatory) | 空リスト → parse error。重複 interface は `unordered_set` で dedup + SWSS_LOG_WARN のみ (error にならない) |
| `description` | `mandatory true; string length 1..255` | **なし** (mandatory) | 空文字列 → parse error |

- 未知フィールドは `SWSS_LOG_WARN("Unknown field(%s): skipping ...")` でサイレントスキップ (error にならない)
- YANG-実装 discrepancy: なし (両フィールドとも YANG mandatory/min-elements と実装が一致)

### PBH_RULE フィールド別デフォルト

| フィールド | YANG default | 実装デフォルト (pbhmgr.cpp `validatePbhRule`) | 備考 |
|---|---|---|---|
| `packet_action` | `SET_ECMP_HASH` | `SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID` を注入 + fieldValueMap 書き戻し | YANG default と一致。未指定でも `SWSS_LOG_NOTICE` のみ |
| `flow_counter` | `DISABLED` | `false` (bool) を注入 + `"DISABLED"` を fieldValueMap 書き戻し | AclRulePbh(…, createCounter=false) で構築 |

### ハードコード mask (YANG 記述なし)

`pbhmgr.cpp` の parse 関数内で、以下フィールドは CONFIG_DB から値のみ受け取り、mask をコードで固定注入する。YANG 側にマスク仕様の記述はない (YANG-実装 discrepancy)。

| フィールド | 注入 mask | SAI attr |
|---|---|---|
| `ether_type` | `0xFFFF` | `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` |
| `ip_protocol` | `0xFF` | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` |
| `ipv6_next_header` | `0xFF` | `SAI_ACL_ENTRY_ATTR_FIELD_IPV6_NEXT_HEADER` |
| `l4_dst_port` | `0xFFFF` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT` |
| `inner_ether_type` | `0xFFFF` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_ETHER_TYPE` |

`gre_key` のみ `value/mask` の 2 値をユーザが明示指定する (YANG パターン `0x.../0x...`)。

### SAI implicit constraint (YANG 非記述)

`AclRulePbh::validate()` は `m_matches.size() == 0 || m_actions.size() != 1` で fail する。つまり：

- **match field が 1 つも設定されない PBH_RULE は SAI バリデーションで reject** される
- YANG 側にこの制約の記述はなく、YANG は全 match field を optional として定義する

### PBH_HASH フィールド別デフォルト

| フィールド | YANG 定義 | 実装デフォルト | 備考 |
|---|---|---|---|
| `hash_field_list` | `leaf-list; min-elements 1; ordered-by user; leafref PBH_HASH_FIELD` | **なし** (mandatory) | 空リスト → `validatePbhHash` が `SWSS_LOG_ERROR` + `return false`。重複エントリは `unordered_set` で dedup + SWSS_LOG_WARN のみ |

- 未知フィールドは `SWSS_LOG_WARN("Unknown field(%s): skipping ...")` でサイレントスキップ
- YANG-実装 discrepancy: なし (`min-elements 1` と実装が一致)

### PBH_HASH_FIELD フィールド別デフォルト

| フィールド | YANG 定義 | 実装デフォルト (pbhmgr.cpp `validatePbhHashField`) | 備考 |
|---|---|---|---|
| `hash_field` | `mandatory true; enum INNER_IP_PROTOCOL\|INNER_L4_*\|INNER_*_IPV4\|INNER_*_IPV6` | **なし** (mandatory) | 未設定 → `SWSS_LOG_ERROR` + `return false` |
| `ip_mask` | `when hash_field is IP addr type; inet:ip-address-no-zone` | **なし** (条件付き必須) | `hash_field` が `INNER_DST/SRC_IPV4/6` のとき必須; 非 IP フィールドで設定すると `isIpv4/6MaskRequired` が false → validation error。未設定でも `sequence_id` があれば通過 |
| `sequence_id` | `mandatory true; uint32` | **なし** (mandatory) | 未設定 → `SWSS_LOG_ERROR` + `return false`。同値を複数フィールドで使用可能 (uniqueness 制約なし) |

- 非 IP フィールド (`INNER_IP_PROTOCOL`, `INNER_L4_DST_PORT`, `INNER_L4_SRC_PORT`) に `ip_mask` を設定するとエラー
- `ip_mask` の IPv4/IPv6 混在も YANG `must` 条件でエラー (`.` 含むなら IPv4 フィールド専用、`:` 含むなら IPv6 フィールド専用)
- YANG-実装 discrepancy: なし

### dead update: PBH_HASH_FIELD

`updatePbhHashField()` は常に `return false` (エラーログ: `"update is prohibited"`)。`PBH_HASH_FIELD` の変更は削除後に再作成が必要。

### 書込み順依存 (dependency retry)

`deployPbhTasks()` は `HASH_FIELD → HASH → TABLE → RULE` の順で setup する。CONFIG_DB に RULE だけ先に書いた場合 `validateDependencies(rule)` が false を返し、RULE は `pendingSetupMap` に留まって retry loop に入る。

### プラットフォーム依存 (Mellanox W/A)

`ASIC_VENDOR=mellanox` 時のみ、`updatePbhRule` 中に `hash` または `packet_action` を変更すると `disableAction()` で既存 ACL action を先に disable してから `updateAclRule` を呼ぶ。GENERIC platform にはこの処理なし。ASIC_VENDOR 未設定時は GENERIC へ fallback (`pbhcap.cpp:296-303`)。

<!-- /defaults -->

<!-- derivation -->
## 派生・条件付き登録 (Phase 6/7)

### Phase 6: 自動派生

minigraph.py および init_cfg.json.j2 からの `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` 自動派生はなし。CLI (`config pbh`) による手動設定のみ。

### Phase 7: 条件付き登録

| 条件 | 影響 | ソース |
|---|---|---|
| `PbhOrch` は常時登録 (platform 非依存) | PBH 全テーブル (TABLE/RULE/HASH/HASH_FIELD) を無条件で購読 | `orchdaemon.cpp:553-565` |
| `PbhOrch` は `gAclOrch` と `gPortsOrch` に依存 | AclOrch が作成された後に PbhOrch が生成される | `orchdaemon.cpp:565` |

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| PbhOrch 登録 | 2 | `orchdaemon.cpp:553-565` |
| cfgDbPbhTableConnectorList 構築 | 4 | `orchdaemon.cpp:553-556` |

<!-- /derivation -->

<!-- handler-branching -->
### Phase 8: Handler メソッド内分岐

`PbhOrch` の処理分岐 (テーブル名ディスパッチ):

| Handler | メソッド | 分岐条件 | 効果 | evidence |
|---|---|---|---|---|
| `PbhOrch` | `doTask()` | `table_name == CFG_PBH_TABLE_TABLE_NAME` | PBH テーブル (ACL グループ) の作成/削除 | `sonic-swss/orchagent/pbhorch.cpp` |
| `PbhOrch` | `doTask()` | `table_name == CFG_PBH_RULE_TABLE_NAME` | PBH ルールの作成/削除。`packet_action` / `flow_counter` 分岐あり | `sonic-swss/orchagent/pbhorch.cpp` |
| `PbhOrch` | `doTask()` | `table_name == CFG_PBH_HASH_TABLE_NAME` | PBH ハッシュオブジェクトの作成/削除 | `sonic-swss/orchagent/pbhorch.cpp` |
| `PbhOrch` | `doTask()` | `table_name == CFG_PBH_HASH_FIELD_TABLE_NAME` | PBH ハッシュフィールドの作成/削除。`hash_field` enum によりSAI attr が決まる | `sonic-swss/orchagent/pbhorch.cpp` |
| `PbhOrch` | `addPbhRule()` | `flow_counter == "ENABLED"` | SAI カウンタオブジェクトを追加でアタッチ | `sonic-swss/orchagent/pbhorch.cpp` |

> **スキャン証跡**: `orchdaemon.cpp:553-565` および `pbhorch.cpp` を確認、5 件分岐抽出。PBH は minigraph 非依存を確認 — 誤読なし。

<!-- /handler-branching -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

`PbhOrch` は `Orch` 基底クラス経由で `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` の 4 テーブルを購読する。すべて CONFIG_DB 起源のため `Orch::addConsumer()` の DB 種別分岐で **`SubscriberStateTable`** が選ばれ、[Redis](../../reference/glossary.md#term-redis) の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>:*` の PSUBSCRIBE) を購読する。channel ベースの `PUBLISH` は使用しない。

| 項目 | 値 |
|------|-----|
| 購読クラス | `SubscriberStateTable` (CONFIG_DB 分岐) |
| keyspace パターン | `__keyspace@4__:PBH_TABLE:*`、`__keyspace@4__:PBH_RULE:*`、`__keyspace@4__:PBH_HASH:*`、`__keyspace@4__:PBH_HASH_FIELD:*` (CONFIG_DB dbId=4) |
| key 区切り | `PBH_TABLE\|<name>` / `PBH_RULE\|<table>\|<rule>` 等 (TableNameSeparator 既定 `\|`) |
| POP_BATCH_SIZE | `TableConsumable::DEFAULT_POP_BATCH_SIZE` = **128** (`sonic-swss-common/common/table.h:164`) |
| 優先度 (`pri`) | 0 (`TableConnector` 既定) |
| 起動時スナップショット | `SubscriberStateTable` が既存エントリを SET イベントとして再配信 |
| TTL | 未設定 (CONFIG_DB は永続前提) |
| ディスパッチ | `Consumer::execute()` → `PbhOrch::doTask(Consumer&)` → `consumer.getTableName()` 分岐 → 各 `doPbhXxxTask(consumer)` |

### ディスパッチ詳細

`PbhOrch::doTask()` は `consumer.getTableName()` により 4 テーブルを分岐し、処理後に `deployPbhTasks()` を呼んで依存関係解消ループを回す:

```
PbhOrch::doTask(Consumer &consumer)          // pbhorch.cpp:1804
  → tableName == CFG_PBH_TABLE_TABLE_NAME    → doPbhTableTask(consumer)
  → tableName == CFG_PBH_RULE_TABLE_NAME     → doPbhRuleTask(consumer)
  → tableName == CFG_PBH_HASH_TABLE_NAME     → doPbhHashTask(consumer)
  → tableName == CFG_PBH_HASH_FIELD_TABLE_NAME → doPbhHashFieldTask(consumer)
  → [unknown]                                SWSS_LOG_ERROR
  → deployPbhTasks()                         依存関係解消ループ
```

### CONFIG_DB → SAI 経路

CONFIG_DB への書き込みは `sonic-utilities` の `config pbh` CLI (`config/plugins/pbh.py`) が `set_entry()` を呼ぶのみ。`orchagent` は APP_DB を経由せず、`PbhOrch` が CONFIG_DB から直接 SAI へ反映する:

```
config pbh → HSET CONFIG_DB PBH_RULE|<table>|<rule> ...
  → Redis keyspace 通知
  → SubscriberStateTable.pops() (batch=128)
  → PbhOrch::doTask() → doPbhRuleTask()
  → AclRulePbh::validate() + sai_acl_api->create_acl_entry()
```

- APP_DB への書き込みなし ([orchagent](../../reference/glossary.md#term-orchagent) 直接 SAI)。
- `allPortsReady()` が false の場合、`PbhOrch::doTask()` は即 return して処理をスキップする。

<!-- evidence: sonic-net/sonic-swss/orchagent/pbhorch.cpp:88-97 (PbhOrch::PbhOrch — Orch(connectorList)) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/pbhorch.cpp:1804-1838 (PbhOrch::doTask — getTableName 分岐 + deployPbhTasks) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orchdaemon.cpp:553-565 (TableConnector 構築 + gPbhOrch 生成) -->
<!-- evidence: sonic-net/sonic-swss/orchagent/orch.cpp (Orch::addConsumer — CONFIG_DB → SubscriberStateTable 分岐) -->
<!-- evidence: sonic-net/sonic-swss-common/common/table.h:164 (DEFAULT_POP_BATCH_SIZE = 128) -->
<!-- /pubsub -->

<!-- constants -->
## ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/pbh/pbhschema.h`、`pbhmgr.cpp`、`pbhrule.cpp`

### PBH_RULE.priority — 有効範囲

| 項目 | 値 | 根拠 |
|------|----|------|
| 型 | `sai_uint32_t` | `pbhmgr.cpp:506` `to_uint<sai_uint32_t>(value)` |
| 有効範囲 | `0` – `4294967295` (uint32 全域) | YANG `type uint32`、実装側に上限チェックなし |
| YANG 定義 | `type uint32; mandatory true` | `sonic-pbh.yang:153-156` |

> YANG / 実装ともに上限は uint32 最大値。実際の SAI 実装が受け入れる上限はプラットフォーム依存だが、ソースコード上の制限は uint32 範囲のみ。

### PBH_RULE.ether_type / inner_ether_type — enum 代表値

`ether_type` / `inner_ether_type` は `0x...` 形式の uint16 hex 文字列。ハードコード mask は `0xFFFF` (exact match)。実装上の代表的な値:

| 値 (hex) | プロトコル | 備考 |
|----------|-----------|------|
| `0x0800` | IPv4 | RFC 791 |
| `0x86DD` | IPv6 | RFC 2460 |
| `0x8847` | [MPLS](../../reference/glossary.md#term-mpls) unicast | RFC 3032 |
| `0x0806` | [ARP](../../reference/glossary.md#term-arp) | RFC 826 |

`ether_type` mask は `pbhmgr.cpp:558` で `0xFFFF` に固定注入 (YANG 非記述)。

### PBH_RULE.ip_protocol — enum 代表値

`ip_protocol` は `0x...` 形式の uint8 hex 文字列。ハードコード mask は `0xFF` (exact match)。

| 値 (hex) | プロトコル番号 (dec) | 用途 |
|----------|---------------------|------|
| `0x04` | 4 | IPv4-in-IPv4 |
| `0x11` | 17 | UDP |
| `0x06` | 6 | TCP |
| `0x2F` | 47 | GRE |
| `0x3B` | 59 | IPv6 No Next Header |

`ip_protocol` mask は `pbhmgr.cpp:583` で `0xFF` に固定注入 (YANG 非記述)。

### SAI acl_entry_attr マッピング

`pbhrule.cpp` の `validateAddMatch` / `validateAddAction` で使用する SAI 属性:

| CONFIG_DB フィールド | SAI acl_entry_attr | 方向 |
|--------------------|--------------------|------|
| `gre_key` | `SAI_ACL_ENTRY_ATTR_FIELD_GRE_KEY` | match |
| `ether_type` | `SAI_ACL_ENTRY_ATTR_FIELD_ETHER_TYPE` | match |
| `ip_protocol` | `SAI_ACL_ENTRY_ATTR_FIELD_IP_PROTOCOL` | match |
| `ipv6_next_header` | `SAI_ACL_ENTRY_ATTR_FIELD_IPV6_NEXT_HEADER` | match |
| `l4_dst_port` | `SAI_ACL_ENTRY_ATTR_FIELD_L4_DST_PORT` | match |
| `inner_ether_type` | `SAI_ACL_ENTRY_ATTR_FIELD_INNER_ETHER_TYPE` | match |
| `packet_action=SET_ECMP_HASH` | `SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID` | action |
| `packet_action=SET_LAG_HASH` | `SAI_ACL_ENTRY_ATTR_ACTION_SET_LAG_HASH_ID` | action |

match field が 0 件、または action が 1 件以外の場合は `AclRulePbh::validate()` で reject (`pbhrule.cpp:84-90`)。

### pbhschema.h 文字列定数

```c
// packet_action 値
#define PBH_RULE_PACKET_ACTION_SET_ECMP_HASH "SET_ECMP_HASH"
#define PBH_RULE_PACKET_ACTION_SET_LAG_HASH  "SET_LAG_HASH"

// flow_counter 値
#define PBH_RULE_FLOW_COUNTER_ENABLED  "ENABLED"
#define PBH_RULE_FLOW_COUNTER_DISABLED "DISABLED"
```

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-side-effects.md -->

### ASIC_DB への書込

PbhOrch → AclOrch → SAI API 経路で [syncd](../../reference/glossary.md#term-syncd) が [ASIC_DB](../../reference/glossary.md#term-asic_db) にオブジェクトを書き込む。直接の [ASIC_DB](../../reference/glossary.md#term-asic_db) アクセスは [syncd](../../reference/glossary.md#term-syncd) 経由。

| 操作 | SAI API | [ASIC_DB](../../reference/glossary.md#term-asic_db) オブジェクト型 | 契機 |
|---|---|---|---|
| PBH_TABLE ADD | `aclOrch->addAclTable()` → `sai_acl_api->create_acl_table()` | `SAI_OBJECT_TYPE_ACL_TABLE` | `PBH_TABLE` SET イベント |
| PBH_RULE ADD | `aclOrch->addAclRule()` → `sai_acl_api->create_acl_entry()` | `SAI_OBJECT_TYPE_ACL_ENTRY` | `PBH_RULE` SET イベント (依存オブジェクト揃い次第) |
| PBH_HASH ADD | `sai_hash_api->create_hash()` | `SAI_OBJECT_TYPE_HASH` | `PBH_HASH` SET イベント |
| PBH_HASH_FIELD ADD | `sai_hash_api->create_fine_grained_hash_field()` | `SAI_OBJECT_TYPE_FINE_GRAINED_HASH_FIELD` | `PBH_HASH_FIELD` SET イベント |
| flow_counter=ENABLED | `sai_acl_api->create_acl_counter()` | `SAI_OBJECT_TYPE_ACL_COUNTER` | PBH_RULE で `flow_counter=ENABLED` 時のみ |

証跡: `pbhorch.cpp:286`（addAclTable）、`pbhorch.cpp:633`（addAclRule）、`pbhorch.cpp:1054`（create_hash）、`aclorch.cpp:1937`（create_acl_counter）

### COUNTERS_DB への書込

`flow_counter=ENABLED` の PBH_RULE のみ、`AclOrch::registerFlexCounter()` を通じて [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に書き込む。

| [COUNTERS_DB](../../reference/glossary.md#term-counters_db) キー | 内容 | 書込タイミング |
|---|---|---|
| `ACL_COUNTER_RULE_MAP` | `"<table_name>|<rule_name>"` → `<acl_counter_oid>` | `flow_counter=ENABLED` の PBH_RULE が addAclRule → createCounter 成功後 |
| [FlexCounter](../../reference/glossary.md#term-flexcounter) 登録 | `CounterType::ACL_COUNTER` として packet / byte カウンタ属性を登録 | 同上 (`show pbh statistics` に表示) |

DEL 時: `aclOrch->deregisterFlexCounter()` が `ACL_COUNTER_RULE_MAP` からエントリ削除 + [FlexCounter](../../reference/glossary.md#term-flexcounter) 解除。

証跡: `aclorch.cpp:6041`（hset ACL_COUNTER_RULE_MAP）、`aclorch.cpp:6047`（hdel DEL 時）、`aclorch.cpp:6040`（flex_counter_manager 登録）

### flow_counter=DISABLED（デフォルト）時

`AclRulePbh` は `createCounter=false` で構築 (`pbhorch.cpp:499`)。ACL_COUNTER SAI オブジェクトは作成されず、[COUNTERS_DB](../../reference/glossary.md#term-counters_db) への書込は発生しない。

### 副次書込サマリ

```
PBH_RULE (flow_counter=ENABLED)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_ENTRY  (via sai_acl_api->create_acl_entry)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_COUNTER (via sai_acl_api->create_acl_counter)
  └─► COUNTERS_DB: ACL_COUNTER_RULE_MAP["<table>|<rule>"] = <counter_oid>
  └─► FlexCounter: CounterType::ACL_COUNTER 登録 (show pbh statistics に表示)

PBH_RULE (flow_counter=DISABLED / デフォルト)
  └─► ASIC_DB: SAI_OBJECT_TYPE_ACL_ENTRY のみ
  └─► COUNTERS_DB: 書込なし
```

<!-- /side-effects -->

<!-- ordering -->
## オブジェクト生成順序・依存関係 (Phase B)

### CONFIG_DB 書き込み順序の要件

`PbhOrch::deployPbhTasks()` (`sonic-swss/orchagent/pbhorch.cpp:1539-1550`) は毎回以下の順序で pending タスクを処理する。

**Setup (作成) 順序**:

```
PBH_HASH_FIELD → PBH_HASH → PBH_TABLE → PBH_RULE
```

**Remove (削除) 順序** (Setup と逆順):

```
PBH_RULE → PBH_TABLE → PBH_HASH → PBH_HASH_FIELD
```

### 依存関係の詳細

| オブジェクト | 依存先 | 依存チェック関数 | 未解決時の挙動 |
|---|---|---|---|
| `PBH_RULE` | `PBH_TABLE` (table_name leafref) + `PBH_HASH` (hash leafref) | `validateDependencies(PbhRule)` (`pbhmgr.cpp:81-98`) | `pendingSetupMap` に留まり retry ループ (`pbhorch.cpp:943`) |
| `PBH_HASH` | `PBH_HASH_FIELD` (hash_field_list の各エントリ) | `validateDependencies(PbhHash)` (`pbhmgr.cpp:99-113`) | `pendingSetupMap` に留まり retry ループ (`pbhorch.cpp:1241`) |
| `PBH_TABLE` | なし (PORT / PORTCHANNEL は leafref だが portsOrch 経由で確認) | — | `allPortsReady()` が false の間は `doTask()` 自体が early return |
| `PBH_HASH_FIELD` | なし | — | 即時 SAI 作成 |

### SAI 呼び出し順序

1. `sai_hash_api->create_fine_grained_hash_field()` — `PBH_HASH_FIELD` ごと (`pbhorch.cpp:1369`)
2. `sai_hash_api->create_hash()` — `PBH_HASH` ごと、hash_field OID リストを付与 (`pbhorch.cpp:1054`)
3. ACL table 作成 (AclOrch 経由) — `PBH_TABLE` ごと
4. `sai_acl_api->create_acl_entry()` — `PBH_RULE` ごと、SAI ACL match + `ACTION_SET_ECMP_HASH_ID` / `ACTION_SET_LAG_HASH_ID` を設定 (`pbhorch.cpp:515-595`)

### 削除時の参照カウント保護

- `PBH_TABLE` / `PBH_HASH` / `PBH_HASH_FIELD` は `refCount > 0` の間削除不可 (`hasDependencies()` が true → retry)。
- `PBH_RULE` 削除時に `decRefCount(rule)` が `PBH_TABLE` と `PBH_HASH` の参照カウントを減算 (`pbhmgr.cpp:163-185`)。
- `PBH_HASH` 削除時に `decRefCount(hash)` が各 `PBH_HASH_FIELD` の参照カウントを減算 (`pbhmgr.cpp:187-210`)。

> **証跡**: `pbhorch.cpp:1539-1550` (deployPbhTasks), `pbhmgr.cpp:81-113` (validateDependencies), `pbhorch.cpp:943, 1241` (retry log)

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-cross-refs.md -->

`PBH_TABLE.interface_list` に記載されたインターフェース名は CONFIG_DB 上では文字列だが、
`PbhOrch` が `AclTable::validateAddPorts()` → `gPortsOrch->getPort()` を通じて以下のテーブルの
エントリを**暗黙的に参照**する。YANG の leafref チェックとは独立したコードレベルの依存。

| 参照元フィールド | 参照先テーブル | 参照先キー形式 | SAI バインド種別 | 参照箇所 |
|---|---|---|---|---|
| `PBH_TABLE.interface_list` | `PORT` | `PORT\|EthernetN` | `SAI_ACL_BIND_POINT_TYPE_PORT` | `pbhorch.cpp:266-268`, `aclorch.cpp:2698` |
| `PBH_TABLE.interface_list` | `PORTCHANNEL` | `PORTCHANNEL\|PortChannelN` | `SAI_ACL_BIND_POINT_TYPE_LAG` | `pbhorch.cpp:266-268`, `aclorch.cpp:106` |
| `PBH_RULE.table_name` | `PBH_TABLE` | `PBH_TABLE\|<table_name>` | N/A (依存エントリ存在チェック) | `pbhmgr.cpp` `deployPbhTasks()` |
| `PBH_RULE.hash` | `PBH_HASH` | `PBH_HASH\|<hash_name>` | N/A (依存エントリ存在チェック) | `pbhmgr.cpp` `validateDependencies()` |

### 解決タイミング

- `interface_list` に指定したポートが PortsOrch 未登録の場合、`pendingPortSet` に保留され
  PortsOrch の `SUBJECT_TYPE_PORT_CHANGE` 通知で再バインドを試みる (`aclorch.cpp:2698-2703`)。
- `PBH_RULE.table_name` が指す `PBH_TABLE` エントリが未作成の場合、RULE は `pendingSetupMap` に
  留まり retry loop に入る (`deployPbhTasks()` — `HASH_FIELD → HASH → TABLE → RULE` 順序依存)。
- `PBH_RULE.hash` が指す `PBH_HASH` エントリが未作成の場合も同様に retry。

### コンストラクタレベル依存

`PbhOrch` は `AclOrch *` と `PortsOrch *` をコンストラクタ引数に受け取り (`pbhorch.cpp:90-91`)、
これらのオーケストレータが先に初期化されていることを前提とする。
`orchdaemon.cpp:553-565` で AclOrch / PortsOrch 作成後に PbhOrch を生成する順序が保証されている。

<!-- /cross-refs -->

<!-- platform -->
## プラットフォーム差異 (Phase H)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-phaseH-platform.md -->

### ASIC ベンダー検出と capability ロード

`PbhCapabilities` は起動時に環境変数 `ASIC_VENDOR` を読み取り、対応する `PbhVendorFieldCapabilities` サブクラスをロードする (`pbhcap.cpp:310-335`)。`ASIC_VENDOR` 未設定または不明値の場合は `generic` へ fallback し、`SWSS_LOG_WARN` を出力する。

現在サポートするベンダー:

| `ASIC_VENDOR` 値 | ロードされるクラス | [STATE_DB](../../reference/glossary.md#term-state_db) `PBH_CAPABILITIES` へ書込 |
|---|---|---|
| `generic` (またはその他 / 未設定) | `PbhGenericFieldCapabilities` | あり (各フィールドの ADD/UPDATE/REMOVE 組み合わせ) |
| `mellanox` | `PbhMellanoxFieldCapabilities` | あり (同上) |

### フィールド別 capability 対照表

以下の通り `ASIC_VENDOR` によって ADD / UPDATE / REMOVE の可否が変わる。空欄は "いずれも不可"。

#### PBH_TABLE

| フィールド | Generic | Mellanox |
|---|---|---|
| `interface_list` | UPDATE | UPDATE |
| `description` | UPDATE | UPDATE |

#### PBH_RULE

| フィールド | Generic | Mellanox |
|---|---|---|
| `priority` | UPDATE | UPDATE |
| `gre_key` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `ether_type` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `ip_protocol` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `ipv6_next_header` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `l4_dst_port` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `inner_ether_type` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `hash` | UPDATE | UPDATE |
| `packet_action` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |
| `flow_counter` | ADD, UPDATE, REMOVE | ADD, UPDATE, REMOVE |

#### PBH_HASH

| フィールド | Generic | Mellanox |
|---|---|---|
| `hash_field_list` | UPDATE | **(空: 不可)** |

> **Mellanox 固有制約**: `PBH_HASH.hash_field_list` の ADD / UPDATE / REMOVE がすべて無効。`hash_field_list` の変更は capability チェックで拒否され `SWSS_LOG_ERROR("Failed to validate field(hash_field_list): capability(UPDATE/ADD/REMOVE) is not supported")` が記録される。

#### PBH_HASH_FIELD

`PbhHashFieldCapabilities` のフィールド (`hash_field`, `ip_mask`, `sequence_id`) はいずれのベンダーも明示的な capability 登録なし (`PbhVendorFieldCapabilities::hashField` が未初期化のまま) → 事実上 ADD のみ許可 (`updatePbhHashField()` は常に `return false` により UPDATE 禁止)。

### Mellanox W/A: PBH_RULE update 時の action disable

`ASIC_VENDOR=mellanox` かつ `updatePbhRule` の変更フィールドに `hash` または `packet_action` が含まれる場合、`pbhorch.cpp:839-863` にてワークアラウンドを実施:

1. `AclRulePbh::disableAction()` で既存 ACL entry の action attr を先に無効化
2. その後 `aclOrch->updateAclRule()` を呼び出す

GENERIC platform ではこの処理は行われず、直接 `updateAclRule()` を呼ぶ。

### VOQ / chassis

`sonic-swss/orchagent/pbh/` ディレクトリに [VOQ](../../reference/glossary.md#term-voq) chassis 固有コードは存在しない。`PbhOrch` は `orchdaemon.cpp` で unconditionally 生成されており、[VOQ](../../reference/glossary.md#term-voq) / non-[VOQ](../../reference/glossary.md#term-voq) の分岐なし。

### capability の STATE_DB 書き込み

`PbhCapabilities::writePbhVendorCapabilitiesToDb()` が起動時に `STATE_DB:PBH_CAPABILITIES` へ各フィールドの capability 文字列 (`ADD`, `UPDATE`, `REMOVE` のカンマ区切り) を書き込む。確認コマンド:

```bash
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|rule'
sonic-db-cli STATE_DB hgetall 'PBH_CAPABILITIES|hash'
```

<!-- /platform -->

<!-- glossary-links-injected: 32758c44ab11 -->
