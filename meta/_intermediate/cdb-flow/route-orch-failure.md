# FLOW_COUNTER_ROUTE_PATTERN — Phase D 失敗挙動スキャンノート

対象テーブル: `FLOW_COUNTER_ROUTE_PATTERN`
Consumer: `FlowCounterRouteOrch::doTask()` (`orchagent/flex_counter/flowcounterrouteorch.cpp`)
スキャン範囲: L55-97 (doTask), L224-253 (addRoutePattern), L574-588 (validateRoutePattern),
             L461-484 (bindFlowCounter), L487-508 (unbindFlowCounter), L166-177 (initRouteFlowCounterCapability)

---

## 重要: task_failed / task_need_retry を使わない設計

`FlowCounterRouteOrch::doTask()` は Orch フレームワーク標準の `task_failed` / `task_need_retry` を**一切使用しない**。
`m_toSync` のイテレート末尾で常に `consumer.m_toSync.erase(it++)` を実行し、
成功・失敗にかかわらずエントリをキューから除去する (L95)。

失敗は `syslog` (SWSS_LOG_ERROR / SWSS_LOG_WARN) に記録されるのみで、CONFIG_DB には残り続ける。
`STATE_DB` / `ERROR_TABLE` への失敗フィードバックはなし。

---

## 失敗パス一覧

### 1. `gRouteOrch == nullptr` または `mRouteFlowCounterSupported == false`

`doTask(Consumer&)` の冒頭ガード (L58-61):

```cpp
if (!gRouteOrch || !mRouteFlowCounterSupported)
{
    return;
}
```

全 `m_toSync` エントリが未処理のまま放置される（erase されない）。
`gRouteOrch` は orchagent 起動後に必ず設定されるため、通常発生しない。
`mRouteFlowCounterSupported == false` はプラットフォーム非対応時に固定される。

- **結果**: CONFIG_DB の変更が全て無視される（エラーログなし）。
- **recovery**: プラットフォーム側のサポート状況は起動後変更不可。

### 2. パターンの IP アドレス解析失敗

`parseRouteKeyForRoutePattern()` (L951-979) で `IpPrefix(key)` / `IpPrefix(key.substr(...))` のコンストラクタが例外を投げる場合（不正な IP プレフィックス文字列）。

- **結果**: 例外がキャッチされずに `orchagent` プロセスが異常終了する可能性がある（防御なし）。
- **対策**: CLI (`config flow_counters route add`) 側で IP プレフィックスの検証を行う。

### 3. VRF / VNET 名が未解決

key に `<vrf_name>|<prefix>` 形式が含まれ、かつ `vrf_name` が VRFOrch または VNetOrch に未登録の場合:

```cpp
// flowcounterrouteorch.cpp:973-975
SWSS_LOG_NOTICE("VRF/VNET name %s is not resolved", vrf_name.c_str());
return false;
```

`parseRouteKeyForRoutePattern()` が `false` を返すため、`addRoutePattern()` 内で `vrf_id = SAI_NULL_OBJECT_ID` として処理が継続される（L232-233）。
VRF_ID が NULL のパターンは **デフォルト VRF のパターンと混同される**可能性がある。

- **結果**: NOTICE ログのみ。パターンは `mRoutePatternSet` に `vrf_id = SAI_NULL_OBJECT_ID` で登録される。
- **retry**: なし（erase される）。

### 4. パターン重複・包含関係による `validateRoutePattern()` 失敗

`addRoutePattern()` → `validateRoutePattern()` が既存パターンとの重複を検出した場合 (L574-588):

```cpp
// flowcounterrouteorch.cpp:582-583
SWSS_LOG_ERROR("Configured route pattern %s is conflict with existing one %s", ...);
return false;
```

`validateRoutePattern()` が `false` を返すと `addRoutePattern()` はセットからイテレータを削除し (`mRoutePatternSet.erase(insert_result.first)`) 即 return する (L239-242)。

- **結果**: ERROR ログのみ。パターンは登録されない。CONFIG_DB エントリは残存。
- **recovery**: 既存パターンを削除してから再登録する必要がある。

### 5. SAI generic counter 作成失敗

`bindFlowCounter()` → `FlowCounterHandler::createGenericCounter()` が失敗した場合 (L461-464):

```cpp
if (!FlowCounterHandler::createGenericCounter(counter_oid))
{
    SWSS_LOG_ERROR("Failed to create generic counter");
    return false;
}
```

- **結果**: ERROR ログのみ。当該ルートへのカウンターバインドをスキップ。次のルートエントリへ継続。

### 6. SAI `set_route_entry_attribute` 失敗（counter bind）

`bindFlowCounter()` → `sai_route_api->set_route_entry_attribute()` がエラーを返した場合 (L475-480):

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    FlowCounterHandler::removeGenericCounter(counter_oid);
    SWSS_LOG_WARN("Failed to bind route entry vrf=%s prefix=%s to flow counter", ...);
    return false;
}
```

作成済みの generic counter は即時クリーンアップされる（leakなし）。

- **結果**: WARN ログのみ。当該ルートのバインドのみ失敗。パターン・他ルートへは影響なし。

### 7. SAI `set_route_entry_attribute` 失敗（counter unbind）

`unbindFlowCounter()` → SAI 失敗 (L501-504):

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Failed to unbind route entry vrf=%s prefix=%s from flow counter", ...);
}
```

WARN ログ後も `FlowCounterHandler::removeGenericCounter(counter_oid)` は必ず呼ばれる (L507)。
SAI 側に counter が残ったまま orchagent 側は解放済みとなる可能性がある。

- **結果**: WARN ログ。SAI と orchagent 内部状態が不整合になる可能性がある。

### 8. DEL 対象パターン不在

`removeRoutePattern(string)` で `mRoutePatternSet` にパターンが存在しない場合 (L270-273):

```cpp
SWSS_LOG_ERROR("Trying to remove route pattern %s, but it does not exist", pattern.c_str());
return;
```

- **結果**: ERROR ログのみ。何も変更されない。

### 9. `max_match_count = 0` のフォールバック

`doTask()` の SET ハンドラで `max_match_count` に `0` が設定された場合 (L81-85):

```cpp
SWSS_LOG_WARN("Max match count for route pattern cannot be 0, set it to default value 30");
maxMatchCount = ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT;
```

- **結果**: WARN ログ。値が `30` にフォールバックして処理継続。

---

## 失敗パス サマリ

| # | トリガー | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | `gRouteOrch = null` / プラットフォーム非対応 | `doTask()` ガード L58-61 | 全エントリが無視（ログなし） | なし |
| 2 | 不正 IP プレフィックス文字列 | `parseRouteKeyForRoutePattern()` | 例外 → orchagent 異常終了の可能性 | なし |
| 3 | VRF/VNET 名が未解決 | `parseRouteKeyForRoutePattern()` L973 | NOTICE ログ。`vrf_id = NULL` で登録継続 | なし |
| 4 | パターン重複・包含 | `validateRoutePattern()` L582 | ERROR ログ。パターン登録拒否 | なし |
| 5 | SAI generic counter 作成失敗 | `bindFlowCounter()` L463 | ERROR ログ。当該ルートスキップ | なし |
| 6 | SAI counter bind 失敗 | `bindFlowCounter()` L477 | WARN ログ。counter クリーンアップ済み | なし |
| 7 | SAI counter unbind 失敗 | `unbindFlowCounter()` L503 | WARN ログ。SAI/orchagent 不整合リスク | なし |
| 8 | DEL 対象パターン不在 | `removeRoutePattern()` L272 | ERROR ログ。no-op | なし |
| 9 | `max_match_count = 0` | `doTask()` SET ハンドラ L83 | WARN ログ。`30` にフォールバック | なし |
