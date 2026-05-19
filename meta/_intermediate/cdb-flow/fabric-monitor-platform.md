# FABRIC_MONITOR テーブル — Phase H プラットフォーム差異スキャンノート

対象ページ: `docs/reference/config-db/fabric-monitor.md`
対象テーブル: `CONFIG_DB.FABRIC_MONITOR`
調査ソース: `sonic-swss/orchagent/fabricportsorch.cpp`, `orchagent/orchdaemon.cpp`, `orchagent/main.cpp`
調査日: 2026-05-19

---

## 検出されたプラットフォーム差異

### 1. switch_type による FabricPortsOrch の起動モード分岐

`main.cpp:995-1011` にて `gMySwitchType` の値により orchagent の起動クラスが分岐する:

| `gMySwitchType` | 起動クラス | FabricPortsOrch | fabricPortStat | fabricQueueStat |
|---|---|---|---|---|
| `"voq"` | `OrchDaemon` | 起動 (`m_fabricEnabled=true`) | 有効 | **無効** |
| `"fabric"` | `FabricOrchDaemon` | 起動 (専用デーモン) | デフォルト有効 | デフォルト有効 |
| その他 (標準 ToR 等) | `OrchDaemon` | **起動しない** | N/A | N/A |

FABRIC_MONITOR テーブルは `gMySwitchType == "voq"` または `"fabric"` の場合にのみ `FabricPortsOrch` が起動し、機能する。標準 ToR では `FabricPortsOrch` 自体が生成されないため FABRIC_MONITOR に値を書き込んでも何も処理されない。

> Evidence: `orchestrator/main.cpp:997-1014`

### 2. switch_type による switch drop counter ポーリング間隔の差異

`FabricPortsOrch` コンストラクタ (`fabricportsorch.cpp:104-111`) は `gMySwitchType` により switch drop counter の FlexCounter ポーリング間隔を切り替える:

| `gMySwitchType` | 定数 | ポーリング間隔 |
|---|---|---|
| `"voq"` | `SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` | **500 ms** |
| `"fabric"` | `FABRIC_SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` | **60,000 ms (60 秒)** |

この switch drop counter は FABRIC_MONITOR の設定フィールドとは直接関係しないが、同じ `FabricPortsOrch` が管理する診断カウンタの収集頻度が switch_type で大きく異なる。voq switch では 500 ms の高頻度収集、fabric switch では 60 秒の低頻度収集となる。

> Evidence: `orchagent/fabricportsorch.cpp:33-34,104-111`

### 3. キャパシティ閾値アラートの NOTICE ログ — voq のみ

`updateFabricCapacity()` (`fabricportsorch.cpp:1201,1214`) のキャパシティ低下/復帰イベント発生時、`SWSS_LOG_NOTICE` によるアラートログ出力は `gMySwitchType == "voq"` の場合のみ実行される。`"fabric"` switch では同じキャパシティ閾値超過が起きても `SWSS_LOG_NOTICE` は出力されない（`SWSS_LOG_INFO` のみ）。

```cpp
// fabricportsorch.cpp:1201-1207 (voq のみ NOTICE)
if (gMySwitchType == "voq")
{
    SWSS_LOG_NOTICE("Total links %d. Expected up links %d. Operational links %d. Fabric capacity %s than threshold.",
          total_links, expect_links, operating_links, cur_event.c_str());
}
```

`monCapacityThreshWarn` を設定しても、`gMySwitchType == "fabric"` の環境ではキャパシティ閾値超過の syslog NOTICE が出力されない点に注意。STATE_DB `FABRIC_CAPACITY_DATA` への書込み自体は両 switch_type で行われる。

> Evidence: `orchagent/fabricportsorch.cpp:1201-1214`

### 4. FabricOrchDaemon (fabric switch) と OrchDaemon (voq switch) の FabricPortsOrch 引数差異

| 起動クラス | `FabricPortsOrch` コンストラクタ引数 | fabricPortStatEnabled | fabricQueueStatEnabled |
|---|---|---|---|
| `OrchDaemon` (voq) | `FabricPortsOrch(applDb, tables, true, false)` | `true` | `false` |
| `FabricOrchDaemon` (fabric) | `FabricPortsOrch(applDb, tables)` (デフォルト引数使用) | `true` (デフォルト) | `true` (デフォルト) |

voq switch では fabricQueueStat が無効化されており、COUNTERS_DB のファブリックキュー統計は収集されない。fabric switch では両方の統計が有効。

> Evidence: `orchagent/orchdaemon.cpp:601-611,1297-1303`

---

## プラットフォーム差異サマリ

| 観点 | voq switch | fabric switch | 標準 ToR |
|---|---|---|---|
| FabricPortsOrch 起動 | 起動 | 起動 | **起動しない** |
| FABRIC_MONITOR 処理 | 有効 | 有効 | **無効 (テーブル無視)** |
| switch drop counter 収集間隔 | 500 ms | 60,000 ms | N/A |
| キャパシティ閾値 NOTICE ログ | **出力あり** | **出力なし** | N/A |
| fabricPortStat | 有効 | 有効 | N/A |
| fabricQueueStat | **無効** | 有効 | N/A |
