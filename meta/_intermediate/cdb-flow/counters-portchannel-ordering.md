# COUNTERS_DB PortChannel/LAG カウンタ — 書込み順依存 (Phase B)

調査日: 2026-05-16
対象ファイル:
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. COUNTERS_LAG_NAME_MAP の書込み順序

`portsorch` が `APP_LAG_TABLE_NAME`（`teamd` → `intfmgrd` → `orchagent`）からの SET イベントを受けて `doLagTask()` → `addLag()` を呼び出す。

```
[条件] allPortsReady() == true   # portsorch.cpp:6514
         ↓
doLagTask() → addLag(alias, lag_id, switch_id)   # portsorch.cpp:6529, 7941
         ↓
sai_lag_api->create_lag()        # portsorch.cpp:7994
         ↓
m_counterLagTable->set("", fields)  # portsorch.cpp:8022
  → COUNTERS_DB COUNTERS_LAG_NAME_MAP に <alias> → <lag_oid> を書き込み
```

**前提条件**: `allPortsReady()` が `true` になるまで LAG 処理は一切スキップされる。
`allPortsReady()` = `m_initDone && m_pendingPortSet.empty()` (`portsorch.cpp:1685-1688`)。
つまり **全物理ポートの初期化完了（PortInitDone）が LAG カウンタ登録より前に必要**。

削除時: `removeLag()` が SAI DEL の後に `m_counterLagTable->hdel("")` を実行する（`portsorch.cpp:8045+`）。

---

## 2. COUNTERS_RIF_NAME_MAP の書込み順序

RIF カウンタ登録は 2 段階の遅延登録（`m_rifsToAdd` キュー＋タイマー）で行われる。

```
[step 1] intfsorch::doTask(Consumer)   # intfsorch.cpp:661
  条件: allPortsReady() == true        # intfsorch.cpp:665
         ↓
  gPortsOrch->getPort(alias, port) が成功する必要がある
  （PORTCHANNEL エントリが portsorch で先に処理され m_portList に登録済みであること）
                                        # intfsorch.cpp:905, 922-924
         ↓
  setIntf() → sai_router_intfs_api->create_router_interface()
                                        # intfsorch.cpp:1296
         ↓
  m_rifsToAdd.push_back(port)           # intfsorch.cpp:1310
  （RIF 作成だけで FlexCounter 登録はまだ行わない）

[step 2] intfsorch::doTask(SelectableTimer &timer)  # intfsorch.cpp:1598
  ループで m_rifsToAdd を走査
         ↓
  m_vidToRidTable->hget("", id, value)  # intfsorch.cpp:1627
  （ASIC_DB の VID→RID マッピングが確定するまで待機）
         ↓
  addRifToFlexCounter(id, alias, type)  # intfsorch.cpp:1530-1538
  → m_rifNameTable->set("", ...)
     = COUNTERS_DB COUNTERS_RIF_NAME_MAP に <alias> → <rif_oid> を書き込み
```

---

## 3. 依存グラフ（要約）

```
CONFIG_DB PORTCHANNEL
       │
       ▼ (teamd → intfmgrd → APP_DB APP_LAG_TABLE_NAME)
portsorch::doLagTask()         [前提: allPortsReady()]
       │ sai_lag_api::create_lag()
       │ m_counterLagTable->set()
       ▼
COUNTERS_DB COUNTERS_LAG_NAME_MAP  ← LAG OID 登録

CONFIG_DB PORTCHANNEL_INTERFACE
       │
       ▼ (intfmgrd → APP_DB INTF_TABLE_NAME)
intfsorch::doTask(Consumer)    [前提: allPortsReady() + LAG が m_portList に存在]
       │ create_router_interface()
       │ m_rifsToAdd.push_back()
       ▼
intfsorch::doTask(SelectableTimer) [前提: ASIC_DB VID→RID 確定]
       │ addRifToFlexCounter()
       ▼
COUNTERS_DB COUNTERS_RIF_NAME_MAP  ← RIF OID 登録
       │
       ▼
FlexCounter (RIF_STAT_COUNTER_FLEX_COUNTER_GROUP)
       │ 定期 polling
       ▼
COUNTERS_DB COUNTERS:<rif_oid>
```

---

## 4. 書込み順序違反時の挙動

| 違反パターン | 結果 |
|---|---|
| `PORTCHANNEL_INTERFACE` が `PORTCHANNEL` より先に CONFIG_DB に書かれた場合 | `intfsorch` が `gPortsOrch->getPort()` で失敗 → `it++` して retry。`PORTCHANNEL` 処理完了後の次回 SelectableTimer サイクルで自動回復 |
| PortInitDone 前に LAG 設定が入った場合 | `allPortsReady()` が false → `doLagTask()` がスキップ。PortInitDone 受信後に自動処理 |
| ASIC_DB VID→RID 未確定時 | `m_rifsToAdd` にキューイングされ、タイマー周期（デフォルト 1 s）ごとに再試行 |

---

## 5. 調査証跡

| コード箇所 | 意味 |
|---|---|
| `portsorch.cpp:1685-1688` | `allPortsReady()` 実装 |
| `portsorch.cpp:6513-6529` | LAG タスクの `allPortsReady()` ガード |
| `portsorch.cpp:7941-8022` | `addLag()` — SAI 作成 → `COUNTERS_LAG_NAME_MAP` 書込み |
| `portsorch.cpp:8045+` | `removeLag()` — `COUNTERS_LAG_NAME_MAP` 削除 |
| `intfsorch.cpp:661-668` | `doTask(Consumer)` の `allPortsReady()` ガード |
| `intfsorch.cpp:905-925` | LAG が `m_portList` に未登録なら retry |
| `intfsorch.cpp:1296-1310` | `create_router_interface()` → `m_rifsToAdd` キュー |
| `intfsorch.cpp:1598-1637` | タイマー処理で VID→RID 確定後に `addRifToFlexCounter()` |
| `intfsorch.cpp:1527-1538` | `addRifToFlexCounter()` — `COUNTERS_RIF_NAME_MAP` 書込み |
