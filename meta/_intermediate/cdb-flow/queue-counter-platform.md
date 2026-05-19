# queue-counter Phase H — プラットフォーム差スキャンノート

Generated: 2026-05-19
Target doc: docs/reference/config-db/queue-counter.md

対象テーブル: `COUNTERS_DB` QUEUE カウンタ (`COUNTERS:<oid>`, `COUNTERS_QUEUE_NAME_MAP` 等)
Consumer: `orchagent` — `PortsOrch::generateQueueMapPerPort()`, `addQueueFlexCountersPerPortPerQueueIndex()`, `initCounterCapabilities()`
スキャン範囲: `portsorch.cpp` generateQueueMap 系・addQueueFlexCounters 系・initCounterCapabilities、`flexcounterorch.cpp` doTask

---

## switch_type による挙動差

### voq

`generateQueueMapPerPort()` (`portsorch.cpp:8446-8535`) は `voq=true` と `voq=false` の 2 パスで呼ばれる:

1. `voq=false` (物理ポートの egress queue): `gMySwitchType == "voq"` 条件 (`portsorch.cpp:8504`) で `FLEX_COUNTER_TABLE|QUEUE` の enable/disable とは無関係に `addQueueFlexCountersPerPortPerQueueIndex(port, queueIndex, false, queueType)` を常時呼ぶ。理由: VOQ システムではバッファプロファイルがシステムポートに定義されるため、物理ポートの `BUFFER_QUEUE` 設定は通常存在しない。`getQueueConfigurations()` の `queuesState` には物理ポートが含まれないため、FlexCounterOrch のロジックでは enable されないが `generateQueueMapPerPort` で補完する。

2. `voq=true` (Virtual Output Queue): `m_port_voq_ids[port.m_alias]` から VOQ OID を取得し、`voq_stat_ids`（`SAI_QUEUE_STAT_CREDIT_WD_DELETED_PACKETS` を含む、`portsorch.cpp:399-401`）を `queue_stat_ids` に合算して FlexCounter 登録。VOQ カウンタに disable 機構はない (`portsorch.cpp:8483-8486`コメント参照)。

evidence: `portsorch.cpp:8483-8510`, `portsorch.cpp:8592-8614`, `portsorch.cpp:399-401`

### fabric

`FabricOrchDaemon` (`orchdaemon.cpp`) が管理する fabric switch では `PortsOrch` は起動するが QUEUE 系の FlexCounter 登録関数は呼ばれない（通常 `orchDaemon` のみが `addQueueFlexCounters` を呼ぶ）。`FlexCounterOrch::doTask()` は `gFabricPortsOrch->allPortsReady()` (`flexcounterorch.cpp:169`) を確認するが、`FLEX_COUNTER_TABLE|QUEUE = enable` の処理は `gPortsOrch` 依存であり、fabric デーモンでは `generateQueueMap` が実行されない。

evidence: `flexcounterorch.cpp:169-173`

### dpu

`portsorch.cpp:6454` コメント: "We have to test the size of m_queue_ids here since it isn't initialized on some platforms (like DPU)". DPU プラットフォームでは `m_queue_ids` が空のままとなり、`createPortBufferQueueCounters()` は `m_host_tx_queue` 設定がある場合のみ 1 エントリを生成する。通常の QUEUE FlexCounter 全体はスキップされる。

evidence: `portsorch.cpp:6454-6459`

## WRED ケイパビリティ依存

`initCounterCapabilities()` (`portsorch.cpp:1881-1922`) が `sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, ...)` を呼んで確認:

| SAI stat | capabilities table キー |
|----------|------------------------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` |

SAI クエリ失敗時は `SWSS_LOG_NOTICE` のみでサイレントスキップ。WRED カウンタは `checkWredCapability()` (`portsorch.cpp:1894-1909`) でポートごとにも確認される。

## isMlnxPlatform との関係

`isMlnxPlatform()` (`portsorch.cpp:689`) は NVIDIA Mellanox ASIC の識別に使う。QUEUE FlexCounter への影響なし。PORT trim stat Lua プラグイン登録 (`portsorch.cpp:858-863`) にのみ使用。

## VOQ NAME_MAP キー形式差

| モード | COUNTERS_QUEUE_NAME_MAP キー |
|--------|---------------------------|
| 通常 | `<port_alias>:<queue_index>` |
| VOQ (物理) | `<system_port_alias>:<queue_index>` |
| VOQ (Virtual) | `COUNTERS_VOQ_NAME_MAP` に別途格納 |

evidence: `portsorch.cpp:8468-8476` (voq 分岐), `portsorch.cpp:779` (m_voqTable 初期化)
