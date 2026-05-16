# ACL_TABLE 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/acl-table.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/aclorch.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-swss/orchagent/aclorch.h`

スキャン範囲: `doAclTableTask()` L5361-5518, `AclTable::validate()` L2725-2769,
`processAclTableType()` L5819-5831, `processAclTableStage()` L5838-5853,
`processAclTablePorts()` L5776-5807, `removeAclTable()` L4829-4910,
`setAclTableStatus()` L6088-6093

---

## 失敗パス一覧

### 1. `type` 空文字 → `processAclTableType()` false → bAllAttributesOk=false → erase + INACTIVE

`aclorch.cpp:5382-5388, 5819-5826`:

```cpp
bool AclOrch::processAclTableType(string type, string &out_table_type)
{
    if (type.empty())
    {
        return false;   // 空文字のみ reject
    }
    out_table_type = type;
    return true;
}
```

`doAclTableTask()`:
```cpp
if (!processAclTableType(attr_value, tableTypeName))
{
    SWSS_LOG_ERROR("Failed to process ACL table %s type", table_id.c_str());
    bAllAttributesOk = false;
    break;  // 以降のフィールド処理を中断
}
```

`bAllAttributesOk=false` → `validate()` スキップ → `erase(it)` + `setAclTableStatus(INACTIVE)` + `SWSS_LOG_ERROR("Failed to create ACL table %s, invalid configuration")` (`aclorch.cpp:5490-5494`)。
CONFIG_DB の値は残る。**retry なし。rollback なし。STATE_DB に "Inactive" 記録。**

---

### 2. 不明な属性名 → bAllAttributesOk=false → erase + INACTIVE

`aclorch.cpp:5415-5420`:

```cpp
else
{
    SWSS_LOG_ERROR("Unknown table attribute '%s'", attr_name.c_str());
    bAllAttributesOk = false;
    break;
}
```

既知属性は `POLICY_DESC` / `TYPE` / `PORTS` / `STAGE` / `SERVICES` のみ。それ以外は即 break。
**retry なし。rollback なし。STATE_DB に "Inactive"。**

---

### 3. `stage` 不正値 → `processAclTableStage()` false → bAllAttributesOk=false → erase + INACTIVE

`aclorch.cpp:5400-5408, 5838-5853`:

```cpp
bool AclOrch::processAclTableStage(string stage, acl_stage_type_t &acl_stage)
{
    auto iter = aclStageLookUp.find(to_upper(stage));
    if (iter == aclStageLookUp.end())
    {
        acl_stage = ACL_STAGE_UNKNOWN;
        return false;
    }
    ...
}
```

`aclStageLookUp` は `{"INGRESS": ACL_STAGE_INGRESS, "EGRESS": ACL_STAGE_EGRESS}` のみ。不正値は `ACL_STAGE_UNKNOWN` → `validate()` で `stage == ACL_STAGE_UNKNOWN` をチェックして false 返却 (`aclorch.cpp:2732`)。
**retry なし。rollback なし。STATE_DB に "Inactive"。**

---

### 4. `ports` 内に bind 不可ポート → `processAclTablePorts()` false → bAllAttributesOk=false → erase

`aclorch.cpp:5392-5398, 5795-5800`:

```cpp
sai_object_id_t bind_port_id;
if (!getAclBindPortId(port, bind_port_id))
{
    SWSS_LOG_ERROR("Failed to get port %s bind port ID for ACL table %s", ...);
    return false;  // IN_PORTS/OUT_PORTS 等の bind 不可インタフェース
}
```

ポートが未登録の場合は `pendingPortSet.emplace(alias)` で **スキップ継続（return false ではない）**。bind 可能でない OID 変換失敗時のみ `return false` → `bAllAttributesOk=false` → erase。
**retry なし。rollback なし。STATE_DB に "Inactive"。**

---

### 5. ユーザ定義 type が未登録 → `getAclTableType()` nullptr → `it++` (保留 retry)

`aclorch.cpp:5432-5437`:

```cpp
auto tableType = getAclTableType(tableTypeName);
if (!tableType)
{
    it++;   // 次のループでリトライ
    continue;
}
```

`getAclTableType()` が nullptr を返すのは `ACL_TABLE_TYPE|<name>` が未処理の場合。`SWSS_LOG_INFO("Failed to find ACL table type %s")` のみ（ERROR でなく INFO）。erase はしない。
**retry: 無制限（ACL_TABLE_TYPE が登録されるまで）。STATE_DB への書き込みなし。**

---

### 6. `validate()` 失敗 (L3V4V6 非サポート / action 非サポート) → erase + INACTIVE

`aclorch.cpp:2737-2767`:

```cpp
if (type.getName() == TABLE_TYPE_L3V4V6)
{
    if (!m_pAclOrch->isAclL3V4V6TableSupported(stage))
    {
        SWSS_LOG_ERROR("Table %s: table type %s in stage %d not supported on this platform.",
                       id.c_str(), type.getName().c_str(), stage);
        return false;
    }
}

if (m_pAclOrch->isAclActionListMandatoryOnTableCreation(stage))
{
    if (type.getActions().empty())
    {
        SWSS_LOG_ERROR("Action list for table %s is mandatory", id.c_str());
        return false;
    }
}

for (const auto& action: type.getActions())
{
    if (!m_pAclOrch->isAclActionSupported(stage, action))
    {
        SWSS_LOG_ERROR("Action %s is not supported on table %s", ...);
        return false;
    }
}
```

`validate()` が false を返すと `bAllAttributesOk && newTable.validate()` が偽 → erase + INACTIVE + ERROR ログ。
**retry なし。rollback なし。STATE_DB に "Inactive"。**

---

### 7. `addAclTable()` SAI 呼び出し失敗 (MIRROR/MIRRORV6 ASIC capability なし等) → `it++` (retry)

`aclorch.cpp:5474-5485`:

```cpp
if (addAclTable(table_id, newTable, orignalTableTypeName))
{
    setAclTableStatus(table_id, AclObjectStatus::ACTIVE);
    it = consumer.m_toSync.erase(it);
}
else
{
    setAclTableStatus(table_id, AclObjectStatus::PENDING_CREATION);
    it++;  // 次サイクルにリトライ
}
```

`addAclTable()` が false を返すケース:
- `type=MIRROR` / `MIRRORV6` + `m_mirrorTableCapabilities[type]` が false (`aclorch.cpp:3502-3541`)
- SAI `create_acl_table` の戻り値 `!= SAI_STATUS_SUCCESS`
- `type=UNDERLAY_SET_DSCP` の MarkMeta テーブル作成失敗

STATE_DB は "Pending creation" に設定。**retry: 無制限 (it++ pattern)。rollback なし。**

---

### 8. `updateAclTable()` 失敗 (既存テーブル更新失敗) → `it++` (retry)

`aclorch.cpp:5465-5470`:

```cpp
else
{
    SWSS_LOG_ERROR("Failed to update existing ACL table %s", table_id.c_str());
    it++;  // 次サイクルにリトライ
}
```

既存テーブルの ports 差分バインド/アンバインドが SAI で失敗した場合。STATE_DB は更新されない。
**retry: 無制限。rollback なし（中途のバインド状態のまま）。**

---

### 9. `removeAclTable()` 失敗 → `it++` (retry) + PENDING_REMOVAL

`aclorch.cpp:5499-5510`:

```cpp
if (removeAclTable(table_id))
{
    removeAclTableStatus(table_id);
    it = consumer.m_toSync.erase(it);
}
else
{
    setAclTableStatus(table_id, AclObjectStatus::PENDING_REMOVAL);
    it++;
}
```

`removeAclTable()` が false を返すケース:
- `removeEgrSetDscpTable()` 失敗 (UNDERLAY 系の内部テーブル削除失敗) (`aclorch.cpp:4835-4840`)
- `m_AclTables[table_oid].clear()` (配下 ACL_RULE の SAI 削除) 失敗 (`aclorch.cpp:4850-4855`)
- `unbindAclTableFromSwitch()` 失敗 (EGRESS + bindToSwitch=true) (`aclorch.cpp:4862-4867`)
- SAI `deleteUnbindAclTable()` 失敗 (`aclorch.cpp:4869-4908`)

STATE_DB は "Pending removal" に設定。**retry: 無制限。rollback なし。**

---

### 10. 未知 op type → erase + SWSS_LOG_ERROR (no retry)

`aclorch.cpp:5512-5516`:

```cpp
else
{
    it = consumer.m_toSync.erase(it);
    SWSS_LOG_ERROR("Unknown operation type %s", op.c_str());
}
```

`SET_COMMAND` / `DEL_COMMAND` 以外の op type は即 erase。**retry なし。**

---

## STATE_DB への障害記録

`AclOrch::setAclTableStatus()` (`aclorch.cpp:6088-6093`) が `STATE_DB` の `ACL_TABLE` テーブルに `status` フィールドを書き込む:

| AclObjectStatus | STATE_DB 値 | 発生ケース |
|---|---|---|
| `ACTIVE` | `"Active"` | SET 正常完了 |
| `INACTIVE` | `"Inactive"` | 設定不正（bAllAttributesOk=false / validate()=false） |
| `PENDING_CREATION` | `"Pending creation"` | addAclTable() 失敗 (retry 中) |
| `PENDING_REMOVAL` | `"Pending removal"` | removeAclTable() 失敗 (retry 中) |

確認コマンド: `sonic-db-cli STATE_DB hgetall 'ACL_TABLE|<table_name>'`

ERROR_TABLE への書き込みはなし。syslog (`SWSS_LOG_ERROR`) のみ。

---

## retry パターンサマリ

| パターン | 対象ケース | 挙動 | STATE_DB |
|---|---|---|---|
| `it++` (無制限 retry) | ユーザ定義 type 未登録 (`getAclTableType()` nullptr) | ACL_TABLE_TYPE 登録待ち | 変更なし |
| `it++` (無制限 retry) | `addAclTable()` 失敗 | ASIC 能力不足等の SAI 一時エラー | "Pending creation" |
| `it++` (無制限 retry) | `updateAclTable()` 失敗 | 既存テーブル ports 更新失敗 | 変更なし |
| `it++` (無制限 retry) | `removeAclTable()` 失敗 | 配下 rule 削除失敗・SAI 削除失敗 | "Pending removal" |
| `erase` (no retry) | 属性不正 / unknown 属性 / validate() 失敗 | 設定値を修正して再 SET が必要 | "Inactive" |
| `erase` (no retry) | unknown op type | 内部不整合 | 変更なし |

---

## config rollback 挙動

- CONFIG_DB のエントリは erase 後も残る（orchagent は CONFIG_DB を書き戻さない）
- `INACTIVE` / `PENDING_CREATION` 状態での SAI への反映はゼロ（ハードウェア影響なし）
- 失敗後に正しい設定値で `DEL → SET` を行えばリカバリ可能
- `PENDING_REMOVAL` 状態では ACL_TABLE エントリが SAI 上に残ったまま CONFIG_DB からの DEL が pending になる
