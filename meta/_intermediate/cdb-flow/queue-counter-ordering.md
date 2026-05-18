# COUNTERS_DB QUEUE カウンタ — Phase B 書込み順依存スキャンノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP` / `COUNTERS:<oid>`  
Consumer: `orchagent` / `PortsOrch` + `FlexCounterOrch`  
スキャン範囲: `initializeQueuesBulk()`, `generateQueueMap()`, `generateQueueMapPerPort()`, `addQueueFlexCounters()`, `addQueueFlexCountersPerPortPerQueueIndex()`, `addPortBufferQueueCounters()`, `FlexCounterOrch::doTask()`, `getQueueConfigurations()`, `FlexCounterOrch` コンストラクタ

---

## 検出した順序依存・タイミング依存

### 1. SAI OID フェッチが先行必須

- `PortsOrch::initializePorts()` 内で `initializeQueuesBulk(ports)` が呼ばれ、SAI から各ポートの Queue OID リスト（`SAI_PORT_ATTR_QOS_QUEUE_LIST`）を取得して `port.m_queue_ids` へキャッシュする。
- `port.m_queue_ids` が空の状態で `generateQueueMapPerPort()` / `addQueueFlexCountersPerPortPerQueueIndex()` が呼ばれると、ループが 0 回で終わりマッピングが COUNTERS_DB に書き込まれない。
- `FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が `false` の間は先頭で `return` する（`flexcounterorch.cpp:164-167`）ため、`FLEX_COUNTER_TABLE|QUEUE = enable` が orchagent 起動前に書き込まれていても OID フェッチ完了まで `generateQueueMap()` は呼ばれない。
- evidence: `portsorch.cpp:6583-6598`, `portsorch.cpp:6854-6950`, `flexcounterorch.cpp:164-167`

### 2. Warm-reboot 時の 60 秒遅延

- `FlexCounterOrch` コンストラクタ（`flexcounterorch.cpp:127-136`）で `FLEX_COUNTER_DELAY_SEC = 60` 秒の `SelectableTimer` を設定する。
- Cold boot では即 `m_delayTimerExpired = true` になり遅延なし。
- Warm-reboot では `doTask()` 冒頭の `if (!m_delayTimerExpired) return;`（`flexcounterorch.cpp:156-158`）で全 FlexCounter 処理が 60 秒間ブロックされる。
- evidence: `flexcounterorch.cpp:44`, `flexcounterorch.cpp:127-136`, `flexcounterorch.cpp:156-158`, `flexcounterorch.cpp:419-430`

### 3. `m_isQueueMapGenerated` ガード — 冪等保護

- `generateQueueMap()`（`portsorch.cpp:8391-8443`）は先頭で `m_isQueueMapGenerated` を確認し、既に `true` であれば即 `return`。
- `FLEX_COUNTER_TABLE|QUEUE = enable` と `FLEX_COUNTER_TABLE|QUEUE_WATERMARK = enable` が両方届いた場合、最初の enable 処理でフラグが立つ。2 回目の enable は `generateQueueMap()` を素通りするが、`addQueueFlexCounters()` / `addQueueWatermarkFlexCounters()` は別フラグで保護されているため正常動作。
- evidence: `portsorch.cpp:8391-8396`, `portsorch.cpp:8443`

### 4. `BUFFER_QUEUE` → `createPortBufferQueueCounters()` — FLEX_COUNTER_TABLE|QUEUE が先行必須

- ランタイム中に `BUFFER_QUEUE` への SET が届くと `PortsOrch` は `createPortBufferQueueCounters()`（`portsorch.cpp:8700-8755`）を呼ぶ。
- `flexCounterOrch->getQueueCountersState()` が `true`（= FLEX_COUNTER_TABLE|QUEUE が enable）の場合のみ `addQueueFlexCountersPerPortPerQueueIndex()` を呼んで SAI カウンタを登録する。
- `BUFFER_QUEUE` を先に書き、後から `FLEX_COUNTER_TABLE|QUEUE = enable` にした場合でも、`enable` 処理時に `addQueueFlexCounters(getQueueConfigurations())` が実行されて遡及追加されるため、最終状態は同じ。
- evidence: `portsorch.cpp:8730-8744`, `flexcounterorch.cpp:247-252`

### 5. `DEVICE_METADATA.create_only_config_db_buffers` の事後変更

- `FlexCounterOrch` コンストラクタで `DEVICE_METADATA|localhost|create_only_config_db_buffers` を起動時に 1 回読み込み `m_createOnlyConfigDbBuffers` にキャッシュ。
- 事後変更は `handleDeviceMetadataTable()` で動的更新されるが、`m_isQueueMapGenerated` が既に `true` であれば以後の `getQueueConfigurations()` 呼び出しにのみ影響し、既登録カウンタは変更されない。
- evidence: `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:488-521`, `flexcounterorch.cpp:544-554`

### 6. VoQ システム — egress queue カウンタは順序非依存

- `gMySwitchType == "voq"` の場合、`generateQueueMapPerPort()` は `getQueueCountersState()` に関係なく `addQueueFlexCountersPerPortPerQueueIndex()` を直接呼ぶ。
- VoQ モードでは `FLEX_COUNTER_TABLE|QUEUE = enable` / `BUFFER_QUEUE` の書込み順に関わらず、`generateQueueMap()` が呼ばれた時点で全 egress queue カウンタが FLEX_COUNTER_DB に登録される。
- evidence: `portsorch.cpp:8499-8514`, `flexcounterorch.cpp:544-551`

### 7. WRED カウンタ — `BUFFER_QUEUE` との順序

- `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE = enable` が届くと `addWredQueueFlexCounters(getQueueConfigurations())` が呼ばれる（`flexcounterorch.cpp:279-281`）。
- `createPortBufferQueueCounters()` 内にも `getWredQueueCountersState()` チェックがあり、BUFFER_QUEUE 追加時点で WRED が enable なら即時追加される。
- どちらの順序でも最終状態は同じ（依存 #4 と同パターン）。
- ASIC が当該 SAI 統計をサポートしない場合は `checkWredCapability()` で検出され silent 未登録（順序と無関係）。
- evidence: `portsorch.cpp:8741-8745`, `flexcounterorch.cpp:276-281`

### 8. DEL 操作 — カウンタ即時停止

- `removePortBufferQueueCounters()` → `deletePortBufferQueueCounters()`（`portsorch.cpp:8756-8816`）は `BUFFER_QUEUE` エントリの DEL で呼ばれ、マッピングテーブルから削除し `queue_stat_manager.clearCounterIdList()` でカウンタ登録を削除する。
- DEL 前に `FLEX_COUNTER_TABLE|QUEUE = disable` にする必要はなく、`BUFFER_QUEUE` DEL のみで当該キューのカウンタ収集が停止する。
- evidence: `portsorch.cpp:8756-8816`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI OID フェッチ → `generateQueueMap()` → マッピング書き込み | 先行必須（allPortsReady 前は doTask がブロック） | FlexCounterOrch が `allPortsReady()` チェックで自動待機 |
| 2 | Warm-reboot 時: 60 秒 delay timer → FlexCounter 処理ブロック | 強制遅延（warm-reboot 固有） | `FLEX_COUNTER_DELAY_SEC=60` は定数 |
| 3 | `m_isQueueMapGenerated` ガード: `generateQueueMap()` は初回のみ | 冪等保護（順序非依存） | 新規ポート追加は `createPortBufferQueueCounters()` 経由 |
| 4 | `BUFFER_QUEUE` SET と `FLEX_COUNTER_TABLE\|QUEUE = enable` の前後 | どちらが先でも最終状態同じ | 推奨: 同時または BUFFER_QUEUE 先 |
| 5 | `DEVICE_METADATA.create_only_config_db_buffers` の事後変更 | 以後の `getQueueConfigurations()` にのみ影響 | 変更反映には orchagent 再起動が必要 |
| 6 | VoQ モード: egress queue カウンタは常時登録 | 順序依存なし | VoQ 固有仕様 |
| 7 | WRED_ECN_QUEUE enable と BUFFER_QUEUE の順序 | 依存 #4 と同パターン | ASIC 非サポートは silent 未登録 |
| 8 | `BUFFER_QUEUE` DEL → カウンタ即時停止 | 順序依存なし | DEL 前に disable 不要 |
