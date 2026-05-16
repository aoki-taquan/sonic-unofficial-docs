# PBH — Phase B オブジェクト生成順序・依存関係 中間ファイル

生成日: 2026-05-16 (Task F Phase B)
対象ドキュメント: `docs/reference/config-db/pbh.md`
ソース: `sonic-swss/orchagent/pbhorch.cpp`, `sonic-swss/orchagent/pbh/pbhmgr.cpp`

---

## 調査概要

`PbhOrch::deployPbhTasks()` (`pbhorch.cpp:1539-1550`) の実装から、PBH オブジェクトの
Setup/Remove 順序と依存関係を抽出した。

---

## Setup 順序（コード証跡）

```cpp
// pbhorch.cpp:1539-1550
void PbhOrch::deployPbhTasks()
{
    // Remove (逆順)
    this->deployPbhRuleRemoveTasks();
    this->deployPbhTableRemoveTasks();
    this->deployPbhHashRemoveTasks();
    this->deployPbhHashFieldRemoveTasks();

    // Setup (依存解決順)
    this->deployPbhHashFieldSetupTasks();  // 1st: 依存なし
    this->deployPbhHashSetupTasks();       // 2nd: HASH_FIELD に依存
    this->deployPbhTableSetupTasks();      // 3rd: 依存なし (ports のみ)
    this->deployPbhRuleSetupTasks();       // 4th: TABLE + HASH に依存
}
```

Setup 順序: `PBH_HASH_FIELD → PBH_HASH → PBH_TABLE → PBH_RULE`

---

## 依存関係チェック（コード証跡）

### PBH_RULE の依存チェック (`pbhmgr.cpp:81-98`)

```cpp
template<>
bool PbhHelper::validateDependencies(const PbhRule &obj) const
{
    // PBH_TABLE が存在するか
    const auto &tCit = this->tableMap.find(obj.table);
    if (tCit == this->tableMap.cend()) return false;

    // PBH_HASH が存在するか
    const auto &hCit = this->hashMap.find(obj.hash.value);
    if (hCit == this->hashMap.cend()) return false;

    return true;
}
```

依存未解決時: `SWSS_LOG_NOTICE("Unable to setup PBH rule(%s): ... adding a retry")` → pendingSetupMap に留まる (`pbhorch.cpp:943`)

### PBH_HASH の依存チェック (`pbhmgr.cpp:99-113`)

```cpp
template<>
bool PbhHelper::validateDependencies(const PbhHash &obj) const
{
    for (const auto &cit : obj.hash_field_list.value)
    {
        const auto &hfCit = this->hashFieldMap.find(cit);
        if (hfCit == this->hashFieldMap.cend()) return false;
    }
    return true;
}
```

依存未解決時: `SWSS_LOG_NOTICE("Unable to create PBH hash(%s): ... adding a retry")` (`pbhorch.cpp:1241`)

---

## SAI 呼び出し順序

| 順序 | SAI API | 対応 CONFIG_DB | ソース行 |
|------|---------|---------------|---------|
| 1 | `sai_hash_api->create_fine_grained_hash_field()` | PBH_HASH_FIELD | pbhorch.cpp:1369 |
| 2 | `sai_hash_api->create_hash()` | PBH_HASH | pbhorch.cpp:1054 |
| 3 | ACL table 作成 (AclOrch) | PBH_TABLE | pbhorch.cpp:244-251 |
| 4 | `sai_acl_api->create_acl_entry()` | PBH_RULE | pbhorch.cpp:515-595 |

PBH_RULE の SAI ACL action:
- `SET_ECMP_HASH` → `SAI_ACL_ENTRY_ATTR_ACTION_SET_ECMP_HASH_ID`
- `SET_LAG_HASH`  → `SAI_ACL_ENTRY_ATTR_ACTION_SET_LAG_HASH_ID`

---

## 参照カウント保護

- `decRefCount(PbhRule)`: TABLE + HASH の refCount を -1 (`pbhmgr.cpp:163-185`)
- `decRefCount(PbhHash)`: 各 HASH_FIELD の refCount を -1 (`pbhmgr.cpp:187-210`)
- `hasDependencies()`: `refCount > 0` なら削除を retry キューへ (`pbhorch.cpp:461, 1290, 1521`)

---

## まとめ

PBH は CONFIG_DB への書き込み順序に強い制約がある:
1. まず `PBH_HASH_FIELD` を全て作成
2. 次に `PBH_HASH` を作成（hash_field_list の全エントリ解決後）
3. 次に `PBH_TABLE` を作成（ports 準備完了後）
4. 最後に `PBH_RULE` を作成（TABLE + HASH 両方解決後）

削除は逆順: RULE → TABLE → HASH → HASH_FIELD
