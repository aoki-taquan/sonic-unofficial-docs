# PBH_TABLE — オブジェクト生成順序・依存関係 (Phase B)

## 調査対象

- `sonic-swss/orchagent/pbhorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/pbh/pbhmgr.cpp`

## 依存関係の概要

`PBH_TABLE` 自体は他の PBH テーブルに依存しないが、参照する `PORT` / `PORTCHANNEL` の存在 (`PortsOrch::allPortsReady()`) を必要とする。また、`PBH_RULE` はこのテーブルに依存するため、`PBH_TABLE` の **作成は PBH_RULE より前**、**削除は PBH_RULE より後**が必須。

## `deployPbhTasks()` の固定順序

```cpp
// pbhorch.cpp:1539-1550
void PbhOrch::deployPbhTasks()
{
    // Remove: RULE → TABLE → HASH → HASH_FIELD
    this->deployPbhRuleRemoveTasks();
    this->deployPbhTableRemoveTasks();
    this->deployPbhHashRemoveTasks();
    this->deployPbhHashFieldRemoveTasks();

    // Setup: HASH_FIELD → HASH → TABLE → RULE
    this->deployPbhHashFieldSetupTasks();
    this->deployPbhHashSetupTasks();
    this->deployPbhTableSetupTasks();
    this->deployPbhRuleSetupTasks();
}
```

## PBH_TABLE に対する依存チェック

### SET 時

`deployPbhTableSetupTasks()` (`pbhorch.cpp:405-435`) は依存チェックを行わず、直接 `createPbhTable()` または `updatePbhTable()` を呼ぶ。ただし `PbhOrch::doTask()` (`pbhorch.cpp:1808`) は `allPortsReady()` が false なら即 return するため、全 PBH 処理が PortsOrch 初期化を待つ。

### DEL 時

`deployPbhTableRemoveTasks()` (`pbhorch.cpp:439-474`) は:

```cpp
if (this->pbhHlpr.hasDependencies(tObj))
{
    SWSS_LOG_NOTICE("Unable to remove PBH table(%s): object has dependencies: adding a retry", key.c_str());
    it++;  // pendingRemoveMap に保留し retry
    continue;
}
```

`hasDependencies(table)` (`pbhmgr.cpp:75-78`) は `table.refCount > 0` のとき true を返す。`PBH_RULE` の create 時に `incRefCount(rule)` が `PBH_TABLE` の refCount を +1 (`pbhmgr.cpp:114-135`)、delete 時に `decRefCount(rule)` が -1 する。

## 依存関係サマリ

| 依存 | 方向 | 説明 |
|------|------|------|
| PortsOrch 初期化 → PBH_TABLE | 必須先行（グローバル） | `allPortsReady()` が false なら全 PBH イベントが skip |
| PBH_TABLE SET → PBH_RULE SET | PBH_TABLE が先 | RULE の `validateDependencies` が TABLE の存在をチェック |
| PBH_RULE DEL → PBH_TABLE DEL | PBH_RULE が先 | TABLE の refCount > 0 の間 DEL は retry ループ |

## interface_list の解決タイミング

`createPbhTable()` (`pbhorch.cpp:266-272`) は `interface_list` で `AclTable::validateAddPorts()` → `gPortsOrch->getPort()` を呼ぶ。ポートが未登録の場合 `pendingPortSet` に保留され、`SUBJECT_TYPE_PORT_CHANGE` 通知で再バインドを試みる (`aclorch.cpp:2698-2703`)。この保留は `PortsOrch::allPortsReady()` とは別の「ポート個別の未登録」ケース。

## createPbhTable() の処理シーケンス

1. 重複チェック: `pbhHlpr.getPbhTable()` — 既存なら `"object already exists"` + `return false`
2. `AclTable` 構築: `ACL_STAGE_INGRESS`、bind point は `PORT` + `LAG`
3. `validateAddType(pbhTableType)` — GRE_KEY / ETHER_TYPE / IP_PROTOCOL / IPV6_NEXT_HEADER / L4_DST_PORT / INNER_ETHER_TYPE の 6 match 属性を付与
4. `validateAddStage(ACL_STAGE_INGRESS)` — ステージ固定
5. `validateAddPorts(interface_list)` — ポート/LAG バインド
6. `aclOrch->addAclTable(pbhTable)` — SAI `create_acl_table`
7. `pbhHlpr.addPbhTable(table)` — 内部キャッシュ登録

各ステップ失敗時は `SWSS_LOG_ERROR` + `return false`。エントリは CONFIG_DB に残る。
