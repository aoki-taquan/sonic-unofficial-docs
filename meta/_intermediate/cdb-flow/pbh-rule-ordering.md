# PBH_RULE — Phase B 書込み順依存スキャンノート

対象テーブル: `PBH_RULE`
Consumer: `PbhOrch::doPbhRuleTask()` (`sonic-swss/orchagent/pbhorch.cpp`)
スキャン範囲: `pbhorch.cpp` 全行精読、`pbhmgr.cpp:81-113` (validateDependencies)

---

## 検出した順序依存・タイミング依存

### 1. allPortsReady() ガード（ポート初期化先行必須）

- `PbhOrch::doTask()` (`pbhorch.cpp:1808-1810`): `this->portsOrch->allPortsReady()` が false の間は即 return。
- **PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD 全テーブル処理がブロックされる**。
- PortsOrch の起動完了前に書き込んだ CONFIG_DB エントリは、ポート初期化完了後の最初のイベントループで一括処理される（自動回復）。
- 順序依存: `PORT` テーブルの初期化完了（PortsOrch）が PBH_RULE より**先に**完了していること。
- evidence: `pbhorch.cpp:1808`

### 2. PBH_TABLE が先行必須（validateDependencies retry ループ）

- `deployPbhRuleSetupTasks()` (`pbhorch.cpp:941-946`) は `this->pbhHlpr.validateDependencies(rule)` を呼ぶ。
- `validateDependencies(PbhRule)` (`pbhmgr.cpp:81-96`): `this->tableMap.find(rule.table)` が `cend()` なら `return false` → NOTICE ログ (`"object has missing dependencies: adding a retry"`) → `it++` で pendingSetupMap に保留。
- PBH_TABLE が orchagent の内部 `tableMap` に存在しなければ（SAI ACL table 未作成）、PBH_RULE の setup は毎イベントループで retry し続ける（無限待機）。
- 順序依存: `PBH_TABLE|<table_name>` が PbhOrch に処理済みであること（SAI ACL table OID 割当済み）。
- evidence: `pbhorch.cpp:941-946`, `pbhmgr.cpp:83-88`

### 3. PBH_HASH が先行必須（validateDependencies retry ループ）

- `validateDependencies(PbhRule)` (`pbhmgr.cpp:88-94`): `this->hashMap.find(rule.hash.value)` が `cend()` なら `return false` → PBH_TABLE と同様の retry ループ。
- PBH_RULE が参照する `PBH_HASH` エントリが hashMap に存在しなければ setup は延期される。
- 順序依存: `PBH_HASH|<hash_name>` が PbhOrch の hashMap に登録済みであること。PBH_HASH は `PBH_HASH_FIELD` を参照するため、全依存の解決順は `HASH_FIELD → HASH → TABLE → RULE`。
- evidence: `pbhmgr.cpp:88-96`, `pbhorch.cpp:941`

### 4. deployPbhTasks() の固定処理順序（4 テーブルの相対順）

- `deployPbhTasks()` (`pbhorch.cpp:1539-1550`) は毎回以下の順序で pending map を処理する:
  - Remove 順 (逆依存): RULE → TABLE → HASH → HASH_FIELD
  - Setup 順 (正依存): HASH_FIELD → HASH → TABLE → RULE
- PBH_RULE の setup は常に最後に試みられる。CONFIG_DB に RULE だけ先に書いても、HASH_FIELD/HASH/TABLE の setup が同一イベントループ内で先に完了していれば、同ループの末尾で RULE の依存チェックが通り一括 setup される。
- evidence: `pbhorch.cpp:1539-1550`

### 5. 参照カウント保護による DEL 順序制約

- `PBH_TABLE` と `PBH_HASH` は `refCount > 0` の間は削除不可（`hasDependencies()` → retry）。
- `PBH_RULE` 作成時に `incRefCount(rule)` が `PBH_TABLE` と `PBH_HASH` の refCount を +1 する (`pbhmgr.cpp:114-135`)。
- `PBH_RULE` 削除時に `decRefCount(rule)` が refCount を -1 する (`pbhmgr.cpp:163-185`)。
- **DEL 順序**: `PBH_RULE` を先に DEL → PBH_TABLE / PBH_HASH の refCount がゼロになれば DEL 可能。
- RULE を DEL せずに TABLE / HASH を DEL しようとすると `hasDependencies()` が true → NOTICE ログ後 retry（削除が保留され続ける）。
- evidence: `pbhorch.cpp:459-474` (TABLE remove — hasDependencies), `pbhorch.cpp:1288-1303` (HASH remove — hasDependencies), `pbhmgr.cpp:114-135, 163-185`

### 6. 同一 key に対する task already exists ガード

- `doPbhRuleTask()` (`pbhorch.cpp:1645-1650`): `pbhTaskExists(rule)` が true（同 key の SET/DEL が既に pendingSetupMap または pendingRemoveMap に存在）の場合、WARN ログ後 `it++` で再試行。
- 高頻度の SET が同一 key を複数回 m_toSync に積んだ場合、先の task が処理完了するまで後続の SET は待機する。
- evidence: `pbhorch.cpp:1645-1650`

### 7. Mellanox W/A における UPDATE 内部順序依存

- `updatePbhRule()` (`pbhorch.cpp:839-863`): `ASIC_VENDOR=mellanox` かつ変更フィールドに `hash` または `packet_action` が含まれる場合、`disableAction()` を先に呼び既存 ACL action を無効化してから `updateAclRule()` を呼ぶ。
- `disableAction()` 失敗時は `return false`（UPDATE 自体が失敗）。
- GENERIC platform ではこのステップは存在せず直接 `updateAclRule()` を呼ぶ。
- evidence: `pbhorch.cpp:839-863`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PortsOrch 初期化 → PBH_RULE 処理 | 必須先行（グローバル） | 自動回復（初期化完了後に一括処理） |
| 2 | PBH_TABLE → PBH_RULE | 必須先行 | retry loop — TABLE 作成後に自動 setup |
| 3 | PBH_HASH_FIELD → PBH_HASH → PBH_RULE | 必須先行（3段） | retry loop — 全依存解決後に自動 setup |
| 4 | deployPbhTasks() 固定順序 | HASH_FIELD→HASH→TABLE→RULE (setup) / RULE→TABLE→HASH→HASH_FIELD (remove) | 自動（コード内固定） |
| 5 | PBH_RULE DEL → PBH_TABLE / PBH_HASH DEL | DEL 時の必須先行 | 違反時は retry（TABLE/HASH 削除が保留） |
| 6 | 同一 key の task 重複 | SET 時の待機 | retry loop（先の task 完了後に処理） |
| 7 | Mellanox: disableAction → updateAclRule | UPDATE 内部順序 | GENERIC では不要 |
