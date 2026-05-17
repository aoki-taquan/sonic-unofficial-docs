# srv6-counter — Phase D: 失敗・エラー処理

slug: srv6-counter
phase: D
date: 2026-05-17
sources:
  - sonic-swss/orchagent/srv6orch.cpp (L144–155, L184–210, L212–234, L236–249, L251–284, L286–312)

---

## 調査結果

### 1. `queryMySidCountersCapability()` 失敗 (L144–155)

```cpp
sai_status_t status = sai_query_attribute_capability(
    gSwitchId, SAI_OBJECT_TYPE_MY_SID_ENTRY,
    SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, &capability);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Could not query SRv6 MySID entry attribute ...");
    return false;
}
return capability.set_implemented && capability.create_implemented;
```

- `sai_query_attribute_capability` が `SAI_STATUS_SUCCESS` 以外を返した場合: `SWSS_LOG_WARN` → `return false`
- `capability.set_implemented` または `capability.create_implemented` が false の場合も `return false`
- → `m_mysid_counters_supported = false` → 以降の `enable` は常に無視

### 2. `setCountersState(enable)` — プラットフォーム非対応ガード (L255–258)

```cpp
if (!getMySidCountersSupported())
{
    SWSS_LOG_WARN("Ignoring SRv6 counters state change as they are not supported on this platform");
    return;
}
```

- プラットフォームが非対応の場合は early return。CONFIG_DB への書き込みは silent drop。
- 再起動なしに `m_mysid_counters_supported` を変えることはできない。

### 3. `addMySidCounter()` — SAI カウンタ生成失敗 (L188–192)

```cpp
if (!FlowCounterHandler::createGenericCounter(counter_oid))
{
    SWSS_LOG_ERROR("Failed to create SAI counter for SRv6 MySID entry");
    return false;
}
```

- `createGenericCounter()` 失敗時: `SWSS_LOG_ERROR` → `return false`
- 呼び出し元 `setCountersState()` では戻り値を確認せず次の MySID へ進む（partial failure: 一部 SID だけカウンタ未登録になる可能性がある）
- `COUNTERS_SRV6_NAME_MAP` や `m_pending_counters` への追加は行われない

### 4. `setMySidEntryCounter()` — SAI attribute set 失敗 (L244–248)

```cpp
auto status = sai_srv6_api->set_my_sid_entry_attribute(&sai_entry, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set my_sid entry counter oid to %s, rc: %s", ...);
}
```

- `SWSS_LOG_ERROR` ログのみ。リトライなし、ロールバックなし。
- SAI カウンタオブジェクトは作成済みだが MySID エントリへの紐付けが失敗した状態になる（孤立カウンタ）。
- `m_pending_counters` はそのまま残るため 1 秒タイマーで syncd 登録は試みられるが、MySID エントリへの紐付けがないためカウンタは常にゼロ。

### 5. `doTask(SelectableTimer)` — VIDTORID 待ちループ (L291–312)

```cpp
if (!gTraditionalFlexCounter || m_vid_to_rid_table->hget("", oid, value))
{
    // syncd へ登録
    it = m_pending_counters.erase(it);
}
else
{
    ++it; // 次回タイマーで再試行
}
if (m_pending_counters.empty())
{
    m_counter_update_timer->stop();
}
```

- `gTraditionalFlexCounter == true` かつ ASIC_DB の `VIDTORID` に OID が未登録の場合: スキップして次回タイマーで再試行（明示的なリトライ上限なし）
- タイマー間隔 = `SRV6_FLEX_COUNTER_UPDATE_TIMER = 1` 秒
- ASIC_DB に OID が永久に現れない場合: `m_pending_counters` が空にならず 1 秒ごとにタイマーが発火し続ける（リソースリーク的挙動だが実害は軽微）

### 6. `removeMySidCounter()` — SAI NULL OID 早期リターン (L216–218)

```cpp
if (counter_oid == SAI_NULL_OBJECT_ID)
{
    return;
}
```

- `addMySidCounter()` が失敗した SID に対して `removeMySidCounter()` を呼んでも安全にスキップされる。

### まとめ表

| 失敗ポイント | 挙動 | ログ | リトライ |
|------------|------|------|---------|
| `queryMySidCountersCapability` SAI エラー | `m_mysid_counters_supported=false`、以降 enable 全無視 | WARN | なし（再起動必要） |
| `queryMySidCountersCapability` capability false | 同上 | なし（WARN なし）| なし |
| `createGenericCounter` 失敗 | 当該 SID のカウンタ未登録、次 SID へ続行 | ERROR | なし |
| `set_my_sid_entry_attribute` 失敗 | 孤立カウンタ（OID 作成済みだが SID 未紐付け）| ERROR | なし |
| VIDTORID 未登録（gTraditionalFlexCounter） | 1 秒ごと再試行、上限なし | なし | 自動（タイマー） |
| `removeMySidCounter` counter_oid == SAI_NULL | 早期リターン（安全） | なし | N/A |
