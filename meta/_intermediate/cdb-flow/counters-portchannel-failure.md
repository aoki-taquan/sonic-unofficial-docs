# COUNTERS_DB PortChannel/LAG カウンタ — 障害挙動 (Phase D)

調査日: 2026-05-18
対象ファイル:
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/saihelper.cpp`

---

## 1. addLag() — SAI LAG 作成失敗時

`portsorch.cpp:7994-8003`

```cpp
sai_status_t status = sai_lag_api->create_lag(&lag_id, gSwitchId, ...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create LAG %s lid:%" PRIx64, lag_alias.c_str(), lag_id);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_LAG, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`parseHandleSaiStatusFailure()` (saihelper.cpp:745):
- `task_need_retry` → `false` を返す（再試行）
- `task_failed` → `true` を返す（失敗確定、エントリを破棄）

呼び出し側 `doLagTask()` (portsorch.cpp:6133-6139):
```cpp
if (!addLag(alias, lag_id, switch_id))
{
    it++;   // retry: consumer.m_toSync にエントリを残す
    continue;
}
```
→ `addLag()` が `false` を返した場合（再試行が必要）: エントリを `m_toSync` に残し、次の Select サイクルで再試行。
→ `addLag()` が `true` (= `parseHandleSaiStatusFailure()` = true) を返した場合（失敗確定）: `it++` → `erase(it)` でエントリを消去。COUNTERS_LAG_NAME_MAP への書き込みは行われない。

**要約**: SAI LAG 作成失敗時は **COUNTERS_LAG_NAME_MAP への書き込みが発生しない**。
`show interfaces portchannel` でも LAG が表示されず、`intfstat` は "Interface missing from COUNTERS_LAG_NAME_MAP" にはならず単純に不在になる。

---

## 2. removeLag() — SAI LAG 削除失敗時

`portsorch.cpp:8074-8095`

```cpp
sai_status_t status = sai_lag_api->remove_lag(lag.m_lag_id);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove LAG %s lid:%" PRIx64, ...);
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_LAG, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
// 成功時のみ:
m_counterLagTable->hdel("", lag.m_alias);  // COUNTERS_LAG_NAME_MAP から削除
```

SAI 削除失敗時（`parseHandleSaiStatusFailure()` → true, i.e. `task_failed`）:
- `m_counterLagTable->hdel()` は呼ばれない → **COUNTERS_LAG_NAME_MAP に古いエントリが残る**
- 削除コマンドはエントリを消去済み（consumer.m_toSync から erase）
- これにより LAG は HW 上存在しないが COUNTERS_LAG_NAME_MAP に stale OID が残存する状態になる

`m_port_ref_count > 0` や `m_members.size() > 0` などの前提チェックで `return false` する場合は、
呼び出し元 `doLagTask()` が `it++` → retry へ移行する（SAI を呼ばないため COUNTERS_LAG_NAME_MAP は変化しない）。

---

## 3. create_router_interface() 失敗時（intfsorch）

`intfsorch.cpp:1296-1310`

```cpp
sai_status_t status = sai_router_intfs_api->create_router_interface(&port.m_rif_id, ...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d", ...);
    if (handleSaiCreateStatus(SAI_API_ROUTER_INTERFACE, status) != task_success)
    {
        throw runtime_error("Failed to create router interface.");
    }
}
// 成功時のみ:
m_rifsToAdd.push_back(port);   // FlexCounter 登録キューに追加
```

RIF 作成失敗時: `throw runtime_error` でタスクループが例外終了。
`m_rifsToAdd.push_back()` は呼ばれない → **COUNTERS_RIF_NAME_MAP への書き込みが発生しない**。

---

## 4. addRifToFlexCounter() 内の障害

`intfsorch.cpp:1527-1551`

RIF が `m_rifsToAdd` にキューイングされた後、タイマーループで `m_vidToRidTable->hget()` が失敗する（VID→RID 未確定）場合:
- エントリは `m_rifsToAdd` に残り、次回タイマー（約 1 s）で再試行
- `COUNTERS_RIF_NAME_MAP` への書き込みはまだ発生しない
- `gTraditionalFlexCounter = false` の場合は `hget()` チェックをスキップして即座に `addRifToFlexCounter()` を呼ぶ

`startFlexCounterPolling()` が失敗した場合（インナーレイヤー）: `SWSS_LOG_ERROR` のみ。
`m_rifNameTable->set()` と `m_rifTypeTable->set()` はその前に完了しているため、
COUNTERS_RIF_NAME_MAP 自体は書き込まれるが FlexCounter ポーリングが開始されない状態になる。

---

## 5. 障害パターン一覧

| 障害パターン | COUNTERS_LAG_NAME_MAP | COUNTERS_RIF_NAME_MAP | COUNTERS:<oid> | 回復経路 |
|---|---|---|---|---|
| SAI create_lag 失敗 (need_retry) | 書き込まれない | 書き込まれない（前提未達） | N/A | consumer.m_toSync に残り次サイクル retry |
| SAI create_lag 失敗 (task_failed) | 書き込まれない | 書き込まれない | N/A | エントリ破棄。LAG 再設定が必要 |
| SAI remove_lag 失敗 (task_failed) | **stale OID が残存** | 変化なし | 古い値が残る可能性 | LAG 再設定/SAI リセットが必要 |
| LAG members 残存での remove_lag 試行 | 変化なし | 変化なし | 変化なし | メンバ削除後に自動retry |
| create_router_interface 失敗 | 変化なし | 書き込まれない | N/A | `throw runtime_error` → INTF エントリ再設定が必要 |
| VID→RID 未確定（タイマー待ち） | 変化なし | 書き込まれない（遅延） | N/A | タイマーループで自動回復（約 1 s 周期） |
| allPortsReady() == false | 変化なし | 変化なし | N/A | PortInitDone 後に自動回復 |

---

## 6. 調査証跡

| コード箇所 | 意味 |
|---|---|
| `portsorch.cpp:7994-8003` | addLag() SAI 失敗時の handleSaiCreateStatus |
| `portsorch.cpp:8074-8083` | removeLag() SAI 失敗時の handleSaiRemoveStatus |
| `portsorch.cpp:6133-6139` | doLagTask() での addLag 戻り値処理 (retry/discard) |
| `saihelper.cpp:745-761` | parseHandleSaiStatusFailure() の実装 |
| `intfsorch.cpp:1296-1310` | create_router_interface 失敗時の throw |
| `intfsorch.cpp:1598-1637` | タイマーループでの VID→RID 確認と addRifToFlexCounter 呼び出し |
| `intfsorch.cpp:1527-1551` | addRifToFlexCounter — m_rifNameTable→set() と startFlexCounterPolling |
