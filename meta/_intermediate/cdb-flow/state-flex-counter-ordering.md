# state-flex-counter — Phase B 書込み順依存 調査ノート

## 調査対象ファイル

- `sonic-sairedis/syncd/FlexCounter.cpp`
- `sonic-sairedis/syncd/FlexCounterManager.cpp`
- `sonic-sairedis/syncd/Syncd.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

## 書込みフロー概要

### 主要経路

```
CONFIG_DB FLEX_COUNTER_TABLE
  └─ FlexCounterOrch::doTask()          (orchagent/flexcounterorch.cpp)
       ├─ FLEX_COUNTER_STATUS=enable 受信
       │    ├─ gPortsOrch->generatePortCounterMap()  →  FLEX_COUNTER_DB FLEX_COUNTER_TABLE に OID リスト書込み
       │    └─ setFlexCounterGroupOperation()          →  FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE に STATUS 書込み
       └─ POLL_INTERVAL 受信
            └─ setFlexCounterGroupPollInterval()       →  FLEX_COUNTER_DB FLEX_COUNTER_GROUP_TABLE に POLL_INTERVAL 書込み

FLEX_COUNTER_DB
  └─ Syncd（メインループ）
       ├─ processFlexCounterGroupEvent()              (Syncd.cpp:3101)
       │    └─ FlexCounterManager::addCounterPlugin() → FlexCounter::addCounterPlugin() → setStatus/setPollInterval
       └─ processFlexCounterEvent()                   (Syncd.cpp:3158)
            └─ FlexCounterManager::addCounter()      → FlexCounter::addCounter()
```

### ポーリング起動 3 条件（FlexCounter.cpp:3538）

```cpp
if (m_enable && !allIdsEmpty() && (m_pollInterval > 0))
```

`m_enable`・ID リスト（`!allIdsEmpty()`）・`m_pollInterval > 0` の 3 つがすべて満たされないとポーリングしない。

## 書込み順依存の発見

### 依存 #1: GROUP_TABLE（enable/interval）→ COUNTER_TABLE（OID リスト）の到着順不定

**発見根拠**: Syncd のメインループ（`Syncd.cpp:5982,5986`）は `m_flexCounter`（FLEX_COUNTER_TABLE）と `m_flexCounterGroup`（FLEX_COUNTER_GROUP_TABLE）を **別の Selectable** として `swss::Select::addSelectable()` で登録する。Redis の通知順序はキューの到着順に依存するため、orchagent が `setFlexCounterGroupOperation()`（FLEX_COUNTER_GROUP_TABLE に STATUS=enable 書込み）より先に `FLEX_COUNTER_TABLE` へ OID リストを書き込んだ場合でも、syncd 側では GROUP_TABLE イベントが先に届く保証はない。

**中間状態**: syncd が OID リスト（FLEX_COUNTER_TABLE SET）を先に受信した場合、`FlexCounter::addCounter()` が呼ばれてカウンタコンテキストは追加されるが、`m_enable = false` なのでポーリングスレッドは起動しない。その後 GROUP_TABLE から `STATUS=enable` が届いて `setStatus(true)` が呼ばれ、3 条件が揃った時点でポーリングが始まる（`FlexCounter.cpp:3088-3092`）。

**逆順の場合**: GROUP_TABLE が先に届いて `m_enable=true` になっても OID リストが空（`allIdsEmpty()=true`）なのでポーリングは起動しない。FLEX_COUNTER_TABLE から OID リストが届いて初めて 3 条件が揃う。

→ **どちらの順序でも最終的にポーリングが起動する**。中間状態は存在するが、機能破綻にはならない。

### 依存 #2: portsorch 初期 POLL_INTERVAL → FlexCounterOrch CONFIG_DB 書込み

**発見根拠**: `portsorch.cpp:87-93` のハードコード定数がコンストラクタ内で FLEX_COUNTER_GROUP_TABLE に書き込まれる（`FlexCounterOrch::createCounterTable()` 経由）。その後 `FlexCounterOrch::doTask()` が CONFIG_DB `FLEX_COUNTER_TABLE` の `POLL_INTERVAL` を受信して `setFlexCounterGroupPollInterval()` で上書きする。

**中間状態**: portsorch 初期化後〜CONFIG_DB の `POLL_INTERVAL` が処理されるまでの間、FLEX_COUNTER_GROUP_TABLE には portsorch のハードコード値が書かれている。`counterpoll show` が参照する CONFIG_DB 値と乖離している可能性がある（Phase A でも言及）。

### 依存 #3: enable 受信時の generatePortCounterMap → OID リスト書込みの原子性

**発見根拠**: `flexcounterorch.cpp:235-244`。`FLEX_COUNTER_STATUS=enable` 受信時に `gPortsOrch->generatePortCounterMap()` を呼んでから `setFlexCounterGroupOperation()` を呼ぶ（複数の Redis write を発行）。这の 2 ステップは単一 orchagent event ループイテレーション内で実行されるが、Redis への書込みはパイプライン経由で非同期になる。syncd 視点では GROUP SET と COUNTER_TABLE SET が別イベントとして到達する（依存 #1 を参照）。

### 依存 #4: allPortsReady() ガードと OID リスト生成

**発見根拠**: `flexcounterorch.cpp` が `gPortsOrch` ポインタを使用する際、`gPortsOrch` が null でないことは確認するが、PortsOrch 内部で `allPortsReady()` が false の間は `generatePortCounterMap()` がポートリストを走査して空リストを生成する可能性がある。`portsorch.cpp` では `addFlexCounters()` 系関数内で `m_port_counter_enabled` フラグを参照してスキップする実装になっており、新たなポートが `initPort()` で追加されるたびに ID リストへ追記される（`portsorch.cpp:generatePortCounterMap` の append 動作）。

→ **起動直後**: GROUP_TABLE STATUS=enable が書かれ `m_port_counter_enabled=true` になっていても、portsorch がまだポートを初期化していない段階では FLEX_COUNTER_TABLE に Ethernet0 の OID が書かれていない。ポートが追加されるたびに OID リストが逐次追加されていくことで、ポーリング対象が増加する。

## まとめ（Phase B 書込みシーケンス）

| # | 依存関係 | 方向 | 中間状態 | 緩和策 |
|---|----------|------|---------|--------|
| 1 | GROUP_TABLE STATUS=enable / COUNTER_TABLE OID リスト 到着順不定 | Redis queueing | `m_enable=true` + OID 空、または OID あり + `m_enable=false` | 3 条件揃い次第ポーリング起動（自動解消） |
| 2 | portsorch ハードコード POLL_INTERVAL → CONFIG_DB 上書き | init → doTask | CONFIG_DB 値反映前は初期値で動作 | counterpoll で再設定で即上書き可能 |
| 3 | enable 受信 → generatePortCounterMap → setFlexCounterGroupOperation の 2 ステップ | 単一 doTask イテレーション内 | syncd では GROUP SET と COUNTER_TABLE SET が別イベント到達 | 依存 #1 と同様、最終的に収束 |
| 4 | gPortsOrch 初期化完了 → OID 逐次追加 | 起動シーケンス | 起動直後は FLEX_COUNTER_TABLE が空 → ポーリング無効 | portsorch が `initPort()` ごとに OID 追記、最終的にすべてのポートが追加 |
