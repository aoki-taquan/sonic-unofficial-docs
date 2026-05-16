# srv6-state — Phase A デフォルト導出メモ

## 対象ページ

`docs/reference/config-db/srv6-state.md`

## 調査ソース

| ファイル | ref |
|---------|-----|
| `sonic-swss/orchagent/srv6orch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-swss/orchagent/srv6orch.h` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `sonic-utilities/utilities_common/srv6stat.py` | master |
| `sonic-swss-common/common/schema.h` | master |

## 調査内容

### COUNTERS_DB スキーマ

SRv6 の "state" は STATE_DB ではなく **COUNTERS_DB** に格納される。

#### `COUNTERS_SRV6_NAME_MAP` (schema.h:257)

- 型: Redis Hash
- キー: `""` (空文字)
- フィールド: `<mysid_prefix>` (例: `fcbb:bbbb:20:f1::/64`)
- 値: SAI カウンタ OID (例: `oid:0x17000000001000`)
- 書き込み主体: `Srv6Orch::addMySidCounter()` → `m_mysid_counters_table->set()`
- 削除主体: `Srv6Orch::removeMySidCounter()` → `m_mysid_counters_table->hdel()`

#### `COUNTERS:<oid>` (COUNTERS_DB)

- フィールド: `SAI_COUNTER_STAT_PACKETS` / `SAI_COUNTER_STAT_BYTES`
- 型: integer (文字列)
- 書き込み主体: syncd の FlexCounter が `SRV6_STAT_COUNTER` グループとしてポーリング
  (`SRV6_STAT_COUNTER_POLLING_INTERVAL_MS = 10000` ms)

### コード由来デフォルト (srv6orch.cpp)

```cpp
// srv6orch.cpp:21-24
#define LOCATOR_DEFAULT_BLOCK_LEN "32"
#define LOCATOR_DEFAULT_NODE_LEN  "16"
#define LOCATOR_DEFAULT_FUNC_LEN  "16"
#define LOCATOR_DEFAULT_ARG_LEN   "0"
```

`getLocatorCfgFromDb()` (L331-354) は `fvsGetValue(..., true)` (Optional) で各フィールドを読み取り、
`get_value_or(LOCATOR_DEFAULT_*)` で fallback を適用する。これは orchagent が CONFIG_DB の
`SRV6_MY_LOCATORS` を読む際の fallback であり、**STATE_DB 書き込みには直接関係しない**が、
counter key 生成 (`getMySidCounterKey`) に影響する。

### カウンタ有効条件

```cpp
// srv6orch.cpp:144-155 queryMySidCountersCapability()
bool Srv6Orch::queryMySidCountersCapability() const {
    sai_attr_capability_t capability;
    sai_status_t status = sai_query_attribute_capability(
        gSwitchId, SAI_OBJECT_TYPE_MY_SID_ENTRY,
        SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, &capability);
    if (status != SAI_STATUS_SUCCESS) { return false; }
    return capability.set_implemented && capability.create_implemented;
}
```

`m_mysid_counters_supported = false` の場合、`COUNTERS_SRV6_NAME_MAP` は生成されない。

### カウンタキー生成ロジック

```cpp
// srv6orch.cpp:177-182
string Srv6Orch::getMySidCounterKey(const sai_my_sid_entry_t& sai_entry) const {
    auto mysid_addr = getMySidAddress(sai_entry).to_string();
    auto locator_cfg = getMySidEntryLocatorCfg(sai_entry);
    return getMySidPrefix(mysid_addr, locator_cfg);
}
// getMySidPrefix: mysid_addr + "/" + str(block_len + node_len + func_len)
```

プレフィックス長 = `block_len + node_len + func_len`。デフォルト (32+16+16) = `/64`。

### polling interval

```cpp
#define SRV6_STAT_COUNTER_POLLING_INTERVAL_MS 10000  // 10秒
#define SRV6_FLEX_COUNTER_UPDATE_TIMER 1             // 1秒 (OID 登録タイマー)
```

### srv6stat.py から読み取られる値

```python
COUNTER_PACKETS = "SAI_COUNTER_STAT_PACKETS"
COUNTER_BYTES   = "SAI_COUNTER_STAT_BYTES"
```

差分表示: `show srv6 stats` は保存済みカウンタとの差分を表示。マイナスになった場合は全量表示に fallback。

## 結論

| DB | キー | フィールド | デフォルト / fallback |
|----|------|----------|----------------------|
| COUNTERS_DB | `COUNTERS_SRV6_NAME_MAP` | `<mysid_prefix>` | フィールド不在 = カウンタ未登録（SAI 非対応またはカウンタ無効） |
| COUNTERS_DB | `COUNTERS:<oid>` | `SAI_COUNTER_STAT_PACKETS` | `"0"` (初期値) |
| COUNTERS_DB | `COUNTERS:<oid>` | `SAI_COUNTER_STAT_BYTES` | `"0"` (初期値) |
| (STATE_DB) | — | — | SRv6 専用 STATE_DB テーブルは存在しない |
