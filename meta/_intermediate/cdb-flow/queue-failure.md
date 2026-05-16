# QUEUE 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/queue.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (`handleQueueTable`, `applySchedulerToQueueSchedulerGroup`, `applyWredProfileToQueue`)

---

## 失敗パス一覧

### 1. key トークン数不正 → `task_invalid_entry`

`qosorch.cpp:1772-1811` — `handleQueueTable()`:

非 VOQ 環境でトークンが 2 個でない、または VOQ 環境でトークンが 4 個でない場合:

```cpp
// 非 VOQ
if (tokens.size() != 2)
{
    SWSS_LOG_ERROR("malformed key:%s. Must contain 2 tokens", key.c_str());
    return task_process_status::task_invalid_entry;
}
// VOQ
if (tokens.size() != 4)
{
    SWSS_LOG_ERROR("malformed key:%s. Must contain 4 tokens", key.c_str());
    return task_process_status::task_invalid_entry;
}
```

- ログ: `SWSS_LOG_ERROR "malformed key: ... Must contain N tokens"`
- 効果: `task_invalid_entry` → エントリ削除。**retry なし。rollback なし。**

---

### 2. `qindex` パース失敗 → `task_invalid_entry`

`qosorch.cpp:1781-1811` — `handleQueueTable()`:

```cpp
if (!parseIndexRange(tokens[1], range_low, range_high))
{
    SWSS_LOG_ERROR("Failed to parse range:%s", tokens[1].c_str());
    return task_process_status::task_invalid_entry;
}
```

`parseIndexRange` は整数または `X-Y` (`X < Y`、X と Y は非負整数) のみ受け付ける。同値 `X-X` や非整数文字列は失敗する (実装: `orch.cpp`)。YANG 型は `string` のため YANG バリデーションでは弾かれない。

- ログ: `SWSS_LOG_ERROR "Failed to parse range: ..."`
- 効果: `task_invalid_entry` → エントリ削除。**retry なし。rollback なし。**

---

### 3. `scheduler` 参照未解決 → `task_need_retry` または `task_failed`

`qosorch.cpp:1822-1854` — SET 処理内 `resolveFieldRefValue()`:

```cpp
if(ref_resolve_status::not_resolved == resolve_result)
{
    SWSS_LOG_INFO("Missing or invalid scheduler reference");
    return task_process_status::task_need_retry;
}
SWSS_LOG_ERROR("Resolving scheduler reference failed");
return task_process_status::task_failed;
```

- `not_resolved`（SCHEDULER エントリが未作成）: `task_need_retry` → `m_toSync` に残し次回再試行
- それ以外の解決失敗（内部エラー等）: `task_failed` → エントリ削除
- ログ (retry): `SWSS_LOG_INFO "Missing or invalid scheduler reference"`
- ログ (failed): `SWSS_LOG_ERROR "Resolving scheduler reference failed"`
- 効果 (retry): **SCHEDULER 登録後の次 doTask() サイクルで自動再試行。上限なし。**
- 効果 (failed): エントリ削除。rollback なし。

---

### 4. `wred_profile` 参照未解決 → `task_need_retry` または `task_failed`

`qosorch.cpp:1856-1887` — 同パターン:

```cpp
if(ref_resolve_status::not_resolved == resolve_result)
{
    SWSS_LOG_INFO("Missing or invalid wred profile reference");
    return task_process_status::task_need_retry;
}
SWSS_LOG_ERROR("Resolving wred profile reference failed");
return task_process_status::task_failed;
```

- `scheduler` と同一メカニズム。WRED_PROFILE 登録後に自動再試行。
- ログ (retry): `SWSS_LOG_INFO "Missing or invalid wred profile reference"`
- ログ (failed): `SWSS_LOG_ERROR "Resolving wred profile reference failed"`

---

### 5. 存在しないポート名 → `task_invalid_entry`

`qosorch.cpp:1911-1915` — ポートループ内:

```cpp
if (!gPortsOrch->getPort(port_name, port))
{
    SWSS_LOG_ERROR("Port with alias:%s not found", port_name.c_str());
    return task_process_status::task_invalid_entry;
}
```

- ログ: `SWSS_LOG_ERROR "Port with alias: ... not found"`
- 効果: `task_invalid_entry` → エントリ削除。**retry なし。rollback なし。**
- 注意: queue index ループに入る前に返るため、複数 port 指定の途中ポートで失敗した場合、先行ポートへの適用は rollback されない。

---

### 6. queue index 超過 → `task_failed`

`qosorch.cpp:1670-1674` (`applySchedulerToQueueSchedulerGroup`) および `qosorch.cpp:1727-1731` (`applyWredProfileToQueue`):

```cpp
if (port.m_queue_ids.size() <= queue_ind)
{
    SWSS_LOG_ERROR("Invalid queue index specified:%zd", queue_ind);
    return false;
}
```

呼び出し元 `handleQueueTable` が `false` を受け取り `task_failed` を返す (`qosorch.cpp:1926-1929`):

```cpp
if (!result)
{
    SWSS_LOG_ERROR("Failed setting field:%s to port:%s, queue:%zd, line:%d", ...);
    return task_process_status::task_failed;
}
```

- ログ: `SWSS_LOG_ERROR "Invalid queue index specified: N"` + `SWSS_LOG_ERROR "Failed setting field: ... "`
- 効果: `task_failed` → エントリ削除。**retry なし。rollback なし。**
- 注意: range `X-Y` 指定の途中の index で失敗した場合、range_low から失敗 index の直前まで適用済み — **部分適用が発生する**。rollback なし。

---

### 7. scheduler group 未検出 → `task_failed`

`qosorch.cpp:1658-1663` and `1677-1682` (`applySchedulerToQueueSchedulerGroup`):

```cpp
group_id = getSchedulerGroup(port, queue_id);
if(group_id == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_ERROR("Failed to find a scheduler group for port: %s queue: %zu", port.m_alias.c_str(), queue_ind);
    return false;
}
```

- ログ: `SWSS_LOG_ERROR "Failed to find a scheduler group for port: X queue: N"`
- 効果: `false` → `handleQueueTable` が `task_failed` を返す。エントリ削除。**retry なし。**

---

### 8. SAI scheduler group attribute 設定失敗 → `task_failed` (handleSaiSetStatus 依存)

`qosorch.cpp:1692-1700` (`applySchedulerToQueueSchedulerGroup`):

```cpp
sai_status = sai_scheduler_group_api->set_scheduler_group_attribute(group_id, &attr);
if (SAI_STATUS_SUCCESS != sai_status)
{
    SWSS_LOG_ERROR("Failed applying scheduler profile:0x%" PRIx64 " to scheduler group:0x%" PRIx64 ", port:%s", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_SCHEDULER_GROUP, sai_status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`handleSaiSetStatus()` は SAI 戻り値に応じて `task_need_retry` / `task_failed` を返す。`parseHandleSaiStatusFailure()` はそれを `bool (false)` に変換し、`handleQueueTable` が `task_failed` を返す。

- ログ: `SWSS_LOG_ERROR "Failed applying scheduler profile: ... to scheduler group: ..., port: ..."`
- 効果: SAI の種類によって retry / 永続失敗に分岐。実際の SAI エラーコードがログに記録される。

---

### 9. SAI queue WRED attribute 設定失敗 → `task_failed` (handleSaiSetStatus 依存)

`qosorch.cpp:1737-1745` (`applyWredProfileToQueue`):

```cpp
sai_status = sai_queue_api->set_queue_attribute(queue_id, &attr);
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set queue attribute:%d", sai_status);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_QUEUE, sai_status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ログ: `SWSS_LOG_ERROR "Failed to set queue attribute: N"`
- 効果: `false` → `handleQueueTable` が `task_failed`。**retry なし（handleSaiSetStatus が task_need_retry を返した場合を除く）。**

---

### 10. Unknown operation → `task_invalid_entry`

`qosorch.cpp:1895-1899`:

```cpp
SWSS_LOG_ERROR("Unknown operation type %s", op.c_str());
return task_process_status::task_invalid_entry;
```

SET / DEL 以外の操作文字列が来た場合（通常は発生しない）。

---

### 11. VOQ: remote system port の scheduler → no-op (成功扱い)

`qosorch.cpp:1639-1641` (`applySchedulerToQueueSchedulerGroup`):

```cpp
if(port.m_system_port_info.type == SAI_SYSTEM_PORT_TYPE_REMOTE)
{
    return true;
}
```

VOQ シャーシのリモートシステムポートには scheduler を適用しない（no-op で `true` を返す）。エラーログなし。

---

## retry / recovery メカニズム

QUEUE テーブルは orchagent の `Consumer` ベースの `task_process_status` パターンを使用する。

| ステータス | 挙動 |
|---|---|
| `task_success` | エントリを `m_toSync` から削除（完了） |
| `task_need_retry` | エントリを `m_toSync` に残す。次の doTask() で再処理（タイミングは SELECT timeout 次第、通常 1-2 秒） |
| `task_invalid_entry` | エントリを `m_toSync` から削除（永続エラー、syslog 記録のみ） |
| `task_failed` | エントリを `m_toSync` から削除（永続エラー、syslog 記録のみ） |

retry 上限: なし（`task_need_retry` は SCHEDULER / WRED_PROFILE が登録されるまで無制限継続）。
backoff: なし（SELECT timeout ベース）。

---

## 部分適用の罠

`scheduler` と `wred_profile` はそれぞれ独立して適用される（`qosorch.cpp:1922-1944`）。
`scheduler` 適用成功後に `wred_profile` 適用で `task_failed` が返ると:

- `scheduler` は SAI に書き込み済み（**rollback されない**）
- `wred_profile` は未適用
- エントリ全体が削除される
- 次に CONFIG_DB の同エントリが再投入されるまで inconsistent な状態が続く

range 指定 (`X-Y`) の途中での失敗も同様に部分適用が残る。

---

## STATE_DB / ERROR_TABLE への記録

- QosOrch は失敗時に STATE_DB / ERROR_TABLE への書き込みを行わない
- 失敗はすべて `SWSS_LOG_ERROR` / `SWSS_LOG_INFO` のみ (syslog 記録)
- `show queue counters` / `sonic-db-cli CONFIG_DB keys 'QUEUE|...'` で設定は確認できるが、実際に SAI に反映されたかは `sonic-db-cli ASIC_DB hgetall` で確認が必要
