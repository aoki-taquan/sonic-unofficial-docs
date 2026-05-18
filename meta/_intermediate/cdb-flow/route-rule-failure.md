# DASH_ROUTE_RULE_TABLE — 失敗挙動 (Phase D) 調査証跡

## 調査対象

- `sonic-swss/orchagent/dash/dashrouteorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 2 フェーズ bulker パターン

`doTaskRouteRuleTable()` は 2 フェーズ処理を採用している:

1. **pre-op** (`addInboundRouting`): 依存テーブルチェック → SAI エントリを bulker にエンキュー
2. `inbound_routing_bulker_.flush()` — SAI バルク実行
3. **post-op** (`addInboundRoutingPost`): SAI 結果評価 → CRM カウンタ更新

## SET 失敗パス

### 依存テーブル未登録 (pre-op リトライ)

```cpp
// dashrouteorch.cpp:425-428
if (!dash_orch_->getEni(ctxt.eni))
{
    SWSS_LOG_INFO("Retry as ENI entry %s not found", ctxt.eni.c_str());
    return false;
}
// dashrouteorch.cpp:430-433
if (ctxt.metadata.has_vnet() && gVnetNameToId.find(ctxt.metadata.vnet()) == gVnetNameToId.end())
{
    SWSS_LOG_INFO("Retry as vnet %s not found", ctxt.metadata.vnet().c_str());
    return false;
}
```

`return false` → `doTaskRouteRuleTable()` ループで `it++` → m_toSync に残留して自動リトライ。

### protobuf パース失敗 (ドロップ)

```cpp
// dashrouteorch.cpp:633-640
if (!parsePbMessage(kfvFieldsValues(tuple), ctxt.metadata))
{
    SWSS_LOG_WARN("Requires protobuff at InboundRouting :%s", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

`erase` でイベントを消費。リトライなし。

### SAI create 失敗 (post-op)

```cpp
// dashrouteorch.cpp:491-504
if (status != SAI_STATUS_SUCCESS)
{
    if (status == SAI_STATUS_ITEM_ALREADY_EXISTS)
    {
        return false;  // bulker 再試行
    }
    SWSS_LOG_ERROR("Failed to create inbound routing entry");
    task_process_status handle_status = handleSaiCreateStatus(
        (sai_api_t) SAI_API_DASH_INBOUND_ROUTING, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- `SAI_STATUS_ITEM_ALREADY_EXISTS` → `return false`（bulker 再試行）
- その他エラー → `handleSaiCreateStatus()` で task_need_retry / task_failed 判定
  - `task_need_retry`: `parseHandleSaiStatusFailure()` が `false` を返す → リトライ
  - `task_failed`: `parseHandleSaiStatusFailure()` が `true` を返す → erase

## DEL 失敗パス

### SAI remove 失敗 (post-op)

```cpp
// dashrouteorch.cpp:545-563
if (status == SAI_STATUS_SUCCESS)
{
    gCrmOrch->decCrmResUsedCounter(...);
    return true;
}
if (status == SAI_STATUS_NOT_EXECUTED)
{
    return false;  // bulker 再試行
}
task_process_status handle_status = handleSaiRemoveStatus(
    (sai_api_t) SAI_API_DASH_INBOUND_ROUTING, status);
if (handle_status != task_success)
{
    SWSS_LOG_ERROR("Failed to remove inbound routing entry for %s", key.c_str());
    return parseHandleSaiStatusFailure(handle_status);
}
```

- `SAI_STATUS_NOT_EXECUTED` → `return false`（bulker 再試行）
- その他エラー → `handleSaiRemoveStatus()` → `parseHandleSaiStatusFailure()`

## result テーブルへの書き込み

```cpp
// dashrouteorch.cpp:637-645
if (addInboundRouting(key, ctxt))
{
    it = consumer.m_toSync.erase(it);
    writeResultToDB(dash_route_rule_result_table_, key, result);
}

// dashrouteorch.cpp:653-657
if (removeInboundRouting(key, ctxt))
{
    it = consumer.m_toSync.erase(it);
    removeResultFromDB(dash_route_rule_result_table_, key);
}
```

SET 成功後のみ `writeResultToDB()` が呼ばれる。SAI 失敗時は書き込みなし。
DEL 成功後に `removeResultFromDB()` が呼ばれる。

## まとめ表

| 失敗シナリオ | イベント消費 | result テーブル | リトライ |
|---|---|---|---|
| ENI 未登録 | m_toSync 残留 | 書き込みなし | 自動 |
| vnet 未登録 | m_toSync 残留 | 書き込みなし | 自動 |
| protobuf パース失敗 | erase | 書き込みなし | なし |
| SAI_STATUS_ITEM_ALREADY_EXISTS | m_toSync 残留 | 書き込みなし | bulker 再試行 |
| SAI create (task_need_retry) | m_toSync 残留 | 書き込みなし | 自動 |
| SAI create (task_failed) | erase | 書き込みなし | なし |
| SAI remove (NOT_EXECUTED) | m_toSync 残留 | 削除されない | bulker 再試行 |
