# CONFIG_DB FDB テーブル — Phase D 失敗挙動スキャンノート

対象テーブル: `CONFIG_DB FDB`
Consumer: `swssconfig` (CONFIG_DB → APPL_DB 転記) → `FdbOrch::doTask(Consumer&)` → `addFdbEntry()` / `removeFdbEntry()`
スキャン範囲: `fdborch.cpp` L707-921 (doTask), L1277-1575 (addFdbEntry), L1631-1715 (removeFdbEntry)

---

## SET 時の失敗パターン

### 1. VLAN 未解決（VLAN OID 取得失敗）

`doTask()` L739-760: `m_portsOrch->getPort(keys[0], vlan)` が false の場合:

- **SET_COMMAND**: `it++` して無制限再試行（待機ループ）
- **DEL_COMMAND**: `consumer.m_toSync.erase(it)` で silently drop
- CONFIG_DB エントリは残存。orchagent エラーログなし（SWSS_LOG_INFO のみ）。

### 2. VXLAN FDB: DIP トンネル未作成

`doTask()` L836-841: `isDipTunnelsSupported()` かつ `getTunnelPortName(remote_ip)` 失敗（トンネルポートが未作成）:

- `consumer.m_toSync.erase(it)` で silently drop（retry なし）
- evidence: `fdborch.cpp:836-841`

### 3. VXLAN FDB: SIP VTEP 未取得

`doTask()` L847-853: `getEVPNVtep()` が NULL の場合:

- `consumer.m_toSync.erase(it)` で silently drop（retry なし）
- evidence: `fdborch.cpp:847-853`

### 4. addFdbEntry() 失敗 → retry

`doTask()` L870: `addFdbEntry(entry, port, fdbData)` が `false` を返した場合:

- `it++` で無制限 retry
- `addFdbEntry()` が false を返す主なケース:
  - VLAN BV_ID 解決失敗（`fdborch.cpp:1291-1294`）→ SWSS_LOG_NOTICE のみ
  - SAI `create_fdb_entry()` 失敗かつ `handleSaiCreateStatus()` → `task_failed` / `task_need_retry` → `parseHandleSaiStatusFailure(handle_status)` が true を返した場合（`fdborch.cpp:1536-1541`）

### 5. SAI create_fdb_entry() 失敗

`addFdbEntry()` L1532-1541:

```cpp
status = sai_fdb_api->create_fdb_entry(&fdb_entry, (uint32_t)attrs.size(), attrs.data());
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create %s FDB %s in %s on %s, rv:%d", ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_FDB, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- SWSS_LOG_ERROR を出力
- `handleSaiCreateStatus()` の判定結果で retry / drop が決まる（FIXME コメントあり、現状は status 値に関係なく判定）
- STATE_DB への書き込みは行われない（`storeFdbEntryState()` は SAI 成功後のみ呼ばれる）

### 6. SAI set_fdb_entry_attribute() 失敗（mac-update）

`addFdbEntry()` L1508-1515: 既存エントリ更新時の属性設定失敗:

```cpp
SWSS_LOG_ERROR("macUpdate-Failed for attr.id=0x%x for FDB %s in %s on %s, rv:%d", ...);
task_process_status handle_status = handleSaiSetStatus(SAI_API_FDB, status);
if (handle_status != task_success)
{
    return parseHandleSaiStatusFailure(handle_status);
}
```

- SWSS_LOG_ERROR 出力。`parseHandleSaiStatusFailure` が true なら `addFdbEntry()` は false を返し、`doTask()` は `it++` で retry。

### 7. assert(type) によるプロセスクラッシュ

`doTask()` L830: 有効値以外の `type` が渡ると:

```cpp
assert(type == "dynamic" || type == "dynamic_local" || type == "static");
```

- orchagent プロセスがクラッシュ（SIGABRT）
- 復旧: orchagent 再起動。CONFIG_DB エントリは残存するため再起動後に再処理される

---

## DEL 時の失敗パターン

### 8. origin 不一致（silently ignore）

`removeFdbEntry()` L1654-1691: `fdbData.origin != origin` かつ MCLAG ダウン例外に該当しない場合:

- `deleteFdbEntryFromSavedFDB()` を試みた後 `return true`（成功扱い）
- `doTask()` 側では erase → retry なし
- エントリは orchagent キャッシュ（`m_entries`）に残る。CONFIG_DB エントリは消える
- SWSS_LOG_INFO のみ（ERROR なし）

### 9. SAI remove_fdb_entry() 失敗

`removeFdbEntry()` L1702-1709:

```cpp
status = sai_fdb_api->remove_fdb_entry(&fdb_entry);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("FdbOrch RemoveFDBEntry: Failed to remove FDB entry. mac=%s, bv_id=0x%" PRIx64, ...);
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_FDB, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- SWSS_LOG_ERROR 出力
- `parseHandleSaiStatusFailure` が true → `removeFdbEntry()` は false → `doTask()` は `it++` で無制限 retry

### 10. エントリが orchagent キャッシュに不在（DEL 時）

`removeFdbEntry()` L1649-1655: `m_entries.find(entry)` が `end()` の場合:

- `deleteFdbEntryFromSavedFDB()` を試みて `return true`（成功扱い）
- SAI 操作なし、STATE_DB 削除なし
- SWSS_LOG_INFO のみ

---

## 失敗サマリ表

| # | 失敗ケース | 発生箇所 | 挙動 | retry | ログレベル |
|---|-----------|---------|------|-------|-----------|
| 1 | VLAN 未解決（SET） | `doTask:739` | `it++`（待機ループ） | 無制限 | INFO |
| 2 | VXLAN DIP トンネル未作成 | `doTask:836` | erase（drop） | なし | — |
| 3 | VXLAN SIP VTEP 未取得 | `doTask:847` | erase（drop） | なし | — |
| 4 | `addFdbEntry()` false | `doTask:870` | `it++` | 無制限 | INFO/ERROR |
| 5 | SAI create_fdb_entry 失敗 | `addFdbEntry:1532` | SWSS_LOG_ERROR → parseHandleSaiStatus | 条件次第 | ERROR |
| 6 | SAI set_fdb_entry_attr 失敗（update） | `addFdbEntry:1508` | SWSS_LOG_ERROR → parseHandleSaiStatus | 条件次第 | ERROR |
| 7 | `type` 不正値 | `doTask:830` | assert クラッシュ | 再起動後 | — |
| 8 | origin 不一致（DEL） | `removeFdbEntry:1654` | erase（silently ignore） | なし | INFO |
| 9 | SAI remove_fdb_entry 失敗 | `removeFdbEntry:1702` | `it++` | 無制限 | ERROR |
| 10 | エントリ不在（DEL） | `removeFdbEntry:1649` | erase（成功扱い） | なし | INFO |

---

## 補足: STATE_DB・ERROR_TABLE への書込み

- STATE_DB `FDB_TABLE` への書込みは `storeFdbEntryState()` 経由であり、`addFdbEntry()` が SAI 成功後にのみ呼ばれる。失敗時は書込みされない。
- `ERROR_TABLE` への書込みはなし。
- CONFIG_DB `FDB` エントリは失敗後も残存する（orchagent は書き戻さない）。
