# TC_TO_QUEUE_MAP — Phase D: 失敗挙動 (failure)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 抽出根拠

`TcToQueueMapHandler::convertFieldValuesToAttributes()` / `addQosItem()` / `QosMapHandler::processWorkItem()` を精査。

## 失敗パターン一覧

### 1. 不正な TC / queue_index 値 → `task_invalid_entry`

```cpp
// qosorch.cpp L441-442
tc_map_list.list[ind].key.tc = (uint8_t)stoi(fvField(*i));
tc_map_list.list[ind].value.queue_index = (uint8_t)stoi(fvValue(*i));
```

`stoi()` は try-catch なしで呼ばれるため、TC フィールドまたは queue インデックスが数値に変換できない場合（空文字列・英字混入など）は C++ 例外が上位へ伝播し、`convertFieldValuesToAttributes()` が `false` を返す。
その結果 `processWorkItem()` は `task_invalid_entry` を返し、エントリはキューから除去される（silent drop）。

### 2. SAI `create_qos_map()` 失敗 → `task_failed`

```cpp
// qosorch.cpp L469-471
if (SAI_STATUS_SUCCESS != sai_status)
{
    SWSS_LOG_ERROR("Failed to create tc_to_queue map. status:%d", sai_status);
    return SAI_NULL_OBJECT_ID;
}
```

`addQosItem()` が `SAI_NULL_OBJECT_ID` を返すと `processWorkItem()` で検出され：

```cpp
// qosorch.cpp L162-166
SWSS_LOG_ERROR("Failed to create [%s:%s]", qos_map_type_name.c_str(), qos_object_name.c_str());
freeAttribResources(attributes);
return task_process_status::task_failed;
```

`task_failed` が返り、Consumer はエントリを再キューイングする。

### 3. SAI `set_qos_map_attribute()` 失敗（既存マップ更新時）→ `task_failed`

```cpp
// qosorch.cpp L207-209 (modifyQosItem)
sai_status_t sai_status = sai_qos_map_api->set_qos_map_attribute(sai_object, &attributes[0]);
if (SAI_STATUS_SUCCESS != sai_status)
```

`modifyQosItem()` が失敗すると：

```cpp
// qosorch.cpp L153-156
SWSS_LOG_ERROR("Failed to set [%s:%s]", qos_map_type_name.c_str(), qos_object_name.c_str());
freeAttribResources(attributes);
return task_process_status::task_failed;
```

### 4. DEL 対象オブジェクトが SAI 未作成 → `task_invalid_entry`

```cpp
// qosorch.cpp L176-179
if (SAI_NULL_OBJECT_ID == sai_object)
{
    SWSS_LOG_ERROR("Object with name:%s not found.", qos_object_name.c_str());
    return task_process_status::task_invalid_entry;
}
```

CONFIG_DB に DEL イベントが来たが、対応する SAI オブジェクトが存在しない場合（例: 先行 create が失敗していた場合）。エントリは除去される。

### 5. PORT_QOS_MAP 参照中の DEL → `task_need_retry` + pending

```cpp
// qosorch.cpp L181-186
if (gQosOrch->isObjectBeingReferenced(...))
{
    SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)", ...);
    m_pendingRemove = true;
    return task_process_status::task_need_retry;
}
```

参照が外れるまで削除は保留。参照解放後に再処理される。

### 6. pending remove 中の SET → `task_need_retry`

```cpp
// qosorch.cpp L136-139
if (m_pendingRemove && op == SET_COMMAND)
{
    SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry", ...);
    return task_process_status::task_need_retry;
}
```

## まとめ

| 状況 | 戻り値 | ログレベル | ログメッセージ |
|------|--------|-----------|--------------|
| TC/queue 値が非数値 | `task_invalid_entry` | (例外) | — |
| SAI create_qos_map 失敗 | `task_failed` | ERROR | `"Failed to create tc_to_queue map. status:%d"` |
| SAI set_qos_map_attribute 失敗 | `task_failed` | ERROR | `"Failed to set [TC_TO_QUEUE_MAP:<name>]"` |
| DEL 対象が SAI 未作成 | `task_invalid_entry` | ERROR | `"Object with name:<name> not found."` |
| 参照中のマップへの DEL | `task_need_retry` | NOTICE | `"Can't remove object <name> due to being referenced"` |
| pending remove 中の SET | `task_need_retry` | NOTICE | `"Entry ... is pending remove, need retry"` |
