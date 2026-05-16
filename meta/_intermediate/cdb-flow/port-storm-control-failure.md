# port-storm-control — Phase D 失敗挙動 中間ファイル

ソース: `sonic-swss/orchagent/policerorch.cpp`  
対象関数: `PolicerOrch::handlePortStormControlTable()`

## 抽出した失敗挙動

### 1. PORT 未解決 → silent drop (task_success)

```cpp
// policerorch.cpp:139-143
if (!gPortsOrch->getPort(interface_name, port))
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found",
            storm_type.c_str(), interface_name.c_str());
    return task_process_status::task_success;
}
```

- `gPortsOrch->getPort()` が false を返す場合（ポートオブジェクトがまだ初期化されていない等）
- `task_success` を返すため **エントリは erase される**（リトライなし）
- SWSS_LOG_ERROR はログに残るが、エントリは永久に消える（silent drop）

### 2. 非 Ethernet インタフェース → silent drop (task_success)

```cpp
// policerorch.cpp:131-137
if (strncmp(interface_name.c_str(), ETHERNET_PREFIX, strlen(ETHERNET_PREFIX)))
{
    SWSS_LOG_ERROR("%s: Unsupported / Invalid interface %s",
            storm_type.c_str(), interface_name.c_str());
    return task_process_status::task_success;
}
```

- LAG / VLAN / PortChannel など "Ethernet" プレフィックスを持たないインタフェース
- `task_success` → silent drop（リトライなし、エントリ消去）

### 3. storm_type 不正 → task_failed (エントリ消去)

```cpp
// policerorch.cpp:218-219 (SET_COMMAND パス)
SWSS_LOG_ERROR("Unknown storm_type %s", storm_type.c_str());
return task_process_status::task_failed;

// policerorch.cpp:338-339 (DEL_COMMAND パス)
SWSS_LOG_ERROR("Unknown storm_type %s", storm_type.c_str());
return task_process_status::task_failed;
```

- キーの第 2 トークンが `broadcast` / `unknown-unicast` / `unknown-multicast` 以外
- SET / DEL 両パスで `task_failed` → エントリ erase（リトライなし）
- YANG leafref により通常の CLI 経由では発生しないが、直接 DB 書き込み時は発生しうる

### 4. SAI policer create 失敗

```cpp
// policerorch.cpp:228-235
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create policer %s, rv:%d",
            storm_policer_name.c_str(), status);
    if (handleSaiCreateStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- `sai_policer_api->create_policer()` が SAI_STATUS_SUCCESS 以外を返した場合
- `handleSaiCreateStatus` の判定で `task_need_retry` なら再試行、それ以外はエラーログのみでフォールスルー
- 処理続行（port への attach を試みる）

### 5. SAI set_port_attribute 失敗 (attach) → policer rollback + task_need_retry

```cpp
// policerorch.cpp:292-312
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s, rv:%d", ...);
    if (SAI_STATUS_SUCCESS != sai_policer_api->remove_policer(
                m_syncdPolicers[storm_policer_name]))
    {
        SWSS_LOG_ERROR("Failed to remove policer %s, rv:%d", ...);
    }
    SWSS_LOG_NOTICE("Removed policer %s as set_port_attribute for %s failed", ...);
    m_syncdPolicers.erase(storm_policer_name);
    m_policerRefCounts.erase(storm_policer_name);
    return task_process_status::task_need_retry;
}
```

- `sai_port_api->set_port_attribute()` 失敗時、作成済み policer を rollback 削除してから `task_need_retry`
- rollback の `remove_policer` 自体が失敗した場合もログのみで続行（エラー抑制）

### 6. SAI set_policer_attribute 失敗 (update パス)

```cpp
// policerorch.cpp:259-266
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to update policer %s attribute, rv:%d", ...);
    if (handleSaiSetStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- 既存 policer の CIR 更新失敗
- `handleSaiSetStatus` の判定で `task_need_retry` なら再試行

### 7. SAI remove storm-control 失敗 (update の一時解除ステップ)

```cpp
// policerorch.cpp:279-286
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove storm-control %s from port %s, rv:%d", ...);
    if (handleSaiSetStatus(SAI_API_POLICER, status) == task_need_retry)
    {
        return task_process_status::task_need_retry;
    }
}
```

- update 時の remove-then-reapply の "remove" ステップ失敗
