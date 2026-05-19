# fdb-aging Phase D — 失敗挙動 (Failure Behavior)

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp` (doAppSwitchTableTask, setAgingFDB)
- `sonic-swss/orchagent/saihelper.cpp` (handleSaiSetStatus, parseHandleSaiStatusFailure)
- `sonic-swss/orchagent/orch.h` (task_process_status 列挙)

## doAppSwitchTableTask() の失敗パス (L595-748)

### 1. 不明属性 → SWSS_LOG_ERROR + break (L617-623)

```cpp
// switchorch.cpp:617-623
else if (switch_attribute_map.find(attribute) == switch_attribute_map.end())
{
    if (switch_tunnel_attribute_map.find(attribute) == switch_tunnel_attribute_map.end())
    {
        SWSS_LOG_ERROR("Unsupported switch attribute %s", attribute.c_str());
        break;
    }
    ...
}
```

- `fdb_aging_time` は `switch_attribute_map` に登録済みのため通常は該当しない
- ただし同一エントリに不明属性が先行すると break で `fdb_aging_time` はスキップされる（Phase B 記載済み）

### 2. 無効値 → SWSS_LOG_ERROR + break (L709-714)

```cpp
// switchorch.cpp:709-714
if (invalid_attr)
{
    SWSS_LOG_ERROR("Invalid Attribute %s", attribute.c_str());
    break;
}
```

`fdb_aging_time` の値パースは `to_uint<uint32_t>(value)` (L665)。uint32_t に変換できない文字列（負数、非数値）を渡すと `invalid_attr = true` となり `break`。エントリは Consumer キューから削除（`erase`）されるため**再試行なし・silent drop**。

実際には `to_uint` が例外を投げず 0 に丸めるケースもあるため挙動は実装依存。

### 3. SAI set_switch_attribute 失敗 → handleSaiSetStatus 分岐 (L722-728)

```cpp
// switchorch.cpp:722-728
sai_status_t status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set switch attribute %s to %s, rv:%d",
            attribute.c_str(), value.c_str(), status);
    retry = (handleSaiSetStatus(SAI_API_SWITCH, status) == task_need_retry);
    break;
}
```

`handleSaiSetStatus` の分岐 (`saihelper.cpp:639-667`):

| SAI status | handleSaiSetStatus 戻り値 | retry | 備考 |
|---|---|---|---|
| `SAI_STATUS_SUCCESS` | task_success | false | 通常パス |
| `SAI_STATUS_OBJECT_IN_USE` | task_success | false | SET では非想定（warn のみ） |
| `ITEM_ALREADY_EXISTS` / `ITEM_NOT_FOUND` / `ADDR_NOT_FOUND` | task_success | false | success 扱い |
| `INSUFFICIENT_RESOURCES` / `TABLE_FULL` / `NO_MEMORY` / `NV_STORAGE_FULL` | task_need_retry | **true** | `it++` → 次ループ再試行（無制限） |
| その他（デフォルト） | task_failed | false | `handleSaiFailure` 経由で SAI dump リクエスト → erase |

`retry = true` の場合 `it++`（エントリ保持）、false の場合 `consumer.m_toSync.erase(it)`（エントリ破棄）。

### 4. unsupported_attr → SWSS_LOG_ERROR + continue (L716-720)

```cpp
// switchorch.cpp:716-720
if (unsupported_attr){
    SWSS_LOG_ERROR("Unsupported Attribute %s", attribute.c_str());
    continue;
}
```

`fdb_aging_time` は `querySwitchCapability` を呼ばないため `unsupported_attr` にはならない。

### 5. DEL 操作 → SWSS_LOG_WARN + erase (L743-749)

`doAppSwitchTableTask` は `DEL_COMMAND` を受け取ると `Unsupported operation` を warn して erase する。`SWITCH_TABLE:switch` への DEL は通常 swssconfig から発行されないため実運用上は非遭遇。

## setAgingFDB() の失敗パス (L1671-1688)

warm-reboot パスから直接呼ばれる `setAgingFDB(sec)`:

```cpp
// switchorch.cpp:1671-1688
bool SwitchOrch::setAgingFDB(uint32_t sec)
{
    ...
    auto status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to set switch %" PRIx64 " fdb_aging_time attribute: %d", gSwitchId, status);
        task_process_status handle_status = handleSaiSetStatus(SAI_API_SWITCH, status);
        if (handle_status != task_success)
        {
            return parseHandleSaiStatusFailure(handle_status);
        }
    }
    return true;
}
```

`parseHandleSaiStatusFailure` (`saihelper.cpp:745-762`):
- `task_need_retry` → return `false`（= 呼び出し元が失敗とみなす）
- `task_failed` → return `true`（= 失敗だが再試行不要）

呼び出し元 `orchdaemon.cpp:1068` は返り値を無視しているため、warm-reboot 中の `setAgingFDB(0)` 失敗は**無言で継続**する。MAC エントリが warm-reboot 中に aging される可能性がある（想定内リスク）。

## STATE_DB・ERROR_TABLE への影響

- **STATE_DB**: `fdb_aging_time` に関する書き込みなし（SAI 設定のみ）
- **ERROR_TABLE**: 書き込みなし（SWSS_LOG_ERROR のみ）
- **APPL_DB エントリ**: `retry = false` の場合エントリ削除（再書き込みなし）

## 失敗パターン一覧

| # | ケース | 発生箇所 | 挙動 | retry | ログ |
|---|--------|---------|------|-------|------|
| 1 | 不明属性が同一エントリに先行 | switchorch.cpp:622-623 | break → 残フィールドスキップ → erase | なし | ERROR |
| 2 | 無効値（非 uint32_t 変換可能） | switchorch.cpp:709-714 | break → erase | なし | ERROR |
| 3 | SAI INSUFFICIENT_RESOURCES 等 | switchorch.cpp:723-728 + saihelper.cpp:658-662 | it++ → 無制限再試行 | 無制限 | ERROR |
| 4 | SAI その他エラー | switchorch.cpp:723-728 + saihelper.cpp:663-667 | handleSaiFailure → erase | なし | ERROR |
| 5 | setAgingFDB SAI 失敗 (warm-reboot) | switchorch.cpp:1677-1684 | 呼び元が戻り値無視 → 無言継続 | なし | ERROR |
| 6 | DEL 操作受信 | switchorch.cpp:743-749 | warn → erase | なし | WARN |
