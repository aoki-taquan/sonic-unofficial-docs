---
title: STATE_DB COPP 状態テーブル
description: "STATE_DB の COPP_GROUP_TABLE / COPP_TRAP_TABLE / COPP_TRAP_CAPABILITY_TABLE — CoPP グループ・トラップの適用状態と SAI 能力情報。"
area: reference
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: cfgmgr/coppmgr.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/copporch.cpp
    ref: master
related:
  config_db:
    - COPP_GROUP
    - COPP_TRAP
  cli:
    - show copp
hard: 0
---

# STATE_DB COPP 状態テーブル

## 概要

[STATE_DB](../../reference/glossary.md#term-state_db) には [CoPP](../../reference/glossary.md#term-copp) に関連する 3 つのテーブルが存在する。`COPP_GROUP_TABLE` と `COPP_TRAP_TABLE` は `coppmgrd` が書き込む適用状態フラグであり、`COPP_TRAP_TABLE` の `hw_status` フィールドは `orchagent` (`CoppOrch`) が [SAI](../../reference/glossary.md#term-sai) 操作の結果を反映する。`COPP_TRAP_CAPABILITY_TABLE` はプラットフォームがサポートするトラップ ID 一覧を `CoppOrch` 初期化時に公開する。

## テーブル一覧

| テーブル名 | キー | 書き手 | 役割 |
|---|---|---|---|
| `COPP_GROUP_TABLE` | グループ名 | `coppmgr` | グループの適用状態 (`state`) |
| `COPP_TRAP_TABLE` | トラップ名 | `coppmgr` + `CoppOrch` | トラップの適用状態 (`state`) と SAI 状態 (`hw_status`) |
| `COPP_TRAP_CAPABILITY_TABLE` | `traps` (固定) | `CoppOrch` | SAI capability — プラットフォームがサポートするトラップ ID 一覧 |

---

## COPP_GROUP_TABLE

### key 構造

```text
COPP_GROUP_TABLE|<group-name>
```

`<group-name>` は `COPP_GROUP|<name>` と同一（例: `queue4_group1`, `default`）。

### フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `state` | string | 常に `"ok"`。エントリの存在自体がグループが [APP_DB](../../reference/glossary.md#term-appl_db) に書き込まれたことを示す。 |

### 書き込みタイミング

`coppmgr` の `setCoppGroupStateOk()` が以下のタイミングで呼ばれる:

1. 起動時 (`CoppMgr` コンストラクタ) — マージ後の `group_cfg` を [APPL_DB](../../reference/glossary.md#term-appl_db) に書き込んだ直後
2. `doCoppGroupTask()` — CONFIG_DB の `COPP_GROUP` 変更受信後
3. `doCoppTrapTask()` / `setFeatureTrapIdsStatus()` — トラップ追加・削除により trap_ids が変化した後

### 削除タイミング

`delCoppGroupStateOk()` は以下のタイミングで呼ばれる:

- グループが pending 状態になったとき (feature 無効化によりグループに有効なトラップが 0 件になった場合)
- `doCoppGroupTask()` の DEL 処理時

### エントリ不在の意味

- グループが **pending** 状態 — そのグループに関連する feature がすべて無効
- または CoPP の初期処理未完了

---

## COPP_TRAP_TABLE

### key 構造

```text
COPP_TRAP_TABLE|<trap-name>
```

`<trap-name>` は `COPP_TRAP|<name>` と同一（例: `bgp`, `arp`, `snmp_grp`）。

### フィールド

| フィールド | 型 | 書き手 | 説明 |
|---|---|---|---|
| `state` | string | `coppmgr` | 常に `"ok"`。エントリ存在 = トラップが coppmgr によって有効化済み。 |
| `hw_status` | string | `CoppOrch` | SAI 操作の結果。`"installed"` または `"not-installed"`。 |

`state` と `hw_status` は**同一テーブル・同一 key** に異なるプロセスが書き込む独立したフィールド。

### `state` フィールドの書き込みタイミング

`setCoppTrapStateOk()` が呼ばれる条件:

1. 起動時 — `is_always_enabled == "true"` または feature が有効な場合
2. `doCoppTrapTask()` — SET 操作の完了後
3. feature 有効化時 (`setFeatureTrapIdsStatus(feature, true)`)
4. DEL 後に init cfg に同名キーが存在する場合の自動復元時

`delCoppTrapStateOk()` が呼ばれる条件:

- feature 無効化後にグループが pending → `setFeatureTrapIdsStatus(feature, false)` 経路
- `doCoppTrapTask()` の DEL 処理時

### `hw_status` フィールドの書き込みタイミング

`CoppOrch::updateTrapOperStatus()` が呼ばれる:

| 値 | タイミング | ソース行 |
|---|---|---|
| `"installed"` | `sai_hostif_api->create_hostif_trap()` 成功後 | `copporch.cpp:526` |
| `"not-installed"` | `sai_hostif_api->remove_hostif_trap()` 成功後 | `copporch.cpp:1413` |

key は `get_trap_name_by_type()` で `sai_hostif_trap_type_t` を文字列に変換したもの（`trap_id_map` の逆引き）。

### エントリ不在の意味

- `state` なし → coppmgr がトラップをまだ有効化していない（pending / feature 無効 / DEL 済み）
- `hw_status` なし → CoppOrch がそのトラップに対して SAI 操作をまだ実行していない

---

## COPP_TRAP_CAPABILITY_TABLE

### key 構造

```text
COPP_TRAP_CAPABILITY_TABLE|traps
```

key は常に `traps` 固定。

### フィールド

| フィールド | 型 | 説明 |
|---|---|---|
| `trap_ids` | string | プラットフォームがサポートするトラップ ID 名のカンマ区切りリスト |

### 書き込みタイミング

`CoppOrch` コンストラクタの `publishTrapIdsCapability()` が orchagent 起動時に 1 回だけ書き込む。

### 値の決定ロジック

```
sai_query_attribute_enum_values_capability() 成功
  → SAI が返したトラップ ID を文字列リストに変換して書き込み

sai_query_attribute_enum_values_capability() 失敗
  → default_supported_trap_ids (静的リスト, 42 種) にフォールバック
```

フォールバックリストには `neighbor_miss` が意図的に含まれない（コードコメント: "This list is intended to remain static and should not be updated with new traps."）。

---

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

### `state` フィールド — 値は常に `"ok"` でハードコード

`setCoppGroupStateOk()` と `setCoppTrapStateOk()` はともに文字列 `"ok"` をハードコードで書き込む。外部設定やフィールドの選択肢は存在しない。エントリの**存在/不在**がステータスを表す二値表現。<!-- evidence: coppmgr.cpp L426, L441 -->

### `hw_status` フィールド — 値は `"installed"` / `"not-installed"` の 2 値のみ

`updateTrapOperStatus()` に渡される文字列はコード内で直接指定される (`"installed"` または `"not-installed"`)。中間状態を表す値は存在しない。<!-- evidence: copporch.cpp L526, L1413 -->

### `COPP_TRAP_TABLE` の二重書き込み — `state` と `hw_status` の非同期

`state` (coppmgr) と `hw_status` (copporch) は同一 Redis key に別プロセスが独立して書き込む。`state=ok` であっても `hw_status` がまだ存在しない（SAI 登録前）、あるいは逆に `hw_status=installed` であっても `state` が存在しない（coppmgr での DEL 後に orchagent がまだ操作を受け取っていない）状態が短時間発生しうる。

### `COPP_TRAP_CAPABILITY_TABLE` — フォールバック時の `neighbor_miss` silent drop

SAI capability query が失敗した場合、`neighbor_miss` は `default_supported_trap_ids` に含まれないため `supported_trap_ids` セットに登録されない。結果として `neighbor_miss` trap を含む COPP グループは SAI への適用がスキップされ、ログ (`SWSS_LOG_NOTICE("Ignoring the trap_id: %s, since not supported by vendor SAI", ...)`) のみが出力される。<!-- evidence: copporch.cpp L104-151, L263-270, L408-413 -->

### `hw_status` キーの導出 — `trap_id_map` 逆引き

`updateTrapOperStatus()` は `get_trap_name_by_type()` で `sai_hostif_trap_type_t` を文字列に変換する。`trap_id_map` に存在しない SAI 内部トラップ型は文字列変換に失敗し、`SWSS_LOG_ERROR` を出力したうえで `COPP_TRAP_TABLE` への書き込みをスキップする。<!-- evidence: copporch.cpp L226-231 -->

> **スキャン証跡**: coppmgr.cpp L424-451 全行読了。copporch.cpp L104-300, L499-540, L1390-1420 読了。schema.h L448-450 読了。state_db.json (UT mock) 読了。発見 4 件。
<!-- /defaults -->

<!-- ordering -->
## STATE_DB 書き込み順序 (Phase B)

### 通常起動シーケンス

STATE_DB への書き込みは 3 段階に分かれ、2 プロセスが非同期に関与する。

#### ステップ 1: `CoppOrch` コンストラクタ（orchagent 起動直後）

```
CoppOrch::CoppOrch()
  └─ publishTrapIdsCapability()
       └─ COPP_TRAP_CAPABILITY_TABLE|traps  ← 起動時 1 回のみ書き込み
```

SAI の `sai_query_attribute_enum_values_capability()` でプラットフォームサポート情報を取得し、即座に書き込む。失敗時は静的デフォルトリスト（42 種、`neighbor_miss` 除外）にフォールバック。`initDefaultHostIntfTable()` 等の初期化はこの後に実行される。<!-- evidence: copporch.cpp L208-209, L240-300 -->

#### ステップ 2: `CoppMgr` コンストラクタ（coppmgrd 起動時）

```
CoppMgr::CoppMgr()
  ├─ [init cfg + CONFIG_DB をマージ]
  ├─ for each trap: setCoppTrapStateOk(trap)
  │    → COPP_TRAP_TABLE|<trap>  state=ok
  ├─ for each group: m_appCoppTable.set(group, ...)
  │    → APPL_DB APP_COPP_TABLE|<group>
  └─ setCoppGroupStateOk(group)
       → COPP_GROUP_TABLE|<group>  state=ok
```

`COPP_TRAP_TABLE` の `state` が先に書かれ、その後 APPL_DB への書き込みと `COPP_GROUP_TABLE` の `state` が書かれる。`COPP_TRAP_TABLE` の `hw_status` はこの時点では書かれない。<!-- evidence: coppmgr.cpp L334-411 -->

#### ステップ 3: orchagent が APPL_DB を処理した後

```
CoppOrch::applyAttributesToTrapIds()
  ├─ sai_hostif_api->create_hostif_trap()  [SAI 成功]
  └─ updateTrapOperStatus(trap_id, "installed")
       → COPP_TRAP_TABLE|<trap-name>  hw_status=installed
```

SAI 操作が成功した場合のみ `hw_status=installed` が書き込まれる。SAI 失敗時は書き込みをスキップし、エラーログのみ出力。<!-- evidence: copporch.cpp L515-526 -->

### 削除・無効化シーケンス

| 操作 | 書き込み順 |
|---|---|
| feature 無効化 | `APPL_DB del(group)` → `COPP_GROUP_TABLE del(group)` |
| SAI remove 成功 | `hw_status=not-installed` |
| `doCoppTrapTask` DEL | `COPP_TRAP_TABLE del(trap)` → init cfg がある場合は自動復元 |

### Warm-reboot の扱い

`coppmgr.cpp` は `warm_restart.h` を include するが `WarmStart::` の呼び出しは存在しない。STATE_DB への書き込みが **冪等**（同一 key への上書き set）であるため、warm-reboot 時も通常起動と同一フローで再書き込みし、orchagent 側の SAI reconciliation に委ねる設計となっている。<!-- evidence: coppmgr.cpp L10 include のみ、WarmStart:: 呼び出し 0 件 -->

### 依存グラフ

```
orchagent 起動
  → COPP_TRAP_CAPABILITY_TABLE|traps

coppmgrd 起動
  → COPP_TRAP_TABLE|<trap> state=ok  (各トラップ)
  → APPL_DB APP_COPP_TABLE|<group>
  → COPP_GROUP_TABLE|<group> state=ok

orchagent が APPL_DB を処理
  → SAI create_hostif_trap 成功
  → COPP_TRAP_TABLE|<trap> hw_status=installed
```

`state` (coppmgr) と `hw_status` (copporch) は同一 Redis キーに非同期で書き込まれるため、両フィールドが揃うタイミングは保証されない。短時間の不整合（`state=ok` だが `hw_status` 未設定、またはその逆）は正常動作である。
<!-- /ordering -->

## 確認コマンド

```bash
# グループ状態確認
sonic-db-cli STATE_DB hgetall 'COPP_GROUP_TABLE|queue4_group1'

# トラップ状態確認
sonic-db-cli STATE_DB hgetall 'COPP_TRAP_TABLE|bgp'

# プラットフォームサポートトラップ一覧
sonic-db-cli STATE_DB hgetall 'COPP_TRAP_CAPABILITY_TABLE|traps'

# 全 COPP 状態を一覧
sonic-db-cli STATE_DB keys 'COPP_*TABLE|*'
```

## 購読者

- `sonic-utilities` の `dump copp` プラグイン (`dump/plugins/copp.py`): デバッグ用にすべての COPP 関連 DB エントリを集約して表示

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): `COPP_GROUP`, `COPP_TRAP`
- 関連 CLI: `show copp config`, `show copp policer`, `sonic-db-cli STATE_DB`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`COPP_GROUP`](copp-group.md)
- CONFIG_DB: [`COPP_TRAP`](copp-trap.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-swss/cfgmgr/coppmgr.cpp` — `setCoppGroupStateOk()` / `setCoppTrapStateOk()` の実装。  
[^2]: `sonic-swss/orchagent/copporch.cpp` — `updateTrapOperStatus()` / `publishTrapIdsCapability()` の実装。  
[^3]: `sonic-swss-common/common/schema.h` L448-450 — テーブル名定数定義。

<!-- glossary-links-injected: a827b4343c01 -->
