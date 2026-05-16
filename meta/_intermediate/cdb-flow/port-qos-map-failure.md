# PORT_QOS_MAP — Phase D: 失敗挙動 (failure)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 調査対象メソッド

- `QosOrch::handlePortQosMapTable` (ポートエントリ SET/DEL)
- `QosOrch::handleGlobalQosMap` (`PORT_QOS_MAP|global` SET/DEL)

---

## 1. 未解決 MAP → task_need_retry

### ポートエントリ (SET)

`handlePortQosMapTable` の SET 処理で、`dscp_to_tc_map` / `tc_to_queue_map` 等の leafref が指す QoS map オブジェクトがまだ SAI に登録されていない場合:

```cpp
// qosorch.cpp ~2129
ref_resolve_status status = resolveFieldRefValue(...);
if (status != ref_resolve_status::success)
{
    SWSS_LOG_INFO("Port QoS map %s is not yet created", map_name.c_str());
    return task_process_status::task_need_retry;
}
```

- `resolveFieldRefValue` が `success` 以外を返した時点で **即 `task_need_retry` を返す**。後続フィールドは評価しない。
- 対応する QoS map エントリが Consumer キューに届き処理されると、自動再実行される。

### global エントリ (SET)

`handleGlobalQosMap` でも同様。`dscp_to_tc_map` の解決失敗時:

```cpp
// qosorch.cpp ~2026
if (status != ref_resolve_status::success)
{
    SWSS_LOG_INFO("Global QoS map %s is not yet created", map_name.c_str());
    task_status = task_process_status::task_need_retry;
    continue;
}
```

- ポートエントリと異なり `continue` で他フィールドへ進む（global は `dscp_to_tc_map` 以外は `SWSS_LOG_WARN` でスキップするため実質的差異は小さい）。

---

## 2. PORT 不在 → continue (ログのみ、retry なし)

```cpp
// qosorch.cpp ~2068, ~2180
if (!gPortsOrch->getPort(port_name, port))
{
    SWSS_LOG_ERROR("Failed to apply QoS maps to port %s. Port is not found.", port_name.c_str());
    continue;
}
```

- **DEL 処理**: ポートが見つからない場合は `continue` でそのポートをスキップし、処理自体は `task_success` で終了。
- **SET 処理**: 同様に `continue` でスキップ。`task_need_retry` は返さない点が MAP 未解決と異なる。
- 複数ポート名が key に含まれる場合（カンマ区切り）、見つからないポートのみスキップし残りには適用する。

---

## 3. SAI bind 失敗 → task_invalid_entry (SET/DEL 共通)

### SET: sai_port_api->set_port_attribute 失敗

```cpp
// qosorch.cpp ~2196
sai_status_t status = sai_port_api->set_port_attribute(port.m_port_id, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to apply %s to port %s, rv:%d",
                   it->second.first.c_str(), port_name.c_str(), status);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_PORT, status);
    if (handle_status != task_process_status::task_success)
    {
        return task_process_status::task_invalid_entry;
    }
}
```

- `handleSaiSetStatus` が `task_success` 以外なら **`task_invalid_entry` を返す**。
- エントリ全体が無効扱いとなりキューから除去される（retry なし）。

### DEL: sai_port_api->set_port_attribute 失敗

```cpp
// qosorch.cpp ~2089
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove %s on port %s, rv:%d", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_PORT, status);
    if (handle_status != task_process_status::task_success)
    {
        return task_process_status::task_invalid_entry;
    }
}
```

- DEL も同様に `task_invalid_entry`。

### PFC ビット失敗

```cpp
// qosorch.cpp ~2217
if (!gPortsOrch->setPortPfc(port.m_port_id, pfc_enable))
{
    SWSS_LOG_ERROR("Failed to apply PFC bits 0x%x to port %s", pfc_enable, port_name.c_str());
}
```

- PFC ビット設定失敗は **ログのみ**。`task_*` 返却なし（処理は `task_success` で継続）。

---

## 4. global vs port 失敗差異

| シナリオ | global (`PORT_QOS_MAP|global`) | port (`PORT_QOS_MAP|<port>`) |
|----------|-------------------------------|------------------------------|
| MAP 未解決 | `task_need_retry` (continue で他フィールド評価継続) | `task_need_retry` (即 return、後続フィールド未評価) |
| PORT 不在 | 該当なし (global は port lookup しない) | `continue` でスキップ、`task_success` |
| SAI bind 失敗 | `task_failed` (`applyDscpToTcMapToSwitch` が `false` 時) | `task_invalid_entry` (`handleSaiSetStatus` 経由) |
| 非対応 map type | `SWSS_LOG_WARN` + `continue` (無視) | N/A (map type は `qos_to_attr_map` に基づくため不一致フィールドは単にスキップ) |
| DEL 時 SAI 失敗 | `task_failed` (`applyDscpToTcMapToSwitch` が `false` 時) | `task_invalid_entry` |

### global 固有: dscp_to_tc_map 以外フィールドは常時無視

```cpp
// qosorch.cpp ~2013
SWSS_LOG_WARN("Qos map type %s is not supported at global level", map_type_name.c_str());
```

- `PORT_QOS_MAP|global` に `tc_to_queue_map` 等を設定しても警告ログのみで適用されない。

---

## 5. 証跡まとめ

| 障害種別 | 返却ステータス | ログレベル | ソース行 (approx) |
|---------|--------------|-----------|------------------|
| MAP 未解決 (port SET) | `task_need_retry` | INFO | `qosorch.cpp:~2129` |
| MAP 未解決 (global SET) | `task_need_retry` | INFO | `qosorch.cpp:~2026` |
| PORT 不在 (port SET/DEL) | なし (continue) | ERROR | `qosorch.cpp:~2068, ~2180` |
| SAI bind 失敗 (port) | `task_invalid_entry` | ERROR | `qosorch.cpp:~2196-2201` |
| SAI DEL 失敗 (port) | `task_invalid_entry` | ERROR | `qosorch.cpp:~2089-2094` |
| SAI bind 失敗 (global) | `task_failed` | INFO/WARN | `qosorch.cpp:~2038-2039, ~2001-2002` |
| PFC ビット設定失敗 | なし (ログのみ) | ERROR | `qosorch.cpp:~2217` |
| PFC bits 取得失敗 | なし (ログのみ) | ERROR | `qosorch.cpp:~2210` |
