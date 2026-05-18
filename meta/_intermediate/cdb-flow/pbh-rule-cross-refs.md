# PBH_RULE 暗黙参照テーブル調査 (Phase C)

## 調査ソース

| ファイル | 役割 |
|---|---|
| `sonic-swss/orchagent/pbhorch.cpp` | PbhOrch メイン処理（subscribe / SAI 反映） |
| `sonic-swss/orchagent/pbh/pbhmgr.cpp` | validateDependencies / incRefCount / decRefCount |
| `sonic-swss/orchagent/pbh/pbhrule.cpp` | AclRulePbh validate / disableAction |
| `sonic-swss/orchagent/orchdaemon.cpp` | PbhOrch 初期化（依存 Orch 渡し） |

## 暗黙参照テーブル一覧

### 1. PBH_TABLE（必須・leafref + 実行時依存）

- YANG: `PBH_RULE.table_name` は leafref → `PBH_TABLE.name`（強制参照整合性）
- 実行時: `validateDependencies(rule)` (`pbhmgr.cpp:83-88`) で `tableMap.find(rule.table)` を確認。未存在なら `return false` → retry loop。
- `createPbhRule` 成功後、`incRefCount(rule)` (`pbhmgr.cpp:114-135`) が `PBH_TABLE` の refCount を +1 する。`PBH_TABLE` DEL 時に `hasDependencies()` が true なら削除保留。

### 2. PBH_HASH（必須・leafref + 実行時依存）

- YANG: `PBH_RULE.hash` は leafref → `PBH_HASH.hash_name`（強制参照整合性）
- 実行時: `validateDependencies(rule)` (`pbhmgr.cpp:88-94`) で `hashMap.find(rule.hash.value)` を確認。未存在なら `return false` → retry loop。
- `incRefCount(rule)` が `PBH_HASH` の refCount も +1 する。`PBH_HASH` DEL 時も同様に保留。

### 3. AclOrch（必須・Orch 間依存）

- `PbhOrch` は `AclOrch *aclOrch` を constructor 引数として受け取る (`pbhorch.cpp:90-94`)。
- `createPbhRule` で `this->aclOrch->addAclRule(pbhRule, rule.table)` を呼ぶ (`pbhorch.cpp:633`)。失敗時は ERROR ログ + `return false`（retry loop）。
- `updatePbhRule` では `this->aclOrch->getAclRule(rule.table, rule.name)` で既存 ACL rule を取得し (`pbhorch.cpp:849`)、Mellanox 環境では `disableAction()` + `updateAclRule()` を呼ぶ。
- `removePbhRule` では `this->aclOrch->removeAclRule(rObj.table, rObj.name)` を呼ぶ (`pbhorch.cpp:906`)。

### 4. PortsOrch（必須・グローバルゲート）

- `PbhOrch` は `PortsOrch *portsOrch` を constructor 引数として受け取る (`pbhorch.cpp:91,95`)。
- `doTask()` (`pbhorch.cpp:1808`) で `this->portsOrch->allPortsReady()` が false の間は即 return。PBH_RULE を含む全 PBH テーブルの処理がブロックされる。
- orchdaemon.cpp で `gPortsOrch` を `gPbhOrch` に渡している (`orchdaemon.cpp:565`)。

### 5. SAI ACL API（間接依存）

- `AclRulePbh` が SAI `sai_acl_api->create_acl_entry()` を呼ぶ（`AclOrch::addAclRule()` 内）。SAI 失敗は `addAclRule()` → `return false` → `createPbhRule()` → `return false` → retry loop として伝播。

## 双方向参照サマリ

| 参照先テーブル / リソース | YANG leafref | 実行時依存 | 未充足時の挙動 |
|---|:---:|:---:|---|
| `PBH_TABLE` (CONFIG_DB) | ✅ | tableMap 存在チェック | retry loop（TABLE 作成後に自動回復） |
| `PBH_HASH` (CONFIG_DB) | ✅ | hashMap 存在チェック | retry loop（HASH 作成後に自動回復） |
| AclOrch (Orch 間) | ✗ | addAclRule() / removeAclRule() | ERROR ログ + return false → retry loop |
| PortsOrch (Orch 間) | ✗ | allPortsReady() ゲート | PBH_RULE 処理全体がブロック（自動回復） |
| SAI ACL API | ✗ | create_acl_entry | AclOrch 経由で ERROR + retry loop |

## 書込み方向

PBH_RULE は CONFIG_DB の **読み手（consumer）のみ**。書き手は `config pbh rule add` CLI / `sonic-cfggen` / mgmt-framework。`PbhOrch` はステータスを STATE_DB / APPL_DB に書き出さない（ステータステーブル未実装）。
