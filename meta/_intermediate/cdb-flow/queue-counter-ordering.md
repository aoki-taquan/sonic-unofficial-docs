# COUNTERS_DB QUEUE カウンタ — Phase B 書込み順依存スキャンノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP` / `COUNTERS:<oid>`（QUEUE_STAT_COUNTER グループ）
Consumer: `orchagent` / `PortsOrch` + `FlexCounterOrch` (`sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/flexcounterorch.cpp`)
スキャン範囲: `initializeQueuesBulk()`, `generateQueueMap()`, `generateQueueMapPerPort()`, `addQueueFlexCounters()`, `addQueueFlexCountersPerPortPerQueueIndex()`, `FlexCounterOrch::doTask()`, `getQueueConfigurations()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SAI OID フェッチ (`initializeQueuesBulk`) → `generateQueueMap()` → マッピング書き込み

- `PortsOrch::initializePorts()` (`portsorch.cpp:6583-6598`) で `initializeQueuesBulk(ports)` が呼ばれ、SAI から各ポートの Queue OID リスト (`SAI_PORT_ATTR_QOS_QUEUE_LIST`) を取得して `port.m_queue_ids` へキャッシュする。
- `port.m_queue_ids` が空の状態で `generateQueueMapPerPort()` / `addQueueFlexCountersPerPortPerQueueIndex()` が呼ばれると、ループが 0 回で終わり `COUNTERS_QUEUE_NAME_MAP` 等のマッピングが書き込まれない。
- **順序依存（強制）**: `FLEX_COUNTER_TABLE|QUEUE|FLEX_COUNTER_STATUS = enable` が orchagent 起動前に CONFIG_DB に書き込まれていても、`initializePorts()` による OID フェッチ完了前は `generateQueueMap()` は実行されない。`FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が false の間 `return` する (`flexcounterorch.cpp:164-167`) ため、enable イベントは allPortsReady 後に処理される。
- evidence: `portsorch.cpp:6583-6598`, `portsorch.cpp:6854-6950`, `flexcounterorch.cpp:164-167`

### 2. Warm-reboot 60 秒遅延タイマー

- `FlexCounterOrch` コンストラクタ (`flexcounterorch.cpp:127-136`) で `FLEX_COUNTER_DELAY_SEC = 60` 秒のタイマーを設定する。
- Cold boot では即 `m_delayTimerExpired = true` になり遅延なし。
- Warm-reboot では `SelectableTimer` が起動し、60 秒間 `doTask()` 先頭の `if (!m_delayTimerExpired) return;` (`flexcounterorch.cpp:156-158`) で全 FlexCounter 処理をブロックする。
- **順序依存（warm-reboot 固有）**: warm-reboot 中に `FLEX_COUNTER_TABLE|QUEUE = enable` を書き込んでも最大 60 秒間 `generateQueueMap()` / `addQueueFlexCounters()` が呼ばれず、COUNTERS_DB のキュー統計は 60 秒間更新されない。
- evidence: `flexcounterorch.cpp:44`, `flexcounterorch.cpp:127-136`, `flexcounterorch.cpp:156-158`

### 3. `m_isQueueMapGenerated` ガード — generateQueueMap() は一度だけ実行

- `generateQueueMap()` (`portsorch.cpp:8391-8443`) は先頭で `m_isQueueMapGenerated` を確認し、既に `true` であれば即 `return` する。
- `FLEX_COUNTER_TABLE|QUEUE = enable` と `FLEX_COUNTER_TABLE|QUEUE_WATERMARK = enable` が両方届いた場合、最初の enable 処理で `generateQueueMap()` が実行されてフラグが立つ。2 回目は `generateQueueMap()` を素通りするが、`addQueueFlexCounters()` / `addQueueWatermarkFlexCounters()` は別フラグで保護されているため正常に動作する。
- **順序非依存（通常）**: QUEUE と QUEUE_WATERMARK の enable 順序は COUNTERS_DB の最終状態に影響しない。ただし `m_isQueueMapGenerated` がセットされた後に新規ポートが追加されても `generateQueueMap()` は再実行されないため、新規ポートは `createPortBufferQueueCounters()` 経由でのみマッピングが生成される。
- evidence: `portsorch.cpp:8391-8396`, `portsorch.cpp:8443`

### 4. `BUFFER_QUEUE` → `FLEX_COUNTER_TABLE|QUEUE = enable` の順序依存

- ランタイム中に `BUFFER_QUEUE` テーブルへの SET が届くと `PortsOrch` は `createPortBufferQueueCounters()` (`portsorch.cpp:8700-8755`) を呼ぶ。
- `flexCounterOrch->getQueueCountersState()` が `true`（= `FLEX_COUNTER_TABLE|QUEUE` が enable）の場合のみ `addQueueFlexCountersPerPortPerQueueIndex()` が呼ばれ SAI カウンタが `FLEX_COUNTER_DB` へ登録される。
- **順序依存（緩）**: `BUFFER_QUEUE` を先に書き込んで後から `FLEX_COUNTER_TABLE|QUEUE = enable` にした場合、`BUFFER_QUEUE` 設定時点では `getQueueCountersState()` が `false` のためカウンタ登録がスキップされる。その後 `enable` を書くと `addQueueFlexCounters(getQueueConfigurations())` が実行されて当時点で非ゼロプロファイルを持つ `BUFFER_QUEUE` エントリのカウンタが追加される。逆順（enable 先、BUFFER_QUEUE 後）でも `createPortBufferQueueCounters()` 内の条件が満たされるため即時追加される。どちらの順序でも最終状態は同じ。
- evidence: `portsorch.cpp:8730-8744`, `flexcounterorch.cpp:247-252`

### 5. `isCreateOnlyConfigDbBuffers` — DEVICE_METADATA の先行読み込み

- `FlexCounterOrch` コンストラクタ (`flexcounterorch.cpp:110-124`) で `DEVICE_METADATA|localhost|create_only_config_db_buffers` を起動時に 1 回読み込み `m_createOnlyConfigDbBuffers` にキャッシュする。
- `getQueueConfigurations()` (`flexcounterorch.cpp:546`) はこの値によって分岐する:
  - `false`（デフォルト）または VoQ モード: 全ポートの全キューに対してカウンタを有効化
  - `true`: `BUFFER_QUEUE` に非ゼロプロファイルが設定されたキューのみ有効化
- **順序依存（後追い変更は限定的効果）**: `DEVICE_METADATA|localhost|create_only_config_db_buffers` を FlexCounterOrch 起動後に変更しても、既に `generateQueueMap()` が `m_isQueueMapGenerated = true` でガードされている場合、変更は以後の `getQueueConfigurations()` 呼び出しにのみ影響し、既登録カウンタは変更されない。既存カウンタを変更するには orchagent 再起動が必要。
- evidence: `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:488-521`, `flexcounterorch.cpp:544-554`

### 6. VoQ モード — 順序非依存で全キューカウンタを登録

- `gMySwitchType == "voq"` の場合、`getQueueConfigurations()` (`flexcounterorch.cpp:546-551`) は `createAllAvailableBuffersStr` を返し、BUFFER_QUEUE 設定に依存しない。
- **順序非依存（VoQ）**: VoQ モードでは `FLEX_COUNTER_TABLE|QUEUE = enable` / `BUFFER_QUEUE` の書込み順序に関わらず、`generateQueueMap()` が呼ばれた時点で全 egress queue カウンタが `FLEX_COUNTER_DB` に登録される。
- evidence: `portsorch.cpp:8499-8514`, `flexcounterorch.cpp:544-551`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI OID フェッチ (`initializeQueuesBulk`) → `generateQueueMap()` → マッピング書き込み | 先行必須（allPortsReady 前は doTask がブロック） | FlexCounterOrch が `allPortsReady()` チェックで自動待機 |
| 2 | Warm-reboot: 60 秒 delay timer → その間 FlexCounter 処理ブロック | 強制遅延（warm-reboot 固有） | `FLEX_COUNTER_DELAY_SEC=60` は定数。COUNTERS_DB 更新は 60 秒後から再開 |
| 3 | `m_isQueueMapGenerated` ガード: `generateQueueMap()` は初回のみ | 冪等保護（順序非依存） | 新規ポート追加は `createPortBufferQueueCounters()` 経由 |
| 4 | `BUFFER_QUEUE` SET と `FLEX_COUNTER_TABLE\|QUEUE = enable` の順序 | どちらが先でも最終状態は同じ | BUFFER_QUEUE 先でも enable 時に `addQueueFlexCounters()` で追加される |
| 5 | `DEVICE_METADATA.create_only_config_db_buffers` の事後変更 | 以後の `getQueueConfigurations()` にのみ影響 | 既存カウンタを変更するには orchagent 再起動が必要 |
| 6 | VoQ モード: 全キューカウンタは常時登録（FLEX_COUNTER_TABLE / BUFFER_QUEUE 順序無関係） | 順序依存なし | VoQ 固有仕様 |
