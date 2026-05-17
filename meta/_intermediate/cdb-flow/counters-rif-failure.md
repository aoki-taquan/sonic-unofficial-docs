# COUNTERS_DB RIF カウンタ 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/counters-rif.md` Phase D block.

## 調査対象ソース

- `sonic-swss/orchagent/intfsorch.cpp` (sha `4305596156d7`)
- `sonic-swss/orchagent/flexcounterorch.cpp` (sha `4305596156d7`)

スキャン範囲: `IntfsOrch::doTask(Consumer)` L661-1200, `addRouterIntfs()` L1198-1320,
`removeRouterIntfs()` L1323-1370, `addRifToFlexCounter()` L1527-1554,
`removeRifFromFlexCounter()` L1556-1569, `doTask(SelectableTimer)` L1598-1638,
コンストラクタ L60-110, `FlexCounterOrch::doTask()` L150-430

---

## 失敗パス一覧

### 1. SAI `create_router_interface` 失敗 → `throw runtime_error`

`intfsorch.cpp:1297-1305`:

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
```

- `handleSaiCreateStatus` が `task_success` を返す場合（一部の retryable エラー）はそのまま処理を続行し `m_rifsToAdd.push_back(port)` が実行される（RIF OID は 0 のまま）。
- `task_success` 以外の場合は `throw` → orchdaemon 全体がクラッシュしてプロセス再起動する。
- **retry なし・rollback なし**（COUNTERS_DB には何も書かれていない）。

### 2. SAI `remove_router_interface` 失敗 → `throw runtime_error`

`intfsorch.cpp:1350-1357`:

```cpp
sai_status_t status = sai_router_intfs_api->remove_router_interface(port.m_rif_id);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove router interface for port %s, rv:%d", ...);
    if (handleSaiRemoveStatus(SAI_API_ROUTER_INTERFACE, status) != task_success)
    {
        throw runtime_error("Failed to remove router interface.");
    }
}
```

- `removeRifFromFlexCounter()` は SAI 削除の**前**に呼ばれているため、SAI 削除が失敗しても COUNTERS_RIF_NAME_MAP / COUNTERS_RIF_TYPE_MAP から当該 RIF はすでに除去済みになる。SAI と COUNTERS_DB の間に乖離が残る可能性がある。
- `throw` 後は orchdaemon 再起動で収束を期待する設計。

### 3. `ref_count > 0` → DEL ブロック

`intfsorch.cpp:1327-1332`:

```cpp
if (m_syncdIntfses[port.m_alias].ref_count > 0)
{
    SWSS_LOG_NOTICE("Router interface %s is still referenced with ref count %d", ...);
    return false;
}
```

- IP プレフィックスが残っている間は RIF 削除を拒否して `return false`。
- Consumer の `it` は erase されず次回イベント処理でリトライされる（Consumer の通常 retry 機構）。
- COUNTERS_DB は変化しない。

### 4. `allPortsReady()` false → INTERFACE 処理全停止

`intfsorch.cpp:665-668`:

```cpp
if (!gPortsOrch->allPortsReady()) return;
```

- `APP_INTF_TABLE` SET/DEL は Consumer キューに残り、`allPortsReady()` が真になる（PortsOrch 初期化完了）まで処理されない。
- COUNTERS_DB に変化なし。ポートが long-pending のまま残ることがある（起動直後の一時的状態）。

### 5. `rif_rates.lua` ロード失敗 → RATES テーブルが更新されない

コンストラクタ `intfsorch.cpp:86-94`:

```cpp
try {
    string rifRateLuaScript = swss::loadLuaScript(rifRatePluginName);
    rifRateSha = swss::loadRedisScript(m_counter_db.get(), rifRateLuaScript);
} catch (const runtime_error &e) {
    SWSS_LOG_WARN("RIF flex counter group plugins was not set successfully: %s", e.what());
}
```

- 例外をキャッチして `SWSS_LOG_WARN` のみで続行。`rifRateSha` が空文字列のまま `setFlexCounterGroupParameter()` に渡される。
- syncd は Lua プラグインなしで RIF カウンタのポーリングは行うが、`RATES:<oid>` の RX_BPS / TX_BPS 等は**永続的に更新されない**。`intfstat` の rate 列は `N/A` 表示になる。
- orchdaemon の再起動なしには回復しない（ファイルが存在するようになっても再ロードは行われない）。

### 6. `gTraditionalFlexCounter` モードで VIDTORID 未到達 → COUNTERS_DB 登録保留

`intfsorch.cpp:1627-1636`:

```cpp
if (!gTraditionalFlexCounter || m_vidToRidTable->hget("", id, value))
{
    addRifToFlexCounter(id, it->m_alias, type);
    it = m_rifsToAdd.erase(it);
}
else
{
    ++it;  // リストに残して次回タイマーで再試行
}
```

- syncd が `VIDTORID` を書かない限り `m_rifsToAdd` に残り続け、1 秒タイマーのたびにリトライする。
- COUNTERS_RIF_NAME_MAP / FLEX_COUNTER_DB への登録が遅延し、その間 `intfstat` で当該 RIF のカウンタが表示されない。
- syncd がクラッシュ等で `VIDTORID` を書かなかった場合、RIF が永続的に COUNTERS_DB に登録されない（ログには何も出ない — `SWSS_LOG_INFO("Registering %s, id %s", ...)` のみ）。

### 7. `FlexCounterOrch::doTask()` warm-reboot 遅延中は RIF enable が有効にならない

`flexcounterorch.cpp:156-160`:

```cpp
if (!m_delayTimerExpired)
{
    return;
}
```

- warm-reboot 時は最大 60 秒間、`FLEX_COUNTER_TABLE|RIF = enable` を受信しても `generateInterfaceMap()` が呼ばれない。
- 60 秒後に `m_delayTimerExpired = true` になり自動処理が再開されるため、永続的な障害ではない。
- `COUNTERS:<oid>` の更新再開まで最大 60 秒 + SAI ポーリング間隔（1 秒）の遅延がある。

---

## 失敗パス要約表

| 失敗ケース | 検出処理 | ログ | retry/recovery | COUNTERS_DB 影響 |
|-----------|---------|------|----------------|-----------------|
| SAI create_router_interface 失敗 | `addRouterIntfs()` | `SWSS_LOG_ERROR` + throw | orchdaemon 再起動 | 書き込みなし |
| SAI remove_router_interface 失敗 | `removeRouterIntfs()` | `SWSS_LOG_ERROR` + throw | orchdaemon 再起動 | NAME_MAP 削除済み (乖離) |
| ref_count > 0 で DEL | `removeRouterIntfs()` | `SWSS_LOG_NOTICE` | Consumer 次イベントでリトライ | 変化なし |
| allPortsReady false | `doTask(Consumer)` | なし | 起動完了後自動再開 | 変化なし |
| rif_rates.lua ロード失敗 | コンストラクタ | `SWSS_LOG_WARN` | 再起動のみ | RATES 永続的に更新なし |
| VIDTORID 未書込み (traditional mode) | `doTask(SelectableTimer)` | `SWSS_LOG_INFO` のみ | 1 秒タイマー自動リトライ | 登録保留 (永続的な場合あり) |
| warm-reboot 遅延 (60 秒) | `FlexCounterOrch::doTask()` | なし | 60 秒後自動回復 | 最大 60 秒遅延 |
