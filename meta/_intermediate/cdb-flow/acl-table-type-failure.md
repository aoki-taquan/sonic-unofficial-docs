# ACL_TABLE_TYPE 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/acl-table-type.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/aclorch.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)
- `sonic-swss/orchagent/acltable.h` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)

スキャン範囲: `doAclTableTypeTask()` L5738-5774, `AclTableTypeParser::parse()` L752-794,
`parseAclTableTypeMatches()` L796-829, `parseAclTableTypeActions()` L831-878,
`parseAclTableTypeBindPointTypes()` L881-897, `addAclTableType()` L4912-4930,
`removeAclTableType()` L4932-4948

---

## 失敗パス一覧

### 1. SET: `MATCHES` に未知の match キー → parse() false → erase (no retry)

`aclorch.cpp:803-820`:

```cpp
auto matchIt = aclMatchLookup.find(match);
auto rangeMatchIt = aclRangeTypeLookup.find(match);
if (rangeMatchIt != aclRangeTypeLookup.end()) { ... }
else if (matchIt != aclMatchLookup.end()) { ... }
else
{
    SWSS_LOG_ERROR("Unknown match %s", match.c_str());
    return false;
}
```

`parseAclTableTypeMatches()` が `false` → `parse()` が `false` →
`doAclTableTypeTask()` L5753-5755:
```cpp
SWSS_LOG_ERROR("Failed to parse ACL table type configuration %s", key.c_str());
it = consumer.m_toSync.erase(it);
```
**retry なし。CONFIG_DB の値は残る。STATE_DB 書き込みなし。rollback なし。**

---

### 2. SET: `ACTIONS` に未知の action キー → parse() false → erase (no retry)

`aclorch.cpp:868-872`:

```cpp
else
{
    SWSS_LOG_ERROR("Unknown action %s", action.c_str());
    return false;
}
```

`parseAclTableTypeActions()` が `false` → `parse()` が `false` → `erase(it)`。
`aclL3ActionLookup`, `aclMirrorStageLookup`, `aclDTelActionLookup`, `aclOtherActionLookup`,
`aclMetadataDscpActionLookup`, `aclInnerActionLookup` のいずれにも存在しない action 名が対象。
**retry なし。rollback なし。**

---

### 3. SET: `BIND_POINTS` に未知の値 → parse() false → erase (no retry)

`aclorch.cpp:886-890`:

```cpp
auto bpointIt = aclBindPointTypeLookup.find(bpointType);
if (bpointIt == aclBindPointTypeLookup.end())
{
    SWSS_LOG_ERROR("Unknown bind point %s", bpointType.c_str());
    return false;
}
```

`aclBindPointTypeLookup` に存在しない値（`PORT` / `PORTCHANNEL` 以外）は即 `false`。
**retry なし。rollback なし。**

---

### 4. SET: 未知フィールド名 → parse() false → erase (no retry)

`aclorch.cpp:786-790`:

```cpp
else
{
    SWSS_LOG_ERROR("Unknown field %s: value %s", field.c_str(), value.c_str());
    return false;
}
```

既知フィールドは `MATCHES`(`ACL_TABLE_TYPE_MATCHES`) / `ACTIONS`(`ACL_TABLE_TYPE_ACTIONS`) /
`BIND_POINTS`(`ACL_TABLE_TYPE_BPOINT_TYPES`) の 3 つのみ。それ以外の field 名は即 false → erase。
**retry なし。rollback なし。**

---

### 5. SET: 同名 type が既に存在 → addAclTableType() false → ログのみ（erase は実行）

`aclorch.cpp:4922-4925`:

```cpp
if (m_AclTableTypes.find(tableType.getName()) != m_AclTableTypes.end())
{
    SWSS_LOG_ERROR("Table type %s already exists", tableType.getName().c_str());
    return false;
}
```

`doAclTableTypeTask()` L5759 で `addAclTableType()` が `false` を返しても、L5760 の
`SWSS_LOG_NOTICE("Created ACL table type %s")` は出力されずに処理が続き、L5772 の
`it = consumer.m_toSync.erase(it)` で erase される（SET_COMMAND ブロック全体が erase）。
組み込み型名（`L3`, `L3V6`, `MIRROR` 等）を CONFIG_DB に書き込んだ場合もこのパスを通る。
**retry なし。既存の m_AclTableTypes エントリへの影響なし。**

---

### 6. DEL: 未登録 type 名 → removeAclTableType() false → ログのみ（erase は実行）

`aclorch.cpp:4941-4944`:

```cpp
if (!m_AclTableTypes.erase(tableTypeName))
{
    SWSS_LOG_ERROR("Unknown table type %s", tableTypeName.c_str());
    return false;
}
```

`doAclTableTypeTask()` L5764 で `removeAclTableType()` が `false` を返しても、L5772 の
`it = consumer.m_toSync.erase(it)` で erase される（DEL_COMMAND ブロック全体が erase）。
**retry なし。CONFIG_DB の値も DEL は完了している（DB 操作と orchagent 処理は独立）。**

---

### 7. 未知 op type → SWSS_LOG_ERROR + erase (no retry)

`aclorch.cpp:5767-5770`:

```cpp
else
{
    SWSS_LOG_ERROR("Unknown operation type %s", op.c_str());
}
```

`SET_COMMAND` / `DEL_COMMAND` 以外の op type は SWSS_LOG_ERROR を出力し、L5772 の共通 erase で処理を終了。
**retry なし。**

---

## retry パターンサマリ

`ACL_TABLE_TYPE` の処理には **`it++` (retry) パターンは存在しない**。
すべての失敗ケースで `erase(it)` が実行され、再処理は行われない。

| 失敗ケース | 結果 | retry |
|---|---|---|
| MATCHES に未知 match キー | parse() false → erase | なし |
| ACTIONS に未知 action キー | parse() false → erase | なし |
| BIND_POINTS に未知値 | parse() false → erase | なし |
| 未知フィールド名 | parse() false → erase | なし |
| 同名 type 既存 (組み込み型含む) | addAclTableType() false → erase | なし |
| DEL で未登録 type 名 | removeAclTableType() false → erase | なし |
| 未知 op type | ERROR + erase | なし |

---

## STATE_DB / ERROR_TABLE への影響

`ACL_TABLE_TYPE` の処理は `setAclTableStatus()` を呼び出さない。
STATE_DB への書き込みは一切発生しない。ERROR_TABLE への書き込みもなし。
エラー情報は `SWSS_LOG_ERROR` (syslog) のみ。

確認コマンド:
```bash
# syslog でエラー確認
journalctl -u swss -n 50 | grep "ACL table type"
```

---

## config rollback 挙動

- CONFIG_DB のエントリは orchagent が書き戻さない（失敗後も CONFIG_DB に残る）
- 失敗しても SAI への影響はゼロ（`ACL_TABLE_TYPE` は SAI オブジェクト非生成）
- 修正後に `DEL → SET` で同名エントリを再作成すれば即座にリカバリ可能
- `ACTIONS` 空文字列 (`""`) の場合は `tokenize()` が空リストを返し parse は成功する（エラーにならない）
