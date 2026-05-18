# route-cache failure phase (Phase D)

## 調査対象

- `sonic-swss/orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/response_publisher.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/fpmsyncd/routesync.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 失敗パスの概要

APPL_STATE_DB `ROUTE_TABLE` への書き込みは `publishRouteState()` → `ResponsePublisher::publish()` 経由で行われる。
SAI 操作の成否によって APPL_STATE_DB への書き込みが制御される。

## SET 操作の失敗パス

### 1. SAI create_route_entry 失敗

`addRoutePost()` (routeorch.cpp:2509-2527) で SAI `create_route_entry` が失敗した場合:

```cpp
sai_status_t status = *it_status++;
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

`addRoutePost()` は `false` を返す → `doTask()` の `addRoute(ctx, nhg)` 呼び出し側が `it++` でイベントを m_toSync に残す。
`publishRouteState()` は呼ばれず **APPL_STATE_DB への書き込みなし**。

### 2. SAI set_route_entry_attribute 失敗（UPDATE パス）

`addRoutePost()` (routeorch.cpp:2572-2589) で SAI `set_route_entry_attribute` が失敗した場合も同様。
`false` を返し、イベントは m_toSync に残り、`publishRouteState()` は呼ばれない。

### 3. SAI_STATUS_ITEM_NOT_FOUND の特殊処理

```cpp
// routeorch.cpp:2575-2581
if (status == SAI_STATUS_ITEM_NOT_FOUND)
{
    // orchagent 内部キャッシュにエントリはあるが SAI には存在しない状態
    m_syncdRoutes.at(vrf_id).erase(ipPrefix);
    return false;
}
```

SAI が `ITEM_NOT_FOUND` を返した場合は内部キャッシュをクリアして `false` を返す（再試行）。
`publishRouteState()` は呼ばれず APPL_STATE_DB への書き込みなし。

### 4. ResponsePublisher の SET 失敗ガード

`publishRouteState()` が呼ばれた場合でも、SAI 失敗時は APPL_STATE_DB への書き込みがスキップされる:

```cpp
// response_publisher.cpp:129-133
if (m_enable_db_write_and_notify &&
     ((intent_attrs.size() && state_attrs.size()) ||
     (status.ok() && !intent_attrs.size()))) {
        writeToDB(table, key, state_attrs, ...);
}
```

SET 操作（`intent_attrs.size() > 0`）かつ SAI 失敗（`status.ok()` が false）の場合:
- `state_attrs` が空（`response_publisher.cpp:144-147`: SAI 失敗時は `state_attrs = intent_attrs` が実行されない）
- 条件 `intent_attrs.size() && state_attrs.size()` が false → `writeToDB` スキップ

通知チャネルへは失敗情報が送信される:
```
err_str = "[SAI] " + status.message()
```

### 5. バリデーションエラーによるスキップ

`doTask()` でのバリデーション失敗（フォーマットエラー等）:

```cpp
// routeorch.cpp:982-991
SWSS_LOG_ERROR("Skip route %s, it has an invalid router mac field %s", key.c_str(), remote_macs.c_str());
it = consumer.m_toSync.erase(it);
continue;
```

バリデーション失敗のイベントはエラーログを出力しつつ **消費（erase）** される。
`publishRouteState()` は呼ばれず APPL_STATE_DB への書き込みなし（通知チャネルへも送信なし）。

## DEL 操作の失敗パス

### 6. SAI remove_route_entry 失敗

`removeRoutePost()` (routeorch.cpp:2874):

```cpp
SWSS_LOG_ERROR("Failed to remove route prefix:%s\n", ipPrefix.to_string().c_str());
```

SAI 削除失敗後も `publishRouteState()` が呼ばれる（routeorch.cpp:2970）:

```cpp
/* Publish removal status, removes route entry from APPL STATE DB */
publishRouteState(ctx);
```

DEL 操作では `fvs` が空配列のため、ResponsePublisher は APPL_STATE_DB のエントリを削除しようとする。
ただし SAI 失敗時は `status.ok()` が false で `intent_attrs.size()` が 0 のため:
- 条件 `status.ok() && !intent_attrs.size()` が false → `writeToDB` スキップ
- APPL_STATE_DB のエントリは削除されない
- 通知チャネルへは失敗情報 `err_str=[SAI]...` が送信される

## fpmsyncd の失敗受け取り

`fpmsyncd` は RESPONSE_CHANNEL で失敗通知を受け取った場合:

```cpp
// routesync.cpp:3195-3206
if (field == "err_str")
    isSuccessReply = (value == "SWSS_RC_SUCCESS");
```

`err_str != "SWSS_RC_SUCCESS"` の場合 `isSuccessReply = false` となり、offload 通知はスキップされる。

## 失敗パスまとめ

| 失敗シナリオ | APPL_STATE_DB | 通知チャネル | イベント消費 |
|---|---|---|---|
| SAI create 失敗 (task_need_retry) | 書き込みなし | 送信なし | m_toSync に残留（リトライ） |
| SAI create 失敗 (task_success) | 書き込みなし | 送信なし | erase（消費） |
| SAI set 失敗 | 書き込みなし | 送信なし | m_toSync に残留（リトライ） |
| SAI ITEM_NOT_FOUND | 書き込みなし | 送信なし | m_toSync に残留（リトライ） |
| バリデーション失敗 | 書き込みなし | 送信なし | erase（消費・ドロップ） |
| SAI remove 失敗 | 削除なし | `err_str=[SAI]...` 送信 | `publishRouteState()` 後 erase |
| SAI 失敗時の ResponsePublisher | 書き込みスキップ | `err_str` 送信 | — |

## ソース参照

- `routeorch.cpp:2509-2527` — SAI create 失敗パス
- `routeorch.cpp:2572-2589` — SAI set 失敗パス
- `routeorch.cpp:2575-2581` — ITEM_NOT_FOUND 特殊処理
- `routeorch.cpp:2870-2874` — SAI remove 失敗パス
- `routeorch.cpp:2970` — DEL 後の publishRouteState 呼び出し
- `response_publisher.cpp:129-133` — writeToDB 条件ガード
- `response_publisher.cpp:143-148` — SAI 失敗時の state_attrs 空配列
- `routesync.cpp:3195-3206` — fpmsyncd の err_str チェック
