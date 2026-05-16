# route-orch ordering — Phase B 調査メモ

対象: `docs/reference/config-db/route-orch.md`（FLOW_COUNTER_ROUTE_PATTERN テーブル）

調査日: 2026-05-16

## 1. orchagent 起動時の初期化順序

`orchdaemon.cpp` の `OrchDaemon::init()` における初期化順序（抜粋、行番号は調査時点）:

1. `gFlowCounterRouteOrch = new FlowCounterRouteOrch(...)` — orchdaemon.cpp:253
   - コンストラクタ内で `initRouteFlowCounterCapability()` を即時呼び出し
   - プラットフォームサポート確認 → STATE_DB へ書き込み
   - サポートあり → `FLEX_COUNTER_UPD_TIMER`（1 秒周期）を登録
2. `gRouteOrch = new RouteOrch(...)` — orchdaemon.cpp:337 ← FlowCounterRouteOrch **より後**
3. `m_orchList` の先頭付近: `{ gSwitchOrch, gCrmOrch, gPortsOrch, gBufferOrch, gFlowCounterRouteOrch, ... gRouteOrch ... }` — orchdaemon.cpp:500

**重要**: `gFlowCounterRouteOrch` は `gRouteOrch` より先に生成されるが、`m_orchList` における Select ループ処理では `gRouteOrch` が後ろ（インデックス大）に配置されている。

## 2. CONFIG_DB 変更のハンドラ処理順

`doTask(Consumer &consumer)` — flowcounterrouteorch.cpp:55–97:

- `m_toSync` を **`begin()` から `end()` まで順番に** イテレート（`std::map<>` なので key の辞書順）
- SET → `addRoutePattern()`, DEL → `removeRoutePattern()` を即時実行
- イテレーション中に処理済み entry は `m_toSync.erase(it++)` で削除
- `gRouteOrch` が null の場合は doTask 全体を即時 return（ガード #1）

### コンシューマキーの辞書順処理

orchdaemon.cpp コメント（行 494–498）に明記:

> "For the multiple consumers in Orchs, tasks in a table which name is smaller in lexicographic order are processed first when iterating ConsumerMap."

`FLOW_COUNTER_ROUTE_PATTERN` テーブルのみを購読するため、テーブル間ソートは不要。  
テーブル内のキー（プレフィックス文字列）は `m_toSync`（`std::map`）の辞書順で処理される。

## 3. RoutePattern 内部ソート順

`RoutePattern::operator<`（flowcounterrouteorch.h:28–47）:

```
比較キー: (vrf_name 辞書順, ip_prefix)
```

- VRF 名で第一ソート（デフォルト VRF は空文字列 `""`）
- 同 VRF 内では `IpPrefix::operator<` による IP プレフィックス順

`mRoutePatternSet` は `std::set<RoutePattern>` なので常にソート済み状態を維持する。

## 4. addRoutePattern / removeRoutePattern 処理順

`addRoutePattern()` — flowcounterrouteorch.cpp:224–253:

1. key を parse して `vrf_id`/`ip_prefix`/`vrf_name` を取得
2. `mRoutePatternSet.emplace(...)` → 新規なら `validateRoutePattern()` → `createRouteFlowCounterByPattern()`
3. 既存パターンの更新なら `onRoutePatternMaxMatchCountChange()` を呼ぶ

バインド処理（`bindFlowCounter`）が ASIC_DB VID 未登録で失敗した場合は `mPendingAddToFlexCntr` にキューし、
`FLEX_COUNTER_UPD_TIMER`（1 秒周期の `doTask(SelectableTimer&)`）で再処理する。

## 5. m_orchList 内での FlowCounterRouteOrch の位置とその影響

```
m_orchList 内順序:
  [0] gSwitchOrch
  [1] gCrmOrch
  [2] gPortsOrch
  [3] gBufferOrch
  [4] gFlowCounterRouteOrch   ← ここ
  [5] gIntfsOrch
  ...
  [10] gFgNhgOrch
  [11] gRouteOrch              ← FlowCounterRouteOrch より後
```

Warm Start リストア時の処理順は `m_orchList` の順番に依存するが、
FlowCounterRouteOrch は `gRouteOrch` が null のとき doTask を全スキップするため、
`gRouteOrch` が初期化完了するまで CONFIG_DB パターンは実質的に処理されない。

## 6. evidence

- `orchdaemon.cpp:494–500`: m_orchList とコメント
- `orchdaemon.cpp:250–254`: FlowCounterRouteOrch 生成 (RouteOrch より先)
- `orchdaemon.cpp:337`: RouteOrch 生成
- `flowcounterrouteorch.cpp:55–97`: doTask(Consumer) — m_toSync 辞書順処理
- `flowcounterrouteorch.h:28–47`: RoutePattern::operator< — (vrf_name, ip_prefix) ソート
- `flowcounterrouteorch.cpp:224–253`: addRoutePattern() フロー
- `flowcounterrouteorch.cpp:99–163`: doTask(SelectableTimer) — pending 再試行ループ
