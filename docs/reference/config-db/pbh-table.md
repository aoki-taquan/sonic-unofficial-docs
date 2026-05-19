---
title: PBH_TABLE テーブル
description: "PBH_TABLE テーブル — Policy Based Hashing の適用 interface 集合を定義する CONFIG_DB テーブル。PBH_RULE / PBH_HASH / PBH_HASH_FIELD と組み合わせ ECMP / LAG hash profile を切り替える。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-16
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/pbhorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/pbh/pbhmgr.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pbh.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
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

# PBH_TABLE テーブル

## 概要

`PBH_TABLE` は [Policy Based Hashing (PBH)](pbh.md) で「どの interface 群に hash policy を適用するか」を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル。`PbhOrch` が SAI [ACL](../../reference/glossary.md#term-acl) テーブル (`ACL_STAGE_INGRESS`) として展開し、各 `PBH_RULE` がこのテーブル内のエントリとして bind される[^1]。

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

<!-- ordering -->
## オブジェクト生成順序・依存関係 (Phase B)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-table-ordering.md -->

`PBH_TABLE` 自体は他の PBH テーブルに対する上流依存を持たないが、参照する `PORT` / `PORTCHANNEL` の PortsOrch 初期化を必要とする。`PBH_RULE` はこのテーブルに依存するため、**作成は PBH_RULE より前**、**削除は PBH_RULE より後**が必須。

### `deployPbhTasks()` の固定処理順序

`deployPbhTasks()` (`pbhorch.cpp:1539-1550`) は毎回以下の固定順で pending map を処理する。

```
Setup (作成): HASH_FIELD → HASH → TABLE → RULE
Remove (削除): RULE → TABLE → HASH → HASH_FIELD
```

`PBH_TABLE` の setup は `PBH_HASH` 完了後、`PBH_RULE` より前に実行される。

### 依存 1: PortsOrch 初期化（必須先行・グローバル）

```
PortsOrch::allPortsReady() == true  先行
  ↓
PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD の全 SET 処理開始
```

`PbhOrch::doTask()` (`pbhorch.cpp:1808`) は `this->portsOrch->allPortsReady()` が false の間は即 return する。CONFIG_DB に書き込まれたエントリは PortsOrch 完了後の最初のイベントループで一括処理される（自動回復）。

### 依存 2: interface_list の PORT / PORTCHANNEL 解決

`createPbhTable()` (`pbhorch.cpp:266-272`) は `AclTable::validateAddPorts()` → `gPortsOrch->getPort()` で各インターフェースを解決する。ポートが PortsOrch 未登録の場合は `pendingPortSet` に保留され、`SUBJECT_TYPE_PORT_CHANGE` 通知で再バインドを試みる (`aclorch.cpp:2698-2703`)。

**違反時**: `interface_list` に指定したポートが `allPortsReady()` 後も未登録であれば `"Failed to configure PBH table(%s) ports"` + `return false`。CONFIG_DB エントリは残り、後続 SET で再試行。

### 依存 3: PBH_TABLE DEL は PBH_RULE DEL が先行必須

```
PBH_RULE|<table_name>|<rule_name>  DEL（先行）
  ↓
PBH_TABLE|<table_name>  DEL
```

`deployPbhTableRemoveTasks()` (`pbhorch.cpp:459-464`) は `hasDependencies(tObj)` が true（refCount > 0）の間 NOTICE ログ後 `it++` で retry。`PBH_RULE` create 時に `incRefCount(rule)` が `PBH_TABLE` の refCount を +1 し (`pbhmgr.cpp:114-135`)、DEL 時に `decRefCount(rule)` が -1 する。

**違反時**: `PBH_TABLE` の DEL が pending map に留まり続ける（永続 retry）。`PBH_RULE` を先に DEL すると自動回復。

### 依存 4: createPbhTable() の内部処理シーケンス

```
1. 重複チェック (pbhHlpr.getPbhTable)
2. AclTable 構築 — ACL_STAGE_INGRESS、bind point PORT + LAG
3. validateAddType(pbhTableType)  — 6 match 属性固定付与
4. validateAddStage(ACL_STAGE_INGRESS)
5. validateAddPorts(interface_list)
6. aclOrch->addAclTable(pbhTable)  → SAI create_acl_table
7. pbhHlpr.addPbhTable(table)     → 内部キャッシュ登録
```

各ステップ失敗時は `SWSS_LOG_ERROR` + `return false`。エントリは CONFIG_DB に残るが SAI には反映されない。

### 順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|-------------|
| 1 | PortsOrch 初期化 → PBH_TABLE 処理 | 必須先行（グローバル） | 自動回復（初期化完了後に一括処理） |
| 2 | PORT / PORTCHANNEL 登録 → PBH_TABLE SET | interface_list の解決 | pendingPortSet → PORT_CHANGE 通知で自動回復 |
| 3 | PBH_RULE DEL → PBH_TABLE DEL | DEL 時の必須先行 | 永続 retry（RULE DEL 後に自動回復） |
| 4 | createPbhTable() 内部: type/stage/ports/validate → addAclTable | SET 内部順序 | 各ステップ失敗で return false（CONFIG_DB は残存） |

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: meta/_intermediate/cdb-flow/pbh-table-cross-refs.md -->

`PBH_TABLE` は CONFIG_DB の他テーブルを**直接読まない**が、`interface_list` の解決で `PORT` / `PORTCHANNEL` に暗黙依存し、SAI 操作で `AclOrch` に依存する。

### このテーブルが参照する側

| 参照先テーブル / リソース | YANG leafref | 実行時依存 | 未充足時の挙動 |
|---|:---:|:---:|---|
| `PORT\|<name>` (CONFIG_DB) | ✅ `sonic-pbh.yang:245-247` | `validateAddPorts()` → `gPortsOrch->getPort()` (`aclorch.cpp:2698`) | `pendingPortSet` 保留 → `SUBJECT_TYPE_PORT_CHANGE` 通知で自動回復 |
| `PORTCHANNEL\|<name>` (CONFIG_DB) | ✅ `sonic-pbh.yang:248-251` | `validateAddPorts()` → `gPortsOrch->getPort()` LAG パス (`aclorch.cpp:106`) | 同上（PORT_CHANGE 通知で自動回復） |
| PortsOrch（グローバルゲート） | ✗ | `allPortsReady()` ゲート (`pbhorch.cpp:1808`) | 全 PBH テーブル処理がブロック（`allPortsReady()` true 後に自動回復） |
| AclOrch（Orch 間） | ✗ | `addAclTable()` / `updateAclTable()` / `removeAclTable()` | SWSS_LOG_ERROR + `return false`（CONFIG_DB エントリ残存・再試行なし） |

### このテーブルを参照する側

| 参照元テーブル | 参照フィールド | 参照タイミング | evidence |
|---|---|---|---|
| `PBH_RULE\|<table_name>\|<rule_name>` | `table_name` (YANG leafref) | PBH_RULE SET 時。`validateDependencies()` が `tableMap.find(rule.table)` を確認し、未存在なら `return false` → retry loop | `pbhmgr.cpp:83-88`, `pbhorch.cpp:929-968` |

!!! note "APP_DB / STATE_DB への書き出しはない"
    `PbhOrch` は `PBH_TABLE` の処理結果を STATE_DB / APPL_DB に書き出さない。ステータステーブルは未実装であり、`PBH_TABLE` は CONFIG_DB の consumer 専用テーブルとして機能する。

<!-- /cross-refs -->

## key 構造

```text
PBH_TABLE|<table_name>
```

`<table_name>` は PBH ポリシーの識別子。`PBH_RULE` の key `PBH_RULE|<table_name>|<rule_name>` でこの名前を参照する。

## フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `interface_list` | ordered leaf-list `PORT` / `PORTCHANNEL` leafref | yes | PBH table を適用する interface 群（1 要素以上） |
| `description` | string 1..255 | yes | table の説明 |

!!! note "未知フィールドの扱い"
    `parsePbhTable()` (`pbhmgr.cpp`) は未知フィールドを `SWSS_LOG_WARN("Unknown field(%s): skipping ...")` でサイレントスキップする。エラーにはならない。

## 購読者

- `orchagent` の `PbhOrch` (`sonic-swss/orchagent/pbhorch.cpp`): [CONFIG_DB](../../reference/glossary.md#term-config_db) の `PBH_TABLE` を `SubscriberStateTable` で直接 subscribe し、SAI ACL テーブルへ反映する。APP_DB への書き込みはない。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: [`PBH_RULE`](pbh-rule.md)、`PBH_HASH`、`PBH_HASH_FIELD`
- 関連 CLI: `config pbh table`
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-pbh`

## 引用元

[^1]: YANG 定義: `sonic-pbh.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-pbh.yang>
