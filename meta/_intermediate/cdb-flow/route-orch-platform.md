# route-orch platform — Phase H 調査メモ

対象: `docs/reference/config-db/route-orch.md`（FLOW_COUNTER_ROUTE_PATTERN テーブル）

調査日: 2026-05-18

## 1. プラットフォームサポート判定メカニズム

`FlowCounterRouteOrch::initRouteFlowCounterCapability()` — flowcounterrouteorch.cpp:166-179:

- `FlowCounterHandler::queryRouteFlowCounterCapability()` を呼び出す
- 内部で `sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_ROUTE_ENTRY, SAI_ROUTE_ENTRY_ATTR_COUNTER_ID, &capability)` を実行
- status != SAI_STATUS_SUCCESS → `false` を返す（warn ログのみ）
- status == SAI_STATUS_SUCCESS → `capability.set_implemented` の値を返す

## 2. aclorch との違い

- aclorch は `DEVICE_METADATA|localhost.platform` 文字列比較（MRVL_PRST / MRVL_TL / VS 等）でハードコード分岐がある
- `FlowCounterRouteOrch` は**プラットフォーム文字列を一切参照しない**
- 判定は純粋に SAI capability クエリの結果のみ

## 3. STATE_DB 書込み

`mRouteFlowCounterSupported` の値に関わらず必ず書込みが発生する:

```
STATE_DB FLOW_COUNTER_CAPABILITY_TABLE|route
  support = "true" または "false"
```

## 4. 非対応プラットフォームの動作

`mRouteFlowCounterSupported = false` の場合に即 return するメソッド:
- `doTask(Consumer&)` — flowcounterrouteorch.cpp:58-61
- `generateRouteFlowStats()` — flowcounterrouteorch.cpp:184
- `clearRouteFlowStats()` — flowcounterrouteorch.cpp:199
- `onAddMiscRouteEntry()` (両オーバーロード) — flowcounterrouteorch.cpp:310, 322
- `onRemoveMiscRouteEntry()` (両オーバーロード) — flowcounterrouteorch.cpp:356, 368
- `onAddVR()` — flowcounterrouteorch.cpp:405
- `onRemoveVR()` — flowcounterrouteorch.cpp:439

## 5. VS 環境

VS SAI は `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` の set capability を実装していないため `false` になる。
CI テスト環境（VS 使用）では `show flow_counters route` は常に空出力になる。

## 6. evidence

- `flow_counter_handler.cpp:51-62`: `queryRouteFlowCounterCapability()` — SAI クエリのみ
- `flowcounterrouteorch.cpp:166-179`: `initRouteFlowCounterCapability()` — 結果を STATE_DB へ
- `flowcounterrouteorch.cpp:55-61`: `doTask` guard
- `flowcounterrouteorch.cpp:305-366`: `onAdd/RemoveMiscRouteEntry` guards
- `flowcounterrouteorch.cpp:401-451`: `onAdd/RemoveVR` guards
