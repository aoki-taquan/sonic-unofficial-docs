# ROUTE_TABLE (STATE_DB / APPL_STATE_DB) — Phase D 失敗挙動スキャンノート

対象テーブル: `STATE_DB ROUTE_TABLE` / `APPL_STATE_DB ROUTE_TABLE`
Consumer: `orchagent RouteOrch` (`sonic-swss/orchagent/routeorch.cpp`)
スキャン範囲: L440-441 (SAI create fail → parseHandleSaiStatusFailure), L2472-2526 (addRoutePost create fail), L2562-2588 (addRoutePost set fail), L2729 (publishRouteState ADD), L2833-2856 (removeRoutePost set fail), L2970 (publishRouteState DEL), L3185-3202 (publishRouteState impl)

---

## STATE_DB `ROUTE_TABLE` — 失敗挙動

### SAI create_route_entry 失敗 → STATE_DB 未更新

`addRoutePost()` (`routeorch.cpp:2472-2526`) でバルク SAI 応答が失敗の場合:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create route %s with next hop(s) %s", ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- `updateDefRouteState()` は `addRoutePost()` の成功パスにのみ存在する (`routeorch.cpp:2700-2703`)
- SAI 失敗時は `updateDefRouteState()` が呼ばれず STATE_DB は古い値（通常 `state=na`）のまま
- `return false` → エントリが `m_toSync` に残り次の `doTask()` サイクルでリトライ

### SAI set_route_entry 失敗 (DEL パス) → STATE_DB 未更新

`removeRoutePost()` (`routeorch.cpp:2833-2856`) でデフォルト経路の packet_action=DROP 設定失敗:

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set route %s packet action to drop, rv:%d", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
// ... SAI 成功後にのみ:
updateDefRouteState(ipPrefix.to_string());  // state=na
```

- DEL 失敗時は `state=na` に更新されず `state=ok` が残る
- リトライで SAI 操作が成功するまで STATE_DB は古い状態

---

## APPL_STATE_DB `ROUTE_TABLE` — 失敗挙動

### SAI 失敗でも err_str が書き込まれる

`publishRouteState()` は SAI 操作の成否に関わらず呼ばれる。失敗時は `status` に SAI エラーコードが入り、`ResponsePublisher::publish()` が自動的に `err_str=[SAI] <エラーメッセージ>` を書き込む:

```cpp
// addRoutePost: routeorch.cpp:2729
publishRouteState(ctx);  // SAI 成功後に呼ばれる (通常パス)

// 例外パス: routeorch.cpp:923 (loopback インタフェース向け経路)
publishRouteState(ctx);  // SAI 呼ばず直接 publish

// 例外パス: routeorch.cpp:1050, 1090 (重複 SET / fullmask subnet)
publishRouteState(ctx);  // SAI 呼ばず直接 publish
```

**注意**: 通常の SAI 失敗パス（`return false` → リトライ）では `publishRouteState()` は呼ばれない。つまり:
- SAI 成功 → APPL_STATE_DB に `protocol` + `err_str=SWSS_RC_SUCCESS` が書き込まれる
- SAI 失敗 → `return false` → APPL_STATE_DB は書き込まれない（前回のエントリが残る）
- 特殊パス (loopback / duplicate) → SAI なしで APPL_STATE_DB に書き込まれる

---

## parseHandleSaiStatusFailure の挙動

```cpp
bool RouteOrch::parseHandleSaiStatusFailure(task_process_status handle_status)
{
    switch (handle_status)
    {
        case task_need_retry:    return false;   // m_toSync に残してリトライ
        case task_failed:        return true;    // エントリを破棄（もうリトライしない）
        default:                 return false;
    }
}
```

| SAI エラー種別 | handle_status | 結果 |
|--------------|--------------|------|
| 一時的なリソース不足等 | `task_need_retry` | `return false` → 次サイクルでリトライ |
| 恒久的なエラー | `task_failed` | `return true` → エントリ破棄 |

---

## 失敗挙動サマリ

| DB / テーブル | 失敗シナリオ | STATE_DB の結果 | APPL_STATE_DB の結果 |
|-------------|------------|----------------|---------------------|
| STATE_DB `ROUTE_TABLE` | SAI create 失敗 | `state` 更新されず（古い値残留） | — |
| STATE_DB `ROUTE_TABLE` | SAI set(DEL) 失敗 | `state=ok` のまま残留 | — |
| APPL_STATE_DB `ROUTE_TABLE` | SAI create 失敗 → return false | 書き込まれない（前エントリ残留） | — |
| APPL_STATE_DB `ROUTE_TABLE` | SAI 成功後 publish | — | `err_str=SWSS_RC_SUCCESS` + `protocol` |
| APPL_STATE_DB `ROUTE_TABLE` | 特殊パス (loopback 等) | — | SAI なしで `err_str` 書き込み |
