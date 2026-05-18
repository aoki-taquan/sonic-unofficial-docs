# route-orch-event 失敗挙動調査 (Phase D)

## 調査対象

- `orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/response_publisher.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/routeorch.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 失敗パターン分類

### A. SAI ルート操作失敗 → APPL_STATE_DB 非更新 + RESPONSE_CHANNEL 通知のみ

`ResponsePublisher::publish()` (`response_publisher.cpp L136-150`) の overload:

```cpp
void ResponsePublisher::publish(..., const ReturnCode &status, bool replace) {
    std::vector<swss::FieldValueTuple> state_attrs;
    if (status.ok()) {
        state_attrs = intent_attrs;  // 成功時のみ state_attrs に値をセット
    }
    publish(table, key, intent_attrs, status, state_attrs, replace);
}
```

内部 publish で DB 書き込み条件:
```cpp
if (m_enable_db_write_and_notify &&
     ((intent_attrs.size() && state_attrs.size()) ||   // SET成功
     (status.ok() && !intent_attrs.size()))) {          // DEL成功
    writeToDB(...);
}
```

- SAI 失敗（SET）時: `state_attrs` が空 → `writeToDB()` が呼ばれない → APPL_STATE_DB 非更新
- RESPONSE_CHANNEL への通知（`err_str = "[SAI] ..."` + `"[OrchAgent] ..."` 等）は成否に関わらず送出される
- evidence: `response_publisher.cpp:126-133`, `response_publisher.cpp:136-150`

### B. SAI エラー直後の publishRouteState — RESPONSE_CHANNEL 通知は送出される

`addRoute()` 内 (routeorch.cpp:L923):

```cpp
publishRouteState(ctx);  // SAI エラー時: RESPONSE_CHANNEL に "[SAI] ..." が通知される
```

`publishRouteState()` は `ReturnCode` のデフォルト引数として `ReturnCode(SAI_STATUS_SUCCESS)` を持つため、
呼び出し側が status を渡さない場合は SUCCESS として処理される可能性に注意。
しかし L923 の呼び出しは `addRoute()` 内で SAI エラー後のパスにある。

実際には `RouteBulkContext.object_statuses` を介して bulk SAI の返却値が渡され、
`addRoutePost()` 内で `*it_status` を確認し失敗時は `return false` → `publishRouteState()` は呼ばれない設計:

```cpp
// addRoutePost(): SAI 失敗なら return false → publishRouteState() は到達しない
if (*it_status++ != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to create route ...");
    return false;
}
// ... 成功経路 ...
publishRouteState(ctx);  // L2729: 成功時のみ到達
```

- evidence: `routeorch.cpp:2462-2476`, `routeorch.cpp:2726-2729`

### C. addRoute() の事前失敗ケース — publishRouteState() が SAI 前に呼ばれる

`doTask()` 内のいくつかのパスでは SAI バルク実行前に `publishRouteState()` を呼ぶ:

| 行番号 | 状況 | 挙動 |
|--------|------|------|
| L923 | loopback インターフェース向けルートを DEL してから publish | 成功扱いで APPL_STATE_DB + RESPONSE_CHANNEL に書く |
| L1050 | 既存エントリと完全一致（再 publish、SAI 操作なし） | 成功扱いで再書き込み |
| L1090 | 重複エントリ追加スキップ | 成功扱いで通知 |

これらのケースでは `ctx.object_statuses` は空のまま `publishRouteState()` に渡るが、
デフォルト引数の `ReturnCode(SAI_STATUS_SUCCESS)` で publish されるため APPL_STATE_DB に書き込まれる。

### D. addRoutePost() false 返却 → retry ループ

`addRoutePost()` が `false` を返すケース（リトライ対象）:

| 条件 | 行番号 | 挙動 |
|------|--------|------|
| `object_statuses` が空（バルク前の早期失敗） | L2388-2392 | return false → m_toSync に残留、次サイクルで再試行 |
| VRF が `m_syncdRoutes` に未登録 | L2396-2401 | return false → リトライ |
| NhgOrch/CbfNhgOrch に NHG 未登録 | L2411-2415 | return false → リトライ |
| 単一 NH の RIF が SAI_NULL_OBJECT_ID | L2431-2436 | return false → リトライ |
| `hasNextHop()` が false | L2440-2445 | return false → リトライ |
| NHG が未登録（一時 NHG にフォールバック） | L2451-2458 | tmp_next_hop で再度 addRoutePost → return false |

これらの場合 `publishRouteState()` は呼ばれず、APPL_STATE_DB は更新されない（エントリは旧値のまま）。
fpmsyncd は経路のプログラミング完了を検知できないため、suppress-fib-pending 使用時は FRR への通知が遅延する。

### E. removeRoutePost() SAI 失敗 → ログのみ、APPL_STATE_DB からは DEL される

`removeRoutePost()` (routeorch.cpp:L2808-) では SAI DEL 失敗時:

```cpp
if (status != SAI_STATUS_SUCCESS) {
    SWSS_LOG_ERROR("Failed to remove route prefix:%s\n", ipPrefix.to_string().c_str());
    task_process_status handle_status = handleSaiRemoveStatus(SAI_API_ROUTE, status);
    if (handle_status != task_success) {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
// ... 成功経路に落ちて publishRouteState() → DEL を APPL_STATE_DB に書く
publishRouteState(ctx);  // L2970
```

SAI DEL 失敗でも `handleSaiRemoveStatus` が `task_success` を返す場合（一部の SAI エラーコード）は
処理が継続し `publishRouteState()` → APPL_STATE_DB からエントリが DEL される。
つまり SAI 上はルートが残っているのに APPL_STATE_DB が削除済みになる矛盾が起きうる。

### まとめ表

| 失敗シナリオ | APPL_STATE_DB | RESPONSE_CHANNEL | orchagent 状態 |
|---|---|---|---|
| SAI ADD 失敗 (`addRoutePost` false) | 更新なし（旧値維持） | 通知なし | 継続・次サイクルでリトライ |
| SAI ADD 失敗 (`*it_status != SUCCESS`) | 更新なし | 通知なし | 継続 |
| VRF 未登録 / NH 未登録 | 更新なし | 通知なし | 継続・リトライ |
| SAI DEL 失敗（task_success 扱い） | エントリが DEL される（矛盾） | DEL 通知送出 | 継続 |
| loopback 除外ルート / 重複スキップ | 成功扱いで書き込み | 成功通知 | 継続 |
