# ACL_TABLE_TYPE 副作用 (Phase F)

intermediate for `docs/reference/config-db/acl-table-type.md` Phase F block.

## 調査対象ソース

- `sonic-swss/orchagent/aclorch.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-swss/orchagent/aclorch.h` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)

スキャン範囲: `doAclTableTypeTask()` L5738-5774, `addAclTableType()` L4912-4930,
`removeAclTableType()` L4932-4948, `doTask()` L4273-4298, `getAclTableType()` L5855-5862

---

## 副作用の全体像

`ACL_TABLE_TYPE` エントリの SET/DEL は **orchagent 内の in-memory マップ `m_AclTableTypes`** のみを変更する。
SAI API 呼び出し・STATE_DB 書き込み・AppDB 書き込みはいずれも発生しない。

---

## SET 時の副作用

### 1. `m_AclTableTypes` へのエントリ追加

`addAclTableType()` (L4912-4930):

```cpp
m_AclTableTypes.emplace(tableType.getName(), tableType);
```

`AclOrch` インスタンス内の `unordered_map<string, AclTableType> m_AclTableTypes` にエントリが追加される。
以降、同名の `ACL_TABLE` が CONFIG_DB / AppDB に到着した際に `getAclTableType()` (L5855) が参照する。

### 2. 後続 `ACL_TABLE` 処理のアンブロック

`doAclTableTask()` (L5432):

```cpp
auto tableType = getAclTableType(tableTypeName);
if (!tableType)
{
    it++;   // retry: pending に残す
    continue;
}
```

カスタム `ACL_TABLE_TYPE` が存在しない状態で `ACL_TABLE` が先に到着すると `it++`（retry pending）となる。
その後 `ACL_TABLE_TYPE` の SET が成功して `m_AclTableTypes` に登録されると、次の `doTask()` サイクルで
`ACL_TABLE` のペンディングが解消され、SAI テーブル生成・STATE_DB `ACL_TABLE_TABLE` への `status=active` 書き込みが行われる。

---

## DEL 時の副作用

### 3. `m_AclTableTypes` からのエントリ削除

`removeAclTableType()` (L4932-4948):

```cpp
// It is Ok to remove table type that is in use by AclTable.
// AclTable holds a copy of AclTableType and there is no
// SAI object associated with AclTableType.
if (!m_AclTableTypes.erase(tableTypeName))
```

**コメント通り**: 既存の `AclTable` は `AclTableType` のコピーを保持しているため、
`m_AclTableTypes` から削除しても実行中の ACL テーブルへの影響はない。
SAI オブジェクトも存在しないため SAI 側変更もなし。

### 4. 新規 `ACL_TABLE` 参照の失敗

DEL 後に同名 type を参照する新規 `ACL_TABLE` が到着すると、`getAclTableType()` が `nullptr` を返し
`doAclTableTask()` の `it++` ループでペンディングが蓄積される。

---

## STATE_DB への影響なし

`doAclTableTypeTask()` は `setAclTableStatus()` を一切呼び出さない。
以下の STATE_DB テーブルへの書き込みは **`ACL_TABLE_TYPE` の処理では発生しない**:

| STATE_DB テーブル | 書き込みトリガ |
|---|---|
| `ACL_TABLE_TABLE` | `doAclTableTask()` (`ACL_TABLE` の SET/DEL 時) |
| `ACL_RULE_TABLE` | `doAclRuleTask()` (`ACL_RULE` の SET/DEL 時) |
| `ACL_STAGE_CAPABILITY_TABLE` | `queryAclActionCapability()` (起動時の SAI 問い合わせ) |

---

## 副作用サマリ

| 操作 | 直接副作用 | 間接副作用 |
|---|---|---|
| SET（parse 成功・新規） | `m_AclTableTypes` に追加 | 後続ペンディング `ACL_TABLE` のアンブロック → SAI テーブル生成・STATE_DB 書込み |
| SET（parse 失敗 or 重複） | なし | なし |
| DEL（登録済み） | `m_AclTableTypes` から削除 | 同名 type 参照の新規 `ACL_TABLE` がペンディング蓄積 |
| DEL（未登録） | なし | なし |
