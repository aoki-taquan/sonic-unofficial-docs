# STATE_DB VRF テーブル 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/state-vrf.md` Phase D block.

## 調査対象ソース

- `sonic-swss/cfgmgr/vrfmgr.cpp` (L164-370) — VrfMgr::setLink(), VrfMgr::doTask()
- `sonic-swss/orchagent/vrforch.cpp` (L27-198) — VRFOrch::addOperation(), VRFOrch::delOperation()

---

## 失敗パス一覧

### 1. `setLink()` テーブル ID 枯渇 → VRF_TABLE は書かれるが Linux VRF デバイスが存在しない

`vrfmgr.cpp:185-194, 281-289`:

```cpp
uint32_t table = getFreeTable();
if (table == 0)
{
    return false;  // setLink() が false を返す
}
// ...
if (!setLink(vrfName))
{
    SWSS_LOG_ERROR("Failed to create vrf netdev %s", vrfName.c_str());
    // エラーログのみ — 以下の処理は継続
}
m_stateVrfTable.set(vrfName, fvVector);   // VRF_TABLE に state=ok が書かれる
```

`doTask()` は `setLink()` の `false` 戻り値を受けて `SWSS_LOG_ERROR` を記録するが、そのまま次行の `m_stateVrfTable.set()` を実行する。Linux VRF デバイスが存在しない状態で `VRF_TABLE|<name>` に `state=ok` が残る。
`intfmgrd` や `vxlanmgr` はこのエントリを「VRF 存在」と判断し、VRF バインドや VXLAN マッピングを進めてしまう可能性がある。

---

### 2. SAI `create_virtual_router()` 失敗 → VRF_OBJECT_TABLE は書かれない

`vrforch.cpp:93-120`:

```cpp
sai_status_t status = sai_virtual_router_api->create_virtual_router(...);
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_VIRTUAL_ROUTER, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);  // 早期 return
    }
}
// ...
m_stateVrfObjectTable.hset(vrf_name, "state", "ok");  // ここには到達しない
```

`parseHandleSaiStatusFailure()` が `false` を返して `addOperation()` が終了するため、`VRF_OBJECT_TABLE` エントリは書かれない。`vrfmgrd` は削除時に `isVrfObjExist()` でこのテーブルを確認するため、この状態では**VRF 削除がスムーズに完了する**（SAI VR が存在しないため VRF_OBJECT_TABLE も存在せず、削除待機ループが即座に通過する）。

---

### 3. SAI `remove_virtual_router()` 失敗 → VRF_OBJECT_TABLE が削除されない → vrfmgrd がブロック

`vrforch.cpp:173-193`:

```cpp
sai_status_t status = sai_virtual_router_api->remove_virtual_router(router_id);
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_VIRTUAL_ROUTER, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);  // 早期 return
    }
}
// ...
m_stateVrfObjectTable.del(vrf_name);  // ここには到達しない
```

SAI 削除が失敗した場合 `VRF_OBJECT_TABLE|<name>` が残留する。`vrfmgrd` の削除タスクは `isVrfObjExist()` が `true` を返す間、`it++; continue;` でループし続ける (`vrfmgr.cpp:331-335, 342-346`)。結果として、VRF は CONFIG_DB から削除されているにもかかわらず `APP_DB` への DEL 通知と Linux VRF デバイス削除が実行されない状態が持続する。

---

### 4. orchagent クラッシュ → VRF_OBJECT_TABLE の stale エントリが残留

orchagent が `remove_virtual_router()` 成功後・`m_stateVrfObjectTable.del()` 実行前にクラッシュした場合、`VRF_OBJECT_TABLE|<name>` が残留する。これは失敗パス 3 と同じく `vrfmgrd` の削除待機ループを永続的にブロックする。warm start なしの orchagent 再起動により、orchagent は内部マップを再構築して `delOperation()` を再実行するため解消する。

---

### 5. `ref_count` が非ゼロ → VRFOrch が DEL を拒否 → VRF_OBJECT_TABLE が残留

`vrforch.cpp:169-170`:

```cpp
if (vrf_table_[vrf_name].ref_count)
    return false;
```

ルートや Next Hop が VRF を参照している間は `delOperation()` が `false` を返し、`VRF_OBJECT_TABLE` は維持される。この場合も `vrfmgrd` の削除待機ループは継続する。`ref_count` がゼロになった時点で orchagent が次の doTask() 実行時に再試行して自然解消する（正常な設計上の依存）。

---

## 失敗時の STATE_DB 状態まとめ

| 失敗シナリオ | VRF_TABLE 状態 | VRF_OBJECT_TABLE 状態 | vrfmgrd 影響 |
|---|---|---|---|
| setLink() ID 枯渇 | `state=ok` 残存（Linux VRF なし） | 存在しない | intfmgrd/vxlanmgr が誤認識する可能性 |
| SAI create 失敗 | `state=ok`（vrfmgrd は先に書いた） | 存在しない（正常） | 削除ループはブロックされない |
| SAI remove 失敗 | 削除待機中（APP_DB DEL 未実行） | 残留（stale） | 削除待機ループが無限継続 |
| orchagent クラッシュ | 削除待機中 | 残留（stale） | orchagent 再起動で解消 |
| ref_count 非ゼロ | 削除待機中 | 残留（設計上の保留） | ref_count=0 になれば自然解消 |
