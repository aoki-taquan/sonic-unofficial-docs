# appl-vrf failure / retry 調査 (Phase D)

調査日: 2026-05-15
対象ページ: `docs/reference/config-db/appl-vrf.md`
ソース:

- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/saihelper.cpp` (`handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` / `parseHandleSaiStatusFailure`)

## 共通機構

`VRFOrch` は `Orch2` 派生で、`addOperation()` / `delOperation()` の戻り値 `bool` で Consumer の `m_toSync` キュー残置を制御する:

- `return true`  → タスク削除 (retry なし)
- `return false` → `m_toSync` に残し次 `doTask()` で再試行 (上限なし)

SAI 失敗は `handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` で `task_success` / `task_need_retry` / `task_failed` に正規化したのち、`parseHandleSaiStatusFailure(handle_status)` が以下に変換:

| `handle_status` | `parseHandleSaiStatusFailure` 戻り値 | VRFOrch の挙動 |
|---|---|---|
| `task_need_retry` (INSUFFICIENT_RESOURCES / TABLE_FULL / NO_MEMORY / NV_STORAGE_FULL) | `false` | `m_toSync` に残し再試行 |
| `task_failed` (default / handleSaiFailure 経由) | `true` | エントリ削除。`handleSaiFailure()` 内で abort_on_failure=false ながら crash dump 要求 |
| `task_success` | (parseHandleSaiStatusFailure 想定外で WARN + true) | エントリ削除 |

`task_success` のケース (例: `ITEM_ALREADY_EXISTS` を SUCCESS 扱い) では `if (handle_status != task_success)` で分岐前に抜けるため `parseHandleSaiStatusFailure` は呼ばれない。

## addOperation の失敗分岐

### A. `Unknown attribute` (silent skip, retry なし)

`vrforch.cpp:79-83`:

```cpp
else
{
    SWSS_LOG_ERROR("Logic error: Unknown attribute: %s", name.c_str());
    continue;
}
```

未知フィールド (`fallback` を含む) はループを `continue` で抜けるのみで `addOperation` は `return true` に到達。**SAI 書込・STATE_DB 書込は通常通り続行され、未知フィールドはロスト**。retry も発火しない。`fallback` の dead-field 挙動の根因。

### B. `sai_virtual_router_api->create_virtual_router()` 失敗 (新規 VRF パス)

`vrforch.cpp:93-105`:

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

| SAI status | handleSaiCreateStatus | 戻り | VRFOrch 戻り | 結果 |
|---|---|---|---|---|
| `SUCCESS` | `task_success` | (分岐通過) | continue | 正常作成 |
| `ITEM_ALREADY_EXISTS` / `ITEM_NOT_FOUND` / `ADDR_NOT_FOUND` / `OBJECT_IN_USE` | `task_success` (WARN/NOTICE) | (分岐通過) | continue | **router_id が未初期化のまま下流 `vrf_table_[vrf_name].vrf_id = router_id` が走る危険** |
| `INSUFFICIENT_RESOURCES` / `TABLE_FULL` / `NO_MEMORY` / `NV_STORAGE_FULL` | `task_need_retry` | `false` | `return false` | retry |
| その他 (`SAI_STATUS_NOT_SUPPORTED` 等) | `task_failed` (`handleSaiFailure` 経由で crash dump 要求) | `true` | `return true` | エントリ削除・no retry |

注意点: `ITEM_ALREADY_EXISTS` を `task_success` にマップする一般化により、`if (handle_status != task_success)` 分岐を通過してしまうが、**SAI API は router_id を保証しない**。`vrf_table_` への保存が不正値で行われる潜在不具合。VRFOrch 側に明示的 fallback は無い。

### C. `updateVrfVNIMap()` の EVPN VTEP 不在 (silent skip っぽい retry)

`vrforch.cpp:111-118`:

```cpp
if (vni != 0)
{
    error = updateVrfVNIMap(vrf_name, vni);
    if (error == false)
    {
        return false;
    }
}
m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
```

`updateVrfVNIMap` 内 (`vrforch.cpp:225-230`):

```cpp
auto evpn_vtep_ptr = evpn_orch->getEVPNVtep();
if(!evpn_vtep_ptr)
{
    SWSS_LOG_NOTICE("updateVrfVNIMap unable to find EVPN VTEP");
    return false;
}
```

`VXLAN_EVPN_NVO` 未投入で `vni>0` を書くと `updateVrfVNIMap` が `false` → `addOperation` も `false` を返す。`m_toSync` 残置で再試行されるが、**SAI Virtual Router 自体は手前で既に create_virtual_router 成功している**ため、retry のたびに `vrf_table_.find(vrf_name)` がヒットし update パス (D ケース) へ流れる。

- `STATE_VRF_OBJECT_TABLE|<vrfName>` の `state=ok` 書き込みは行われない (この前段で return)
- `vrf_vni_map_table_[vrf_name]` も未設定
- ログは `SWSS_LOG_NOTICE` (INFO/NOTICE) のみで `ERROR` が出ないため、運用上 **silent skip** と認識されがち
- VTEP 投入後の `EvpnNvoOrch` 側からの明示的な再 kick はなく、`doTask()` の再ループに依存

### D. `set_virtual_router_attribute()` 失敗 (既存 VRF 更新パス)

`vrforch.cpp:129-141`:

```cpp
for (const auto& attr: attrs)
{
    sai_status_t status = sai_virtual_router_api->set_virtual_router_attribute(router_id, &attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        task_process_status handle_status = handleSaiSetStatus(SAI_API_VIRTUAL_ROUTER, status);
        if (handle_status != task_success)
        {
            return parseHandleSaiStatusFailure(handle_status);
        }
    }
}
```

各 attribute を**逐次 SAI に set**。途中で `task_need_retry` (resource 系) になると `return false` で `m_toSync` 残置。**ただし `attrs` の前半が SAI に既に書き込まれていても rollback されない** → 部分適用が残る。retry 時は再び loop 先頭から全 attribute を投げ直す (idempotent な属性のみ安全)。

`task_failed` (`NOT_SUPPORTED` 等) は `return true` でエントリ削除・no retry。`l3_mc_action` / `ttl_action` 等の任意属性が未対応 ASIC で `NOT_SUPPORTED` を返した場合は **STATE_DB の `state=ok` を経由しない直前で抜ける** が、`set` 済みの先行属性は残り、`vrf_vni_map_table_` も触らない。

### E. `updateVrfVNIMap()` 失敗 (更新パス末尾)

`vrforch.cpp:143-148`:

```cpp
SWSS_LOG_INFO("VRF '%s' vni %d modify", ...);
error = updateVrfVNIMap(vrf_name, vni);
if (error == false)
{
    return false;
}
```

更新パスでも `EvpnNvoOrch::getEVPNVtep()` 失敗時は `false` で retry 残置 (C と同じ silent skip パターン)。

## delOperation の失敗分岐

### F. `ref_count > 0` (silent retry)

`vrforch.cpp:169-170`:

```cpp
if (vrf_table_[vrf_name].ref_count)
    return false;
```

参照中 VRF の削除要求は `m_toSync` 残置で永久 retry。ERROR/WARN ログ無し → **silent retry**。`ref_count` を 0 まで落とすイベント (`INTERFACE` 削除等) を待ち続ける。

### G. `remove_virtual_router()` 失敗

`vrforch.cpp:173-182`:

```cpp
sai_status_t status = sai_virtual_router_api->remove_virtual_router(router_id);
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_VIRTUAL_ROUTER, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- `OBJECT_IN_USE` → `task_need_retry` → `return false` (retry)
- `ITEM_NOT_FOUND` / `ADDR_NOT_FOUND` → `task_success` (分岐通過し remove 成功扱い → `vrf_table_.erase`)
- default → `task_failed` → `return true` (エントリ削除されるが `vrf_table_` には残置)。**後段 `vrf_table_.erase` を実行せずに抜ける → メモリ上 VRF オブジェクトリーク**

### H. `delVrfVNIMap()` 失敗 (現状常に true)

`delVrfVNIMap` は実装上常に `return true` を返す (`vrforch.cpp:275`)。`delOperation` の `if (error == false) return false;` は dead code。retry には繋がらない。

## STATE_DB / ERROR_TABLE への記録

- 成功時のみ `STATE_VRF_OBJECT_TABLE|<vrfName>` に `state=ok` を書く。失敗時の `state=error` 書込は実装されていない
- `vrfmgrd::isVrfObjExist()` は STATE_VRF_OBJECT_TABLE のキー存在を見るだけで、`state` の値判定はしない (失敗状態の VRF が "存在しない" と扱われる)
- `ERROR_TABLE` への記録は VRFOrch には無い (`appl-acl` / `routeorch` のような明示的失敗チャネルが存在しない)

## 不可逆 / silent 挙動の要約

| 観点 | 観測されるログ | retry | 影響 |
|---|---|---|---|
| 未知フィールド (`fallback` 含む) | `SWSS_LOG_ERROR "Logic error: Unknown attribute"` | なし | 値が黙って失われる |
| `vni>0` + EVPN VTEP 未投入 | `SWSS_LOG_NOTICE` のみ (ERROR 無し) | 永久 retry | SAI Virtual Router は作成済みだが STATE_DB `ok` 未投入。**silent skip** |
| 既存 VRF update 中の SAI 部分失敗 | `SWSS_LOG_ERROR` | resource 系のみ retry | rollback 無し・部分適用残置 |
| `NOT_SUPPORTED` 系 SAI 任意属性 (`l3_mc_action` 等) | `handleSaiFailure` crash dump 要求 | なし | エントリ削除・先行属性は残置 |
| `remove_virtual_router` default 失敗 | `handleSaiFailure` | なし | `vrf_table_` 残置 (内部 map リーク) |
| 削除 `ref_count>0` | 無し | 永久 retry | silent retry |
