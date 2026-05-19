# vrf-orch failure-behavior (Phase D)

調査日: 2026-05-19
ソース: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/cfgmgr/vrfmgr.cpp`

## addOperation 失敗経路

### SAI create_virtual_router 失敗

`vrforch.cpp:93-104`:
```cpp
sai_status_t status = sai_virtual_router_api->create_virtual_router(&router_id, ...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create virtual router name: %s, rv: %d", ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_VIRTUAL_ROUTER, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`parseHandleSaiStatusFailure` の戻り値:
- `task_need_retry` → `false` を返す → Consumer が `m_toSync` に残して次ループで再試行
- `task_failed` → `true` を返す → Consumer がエントリを drop (SAI 永続エラー)

### SAI set_virtual_router_attribute 失敗 (既存 VRF 更新)

`vrforch.cpp:131-140`: 1 属性ずつ `set_virtual_router_attribute` を呼ぶ。失敗した属性のみエラー処理し、後続属性の set は**継続する**。

### updateVrfVNIMap での EVPN VTEP 未設定

`vrforch.cpp:225-230`:
```cpp
auto evpn_vtep_ptr = evpn_orch->getEVPNVtep();
if(!evpn_vtep_ptr)
{
    SWSS_LOG_NOTICE("updateVrfVNIMap unable to find EVPN VTEP");
    return false;
}
```

SAI VR 作成は成功済み（`vrf_table_` / `vrf_id_table_` に登録済み）だが `m_stateVrfObjectTable.hset()` が呼ばれない。
`addOperation` が `false` を返し Consumer 再試行 → EVPN VTEP 到着後の次スケジュールで `updateVrfVNIMap` のみ再実行される。

**中間状態の問題**: SAI VR が作成済みだが STATE_VRF_OBJECT_TABLE がない状態。再試行で `vrf_table_.find(vrf_name) != end` に入るため UPDATE 経路（`set_virtual_router_attribute`）が実行され SAI VR 重複作成は発生しない。

## delOperation 失敗経路

### ref_count 非ゼロによる削除保留

`vrforch.cpp:169-170`:
```cpp
if (vrf_table_[vrf_name].ref_count)
    return false;
```

`false` を返すと Consumer が `m_toSync` にエントリを残す。IntfsOrch / RouteOrch が `decreaseVrfRefCount()` を呼ぶたびに再評価される。ref_count が 0 になるまで削除は無限保留。

### 存在しない VRF の DEL

`vrforch.cpp:163-167`:
```cpp
if (vrf_table_.find(vrf_name) == std::end(vrf_table_))
{
    SWSS_LOG_ERROR("VRF '%s' doesn't exist", vrf_name.c_str());
    return true;  // エラーログだが true で正常扱い → Consumer がエントリを消費
}
```

### SAI remove_virtual_router 失敗

`vrforch.cpp:173-182`: 失敗時は `handleSaiRemoveStatus` → `parseHandleSaiStatusFailure` で再試行または drop を判定。
- `task_need_retry` → `false` → Consumer 再試行（`m_stateVrfObjectTable.del` は呼ばれない → vrfmgrd の `ip link del` も保留継続）
- `task_failed` → `true` → Consumer drop（SAI VR リークが発生しうる）

### delVrfVNIMap での VNI 処理

`vrforch.cpp:249-276`: `delVrfVNIMap` は常に `true` を返す（エラーを無視）。`gPortsOrch->updateL3VniStatus(vlan_id, false)` の戻り値も無視。

## vrfmgrd 側の失敗経路

### VRF テーブルプール枯渇

`vrfmgr.cpp:114-127`: `getFreeTable()` が `0` を返した場合（4096 VRF 使用済み）、`setLink()` が `false` を返す。vrfmgrd は `SWSS_LOG_ERROR("Failed to create vrf netdev %s")` を出すが Consumer エントリは **erase** される（再試行なし）。APPL_DB への書き込みは行われず、VRFOrch への通知も発生しない。

`vrfmgr.cpp:281-284`:
```cpp
if (!setLink(vrfName))
{
    SWSS_LOG_ERROR("Failed to create vrf netdev %s", vrfName.c_str());
}
// エラーでも以下に進む → STATE_VRF_TABLE.set() と APPL_DB.set() が実行される
```

注意: `setLink` 失敗をチェックせず STATE_VRF_TABLE と APPL_DB への書き込みを続行するため、プール枯渇時でも APPL_DB に書かれ VRFOrch が SAI VR 作成を試みる。Linux VRF デバイスは存在しないが SAI VR だけが作成される状態になりうる。

### ip link add / ip link del の EXEC_WITH_ERROR_THROW

`vrfmgr.cpp:192, 198`: `EXEC_WITH_ERROR_THROW` は失敗時に例外を投げる（`std::runtime_error`）。例外は `Orch::doTask()` の外側で捕捉されず、vrfmgrd プロセスがクラッシュする。supervisord が自動再起動する（`autorestart=true` 設定 or critical_processes 経由）。

### doVrfVxlanTableCreateTask: VNI 重複

`vrfmgr.cpp:436-445`:
```cpp
if (vni == itr.second)
{
    SWSS_LOG_ERROR(" vni %d is already mapped to vrf %s", vni, itr.first.c_str());
    return false;
}
```
`false` が返ると `doTask` が Consumer エントリを **erase** する（再試行なし）。ただし `setLink` と `STATE_VRF_TABLE.set()` は既に実行済み。APPL_DB への書き込みは行われず VRF は Linux デバイスのみ存在する中間状態となる。
