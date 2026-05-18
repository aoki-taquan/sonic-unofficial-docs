# COPP port-binding (genetlink) 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/copp-port.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/copporch.cpp` (全行スキャン)

スキャン範囲:
- `createGenetlinkHostIf()` L657-680
- `createGenetlinkHostIfTable()` L419-471
- `removeGenetlinkHostIf()` L682-713
- `removeGenetlinkHostIfTable()` L473-500
- `processCoppRule()` L737-877 (genetlink 分岐 L833-856)
- `doTask()` L880-933

---

## 失敗パス一覧

### 1. allPortsReady() false → 全処理保留

`copporch.cpp:885-888`:

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

PortsOrch 初期化完了前にエントリが書き込まれた場合、`doTask()` が即 return。
genetlink HostIf は一切作成されず、`m_toSync` に蓄積されて次サイクルで再処理される。

### 2. Genetlink HostIf 二重作成 → task_failed → orchagent 処理停止

`copporch.cpp:835-840`:

```cpp
if (m_trap_group_hostif_map.find(m_trap_group_map[trap_group_name]) !=
        m_trap_group_hostif_map.end())
{
    SWSS_LOG_ERROR("Genetlink hostif exists for the trap group %s", ...);
    return task_process_status::task_failed;
}
```

同一 trap_group に対して genetlink フィールドを持つエントリが二度 SET された場合（orchagent 再起動なしに再書き込みされた場合など）、
`processCoppRule()` が `task_failed` を返す。
`doTask()` は当該エントリを erase して `return` し、後続の pending エントリも処理が停止する (L920-923)。

### 3. SAI create_hostif 失敗 → task_failed

`copporch.cpp:667-675`:

```cpp
sai_status = sai_hostif_api->create_hostif(...);
if (sai_status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_HOSTIF, sai_status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`create_hostif()` が `SAI_STATUS_SUCCESS` 以外を返した場合、`handleSaiCreateStatus()` + `parseHandleSaiStatusFailure()` により `false` が返り、呼び出し元 `processCoppRule()` で `task_failed` に変換される (L844-846)。

### 4. SAI create_hostif_table_entry 失敗 → task_failed

`copporch.cpp:457-464`:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_HOSTIF, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`createGenetlinkHostIfTable()` 内で trap_id ごとに `create_hostif_table_entry()` を呼ぶ。失敗すると `false` 返却 → `processCoppRule()` が `task_failed` (L848-850)。

### 5. trapGroupProcessTrapIdChange() 失敗 → task_failed

`copporch.cpp:853-856`:

```cpp
if (!trapGroupProcessTrapIdChange(trap_group_name, add_trap_ids, rem_trap_ids))
{
    return task_process_status::task_failed;
}
```

genetlink フィールド処理後に `trapGroupProcessTrapIdChange()` が呼ばれ、これが失敗すると `task_failed`。
genetlink HostIf / HostIfTable はすでに SAI に作成済みだが trap_id への適用が失敗した状態が残る。

### 6. DEL of default_trap_group → task_ignore

`copporch.cpp:861-865`:

```cpp
if (trap_group_name == default_trap_group)
{
    SWSS_LOG_WARN("Cannot remove default trap group");
    return task_process_status::task_ignore;
}
```

`default_trap_group` は削除不可。`task_ignore` として erase され、次アイテムへ進む。

### 7. 例外 → task_invalid_entry → erase & continue

`copporch.cpp:900-909`:

```cpp
catch(const out_of_range& e)
{
    task_status = task_process_status::task_invalid_entry;
}
catch(exception& e)
{
    task_status = task_process_status::task_invalid_entry;
}
```

`processCoppRule()` から例外が伝播した場合、`task_invalid_entry` として当該エントリを erase して継続する。

---

## doTask() の task_status 処理まとめ

| task_status | 発生条件 | doTask() 動作 |
|---|---|---|
| `task_success` / `task_ignore` | 正常完了 / 削除不可グループ | erase → 次アイテム |
| `task_invalid_entry` | 例外、未知 op | erase → 次アイテム（永久スキップ） |
| `task_failed` | SAI 失敗、二重作成、trapGroupProcessTrapIdChange 失敗 | erase → **return**（後続処理停止） |
| `task_need_retry` | SAI 一時失敗 | it++ → 次サイクルで再試行 |

`task_failed` 時は SWSS_LOG_ERROR が出力され、後続 pending エントリはすべて処理されない点に注意。
orchagent は終了せず生存するが、次回 `doTask()` 呼び出しまで他グループの COPP 処理も停止する。
