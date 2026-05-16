# app-counter Phase B 順序依存メモ (FLEX_COUNTER_TABLE|FLOW_CNT_TRAP / FLOW_CNT_ROUTE)

対象ページ: `docs/reference/config-db/app-counter.md`

## 1. orchagent 内のオーケストレータ生成順序 (`orchdaemon.cpp`)

| line | 処理 | 備考 |
|------|------|------|
| 253-254 | `gFlowCounterRouteOrch = new FlowCounterRouteOrch(...)` | コンストラクタ内で `initRouteFlowCounterCapability()` 実行 → STATE_DB に capability publish |
| 341 | `gCoppOrch = new CoppOrch(m_applDb, APP_COPP_TABLE_NAME)` | SAI HOSTIF trap object を生成し `m_syncdTrapIds` を構築 |
| 500 | `m_orchList = { ... gFlowCounterRouteOrch, ..., gCoppOrch, ... }` | doTask の実行順 |
| 625 | `new FlexCounterOrch(m_configDb, flex_counter_tables)` | **必ず最後に生成**。doTask 内で `gCoppOrch` / `gFlowCounterRouteOrch` を参照 |

依存グラフ:
```
FlowCounterRouteOrch::ctor → SAI capability query → STATE_DB FLOW_COUNTER_CAPABILITY_TABLE 書込
        ↓
CoppOrch::ctor → SAI HOSTIF trap object 生成 → m_syncdTrapIds 構築
        ↓
FlexCounterOrch::ctor → FLEX_COUNTER_TABLE 購読開始
```

FlexCounterOrch が CoppOrch / FlowCounterRouteOrch よりも前に生成されると `flexcounterorch.cpp:316` の `gCoppOrch->generateHostIfTrapCounterIdList()` と `:324` の `gFlowCounterRouteOrch->getRouteFlowCounterSupported()` が null になる。現状 orchdaemon.cpp ではこの順序が厳密に守られている。

## 2. capability publish が enable 受理より先

`flexcounterorch.cpp:324`:
```cpp
if (gFlowCounterRouteOrch && gFlowCounterRouteOrch->getRouteFlowCounterSupported() && key == FLOW_CNT_ROUTE_KEY)
```

`mRouteFlowCounterSupported` は `FlowCounterRouteOrch::initRouteFlowCounterCapability()` (`flowcounterrouteorch.cpp:166-179`) でのみセットされる。同関数はコンストラクタ内で 1 回だけ呼ばれる (`flowcounterrouteorch.cpp:39`)。再評価には orchagent 再起動が必要。

## 3. POLL 開始のタイミング

`generateRouteFlowStats()` (`flowcounterrouteorch.cpp:181-194`):
```cpp
if (!mRouteFlowCounterSupported) { return; }
for (const auto &route_pattern : mRoutePatternSet) {
    createRouteFlowCounterByPattern(route_pattern, 0);
}
```

`FLOW_COUNTER_ROUTE_PATTERN` と `FLOW_CNT_ROUTE` enable はどちらを先に書いても最終状態は等価。最初の counter が COUNTERS_DB に現れるまで最大 1 秒 (UPD_TIMER) + 10000 ms (POLL_INTERVAL) のラグ。

## 4. FLEX_COUNTER_UPD_INTERVAL (1 秒タイマー)

`flowcounterrouteorch.cpp:21,43-46`: タイマー登録は capability=true のときのみ。capability=false ASIC では `mPendingAddToFlexCntr` に積まれても永遠に flush されない（addRoutePattern 自体が capability ガードで no-op）。

## 5. Warm restart 60 秒遅延 (`FLEX_COUNTER_DELAY_SEC`)

`flexcounterorch.cpp:44, 127-133`: warm restart 時のみ `FLEX_COUNTER_TABLE|FLOW_CNT_*` の SET イベントは 60 秒間 m_toSync にバッファされる。`FlowCounterRouteOrch::doTask` 側に同等の遅延は無い。

## 6. allPortsReady ゲート

`flexcounterorch.cpp:164-172`: `FLEX_COUNTER_TABLE` 処理は全 PORT が SAI に作成完了するまでブロック。`FlowCounterRouteOrch::doTask` 側にはガード無し。

## 7. 順序依存サマリ

| # | 期待順序 | 強制機構 | 違反時の挙動 |
|---|---------|---------|------------|
| 1 | `FlowCounterRouteOrch` 生成 → `FlexCounterOrch` 生成 | `orchdaemon.cpp` 静的順序 | 違反不可（コード固定） |
| 2 | capability publish → `FLOW_CNT_ROUTE` enable 受理 | コンストラクタ内 1 回呼び | 違反不可 |
| 3 | `FLOW_COUNTER_ROUTE_PATTERN` 投入 → `FLOW_CNT_ROUTE` enable | なし | 逆順でも 1 秒以内に同期 |
| 4 | warm restart: 60 秒待機 | `m_delayTimer` | 強制 |
| 5 | port ready → `FLEX_COUNTER_TABLE` 処理 | `allPortsReady` ガード | 強制 |

## 8. evidence 行番号インデックス

- `sonic-swss/orchagent/orchdaemon.cpp:253-254, 341, 500, 625`
- `sonic-swss/orchagent/flexcounterorch.cpp:44, 127-133, 156-159, 164-172, 311-323, 324-336, 380`
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp:21, 39-46, 166-179, 181-194`
- `sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp:51-62`
