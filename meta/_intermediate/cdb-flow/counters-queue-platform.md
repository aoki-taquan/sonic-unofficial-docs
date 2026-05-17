# counters-queue — Phase H (platform) 調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp`（initializePorts, initCounterCapabilities, isMlnxPlatform, generateQueueMapPerPort）
- `sonic-swss/orchagent/orchdaemon.cpp`（PfcWdSwOrch per-platform instantiation, lines 635–843）
- `sonic-swss/orchagent/orch.h`（platform substring defines）
- `sonic-swss/orchagent/nvda_port_trim_drop.lua`

---

## 発見事項

### 1. DPU モードではキュー/PG カウンタ初期化をスキップ

`initializePorts()` (`portsorch.cpp:6583`) は `gMySwitchType != "dpu"` のときのみ
`initializeQueuesBulk()` / `initializePriorityGroupsBulk()` を呼ぶ（`portsorch.cpp:6589-6592`）。
DPU では `m_queue_ids` が未初期化となるため、`generateQueueMap()` / `generatePriorityGroupMap()` の
ループが 0 回で完結し、COUNTERS_QUEUE_NAME_MAP / COUNTERS_PG_NAME_MAP は書き込まれない。
DPU モードのホスト TX キューのみ `createPortBufferQueueCounters()` を使い、m_queue_ids のサイズチェック付きで登録 (`portsorch.cpp:6454-6458`)。

### 2. VoQ モードではカウンタ制御の特別経路

`generateQueueMapPerPort()` (`portsorch.cpp:8446`) は VoQ パスと通常パスを分岐する。
VoQ モード (`gMySwitchType == "voq"`) では以下が異なる：
- `FLEX_COUNTER_TABLE|QUEUE = disable` 設定を無視して `addQueueFlexCountersPerPortPerQueueIndex()` を強制実行
- `voq_stat_ids`（`SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS`）を追加登録
- VoQ 専用テーブル `COUNTERS_VOQ_NAME_MAP` に書き込み

### 3. Mellanox プラットフォーム固有: trim stat Lua プラグイン

`isMlnxPlatform()` (`portsorch.cpp:689`) は環境変数 `platform` が `"mellanox"` を含むか確認。
以下の3条件が同時に成立する場合のみ `nvda_port_trim_drop.lua` が PORT_STAT FlexCounter グループの
plugin として登録される (`portsorch.cpp:857-863`)：
  - `isMlnxPlatform()` が true
  - `SAI_PORT_STAT_TRIM_PACKETS` がサポートされている
  - `SAI_PORT_STAT_TX_TRIM_PACKETS` がサポートされている
  - `SAI_PORT_STAT_DROPPED_TRIM_PACKETS` が **サポートされていない**

`nvda_port_trim_drop.lua` の実装: `DROPPED_TRIM_PACKETS = TRIM_PACKETS - TX_TRIM_PACKETS` を
Redis Lua 内でアトミック計算して `COUNTERS:<port_oid>` に書き込む。
Queue 側では `SAI_QUEUE_STAT_TRIM_PACKETS` / `SAI_QUEUE_STAT_DROPPED_TRIM_PACKETS` / 
`SAI_QUEUE_STAT_TX_TRIM_PACKETS` が queue_stat_ids に含まれる（Lua プラグイン補完なし）。
ASIC が直接これらの値を提供する場合は Lua 計算不要。

### 4. PFC Watchdog ハンドラとキュー統計のプラットフォーム分岐

`orchdaemon.cpp:635-843` の PfcWdSwOrch インスタンス化はプラットフォームごとに異なる
キュー統計セットとハンドラクラスを使う：

| platform 値 | PortStatIds に含む SAI カウンタ | QueueStatIds | ハンドラクラス |
|---|---|---|---|
| `"mellanox"` / `"vs"` | PFC_N_RX_PAUSE_DURATION_US (0-7), PFC_N_RX_PKTS (0-7) | PACKETS, CURR_OCCUPANCY_BYTES | PfcWdZeroBufferHandler / PfcWdLossyHandler |
| `"broadcom"` | PFC_N_RX_PKTS (0-7), PFC_N_ON2OFF_RX_PKTS (0-7) | PACKETS, CURR_OCCUPANCY_BYTES | PfcWdDlrHandler（DLR ON）/ PfcWdAclHandler（DLR OFF） |
| `"marvell-teralynx"` / `"marvell-prestera"` / `"clounix"` / `"barefoot"` / `"nephos"` | PFC_N_RX_PAUSE_DURATION (0-7), PFC_N_RX_PKTS (0-7) | PACKETS, CURR_OCCUPANCY_BYTES | PfcWdZeroBufferHandler / PfcWdLossyHandler（Marvell/CLX/NPS）; PfcWdAclHandler / PfcWdLossyHandler（Barefoot）|
| `"cisco-8000"` | PFC_N_RX_PKTS (0-7), PFC_N_TX_PKTS (0-7) | PACKETS のみ | PfcWdSaiDlrInitHandler / PfcWdActionHandler |
| その他（プラットフォームなし）| — | — | PfcWd orch インスタンス化なし |

これらのキュー統計は FLEX_COUNTER_TABLE とは別系統（PfcWdSwOrch が管理する専用 FlexCounter グループ）。

### 5. WRED ケイパビリティチェックと STATE_DB 書き込み

`initCounterCapabilities(gSwitchId)` (`portsorch.cpp:1107, 1850`) が orchagent 初期化時に 1 回実行。
`sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE)` でプラットフォームの WRED/ECN 能力を問合せ、
STATE_DB の `QUEUE_COUNTER_CAPABILITIES` テーブルに各フィールドの `isSupported: true/false` を書く。
`SAI_STATUS_BUFFER_OVERFLOW` が返った場合はリスト用バッファを確保して再呼び出しする 2 段取得。
能力問合せ自体が失敗（`SAI_STATUS_SUCCESS` 以外）したときは全フィールドが `isSupported: false` で初期化済みのまま。
プラットフォーム非依存コードだが、実際の WRED サポート有無は ASIC ごとに異なる。

---

## ソース証跡

- `portsorch.cpp:6449-6458`（DPU: initializeQueuesBulk スキップ・host TX queue カウンタ登録）
- `portsorch.cpp:6589-6592`（DPU: initializePorts 内の skip）
- `portsorch.cpp:8446-8530`（generateQueueMapPerPort VoQ/通常分岐）
- `portsorch.cpp:689-704`（isMlnxPlatform）
- `portsorch.cpp:857-863`（Mellanox trim Lua plugin 登録条件）
- `portsorch.cpp:1850-1967`（initCounterCapabilities）
- `portsorch.cpp:793`（m_queueCounterCapabilitiesTable: STATE_DB 接続）
- `orchdaemon.cpp:635-843`（PfcWdSwOrch プラットフォーム別インスタンス化）
- `orchdaemon.cpp:804-842`（cisco-8000 PFC WD）
- `orch.h:40-50`（platform substring 定義）
- `nvda_port_trim_drop.lua`（DROPPED_TRIM_PACKETS = TRIM_PACKETS - TX_TRIM_PACKETS 計算）
