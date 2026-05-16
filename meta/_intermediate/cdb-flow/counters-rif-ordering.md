# COUNTERS_DB RIF カウンタ — Phase B 処理順序スキャンノート

対象テーブル: `COUNTERS_DB / COUNTERS_RIF_NAME_MAP`, `COUNTERS_RIF_TYPE_MAP`, `COUNTERS:<oid>`, `RATES:<oid>`
Consumer/Writer: `IntfsOrch` (`sonic-swss/orchagent/intfsorch.cpp`), `FlexCounterOrch` (`orchagent/flexcounterorch.cpp`), `syncd` FlexCounter
スキャン範囲: `intfsorch.cpp` 全行, `flexcounterorch.cpp` doTask, `orchdaemon.cpp` 初期化シーケンス

---

## 検出した順序依存・タイミング依存

### 1. orchdaemon 初期化順序 — IntfsOrch は VRFOrch の後・FlexCounterOrch の前

`orchdaemon.cpp` の初期化順序:

```
L232: gPortsOrch = new PortsOrch(...)
L283: VRFOrch *vrf_orch = new VRFOrch(...)
L296: gIntfsOrch = new IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, vrf_orch, ...)
L298: gNeighOrch = new NeighOrch(...)
...
L625: FlexCounterOrch *flexCounterOrch = new FlexCounterOrch(m_configDb, flex_counter_tables)
```

**順序依存**:
- `IntfsOrch` は `gPortsOrch` (PortsOrch) と `vrf_orch` (VRFOrch) の **両方が初期化済み** であることを前提にする。
- `FlexCounterOrch` は `IntfsOrch` より後に生成される。`FLEX_COUNTER_TABLE|RIF` の `enable` 処理は `gIntfsOrch != nullptr` を前提とするため (`flexcounterorch.cpp:283`)、IntfsOrch 初期化前に enable 信号が来ても `generateInterfaceMap()` は呼ばれない。
- evidence: `orchdaemon.cpp` L232, L283, L296, L625

### 2. doTask PortsOrch ガード — 全ポート Ready 前は INTERFACE 処理なし

`IntfsOrch::doTask(Consumer)` の先頭 (intfsorch.cpp:665-668):

```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```

**順序依存**: `APP_INTF_TABLE` の `SET` メッセージを受信しても、`PortsOrch` の全ポート初期化 (`allPortsReady()`) が完了するまで一切処理しない。これにより:

- `INTERFACE` テーブルのエントリより前に対応する物理ポート (`Ethernet0`, `PortChannel0001`, `Vlan1000` 等) が PortsOrch に登録されている必要がある。
- `APP_INTF_TABLE` の通知は Consumer キューに積まれ、PortsOrch の準備完了後に初めて処理される。

### 3. RIF 作成 → m_rifsToAdd キューイング — タイマー駆動の非同期登録

`addRouterIntfs()` (intfsorch.cpp:1296-1311) で SAI RIF を作成後、`port` を `m_rifsToAdd` リストに追加するのみで FlexCounter 登録は行わない:

```cpp
gPortsOrch->setPort(port.m_alias, port);
m_rifsToAdd.push_back(port);
```

実際の FlexCounter 登録は `doTask(SelectableTimer &timer)` で行われる。このタイマーは `UPDATE_MAPS_SEC = 1` 秒間隔 (intfsorch.cpp:45, L78)。

**順序依存**:
1. `doTask(Consumer)` → `setIntf()` → `addRouterIntfs()` → RIF 生成 → `m_rifsToAdd` 追加
2. 最大 1 秒後: `doTask(SelectableTimer)` → `addRifToFlexCounter()` → COUNTERS_DB マップ + FLEX_COUNTER_DB 更新

この 1 秒の遅延の間、`COUNTERS_RIF_NAME_MAP` および `COUNTERS_RIF_TYPE_MAP` にエントリが **存在しない**。`intfstat` を即座に実行すると当該 RIF のカウンタが表示されない場合がある。

### 4. gTraditionalFlexCounter — ASIC_DB VID-to-RID 待機

`doTask(SelectableTimer)` (intfsorch.cpp:1629-1636):

```cpp
if (!gTraditionalFlexCounter || m_vidToRidTable->hget("", id, value))
{
    addRifToFlexCounter(id, it->m_alias, type);
    it = m_rifsToAdd.erase(it);
}
```

`gTraditionalFlexCounter = true` の場合、ASIC_DB の `VIDTORID` テーブルに該当 OID が存在する (`hget` が true を返す) まで `addRifToFlexCounter()` を呼ばない。新規 FlexCounter モード (`gTraditionalFlexCounter = false`) では即座に登録する。

**順序依存**: Traditional モードでは `syncd` が ASIC_DB の `VIDTORID` にエントリを書く (`syncd_main` の SAI create 応答処理) より前に `addRifToFlexCounter()` は呼ばれない。

### 5. FLEX_COUNTER_TABLE|RIF enable → generateInterfaceMap() の連鎖

`FlexCounterOrch::doTask()` (flexcounterorch.cpp:283-285):

```cpp
if(gIntfsOrch && (key == RIF_KEY) && (value == "enable"))
{
    gIntfsOrch->generateInterfaceMap();
}
```

`generateInterfaceMap()` (intfsorch.cpp:1576-1578):

```cpp
void IntfsOrch::generateInterfaceMap()
{
    m_updateMapsTimer->start();
}
```

**順序依存**:
- `FLEX_COUNTER_TABLE|RIF` に `FLEX_COUNTER_STATUS = enable` が書かれると、`FlexCounterOrch` → `IntfsOrch::generateInterfaceMap()` → タイマーキック → `doTask(SelectableTimer)` の経路で既存 RIF 全件が FlexCounter に登録される。
- すでに `m_rifsToAdd` に積まれた RIF は次のタイマー発火で一括登録される。
- `FlexCounterOrch` が初期化される前 (orchdaemon 起動直後) に `FLEX_COUNTER_TABLE|RIF` の enable 変化が来ても、`FlexCounterOrch::m_delayTimerExpired` が false の場合は early return し処理しない (flexcounterorch.cpp:157-160)。

### 6. addRifToFlexCounter() — COUNTERS_DB 書き込み順序

`addRifToFlexCounter()` (intfsorch.cpp:1527-1552) の書き込み順:

1. `COUNTERS_RIF_NAME_MAP` に `name → OID` を hset
2. `COUNTERS_RIF_TYPE_MAP` に `OID → type` を hset
3. `FLEX_COUNTER_DB` の `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<OID>` に `COUNTER_ID_LIST` を set → syncd が SAI ポーリングを開始

`COUNTERS:<oid>` は syncd が SAI から受信した値を書き込む（IntfsOrch は直接書かない）。

### 7. 削除時の順序依存

`removeIntf()` → `removeRouterIntfs()` → `removeRifFromFlexCounter()`:

- `removeRifFromFlexCounter()` は `COUNTERS_RIF_NAME_MAP` と `COUNTERS_RIF_TYPE_MAP` の当該エントリを hdel し、`FLEX_COUNTER_DB` の COUNTER_ID_LIST を stopFlexCounterPolling() で削除する。
- `COUNTERS:<oid>` は syncd 側でクリーンアップされる（IntfsOrch は直接削除しない）。
- `m_rifsToAdd` にまだキューイングされている RIF (addRifToFlexCounter 未実行) は `removeRouterIntfs()` 内でリストから除去されるだけで FlexCounter 登録のクリーンアップは不要 (intfsorch.cpp:1337-1344)。

---

## まとめ: RIF カウンタ登録の全体シーケンス

```
[CONFIG_DB INTERFACE SET]
      ↓ (APP_DB 変換は intfmgrd 経由)
[APP_INTF_TABLE SET]
      ↓ IntfsOrch::doTask(Consumer) — PortsOrch.allPortsReady() true 必須
[addRouterIntfs(): SAI RIF 作成 → m_rifsToAdd キュー追加]
      ↓ 最大 1 秒 (UPDATE_MAPS_SEC タイマー)
[doTask(SelectableTimer): addRifToFlexCounter()]
      ↓ 同期書き込み
[COUNTERS_RIF_NAME_MAP, COUNTERS_RIF_TYPE_MAP] (COUNTERS_DB)
[FLEX_COUNTER_DB: COUNTER_ID_LIST 登録]
      ↓ syncd FlexCounter ポーリング (FLEX_COUNTER_TABLE|RIF enable 必須)
[COUNTERS:<oid>] (COUNTERS_DB) ← syncd が SAI poll
[RATES:<oid>]   (COUNTERS_DB) ← rif_rates.lua Lua プラグイン
```

---

## 証跡一覧

| 事実 | ファイル:行 |
|------|-----------|
| `IntfsOrch` 優先度 35 | `intfsorch.cpp:43` |
| `UPDATE_MAPS_SEC = 1` 秒 | `intfsorch.cpp:45` |
| PortsOrch ガード | `intfsorch.cpp:665-668` |
| RIF 作成後 `m_rifsToAdd` キューイング | `intfsorch.cpp:1311` |
| タイマー駆動 `addRifToFlexCounter` | `intfsorch.cpp:1598-1638` |
| `gTraditionalFlexCounter` VID-to-RID 待機 | `intfsorch.cpp:1629-1636` |
| `addRifToFlexCounter` 書き込み順序 | `intfsorch.cpp:1527-1552` |
| `FlexCounterOrch` → `generateInterfaceMap()` | `flexcounterorch.cpp:283-285` |
| `generateInterfaceMap()` = タイマーキック | `intfsorch.cpp:1576-1578` |
| orchdaemon 初期化順序 | `orchdaemon.cpp:232,283,296,625` |
