# COUNTERS_DB QUEUE / PG カウンタ — Phase B 書込み順依存スキャンノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP`（および PG 系マップ）  
Consumer: `orchagent` / `PortsOrch` + `FlexCounterOrch` (`sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/flexcounterorch.cpp`)  
スキャン範囲: `initializeQueuesBulk()`, `generateQueueMap()`, `generateQueueMapPerPort()`, `addQueueFlexCounters()`, `addQueueFlexCountersPerPortPerQueueIndex()`, `addPortBufferQueueCounters()`, `FlexCounterOrch::doTask()`, `getQueueConfigurations()`, `FlexCounterOrch` コンストラクタ 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `initializeQueuesBulk()` — portsorch 起動直後の SAI OID フェッチが先行必須

- `PortsOrch::initializePorts()` (`portsorch.cpp:6583-6598`) 内で `initializeQueuesBulk(ports)` が呼ばれ、SAI から各ポートの Queue OID リスト (`SAI_PORT_ATTR_QOS_QUEUE_LIST`) を取得して `port.m_queue_ids` へキャッシュする。
- `port.m_queue_ids` が空の状態で `generateQueueMapPerPort()` / `addQueueFlexCountersPerPortPerQueueIndex()` が呼ばれると、ループが 0 回で終わりマッピングが COUNTERS_DB に書き込まれない。
- **順序依存**: `FLEX_COUNTER_TABLE|QUEUE|FLEX_COUNTER_STATUS = enable` が `orchagent` 起動前に CONFIG_DB に書き込まれていても、`initializePorts()` による OID フェッチが完了するまでは `generateQueueMap()` は実行されない。`FlexCounterOrch::doTask()` は `gPortsOrch->allPortsReady()` が false の間 `return` する (`flexcounterorch.cpp:164-167`) ため、enable イベントは allPortsReady 後に処理される。
- evidence: `portsorch.cpp:6583-6598`, `portsorch.cpp:6854-6950`, `flexcounterorch.cpp:164-167`

### 2. `m_delayTimerExpired` — Warm-reboot 時の 60 秒遅延

- `FlexCounterOrch` コンストラクタ (`flexcounterorch.cpp:127-136`) で `FLEX_COUNTER_DELAY_SEC = 60` 秒のタイマーを設定する。
- Cold boot では即 `m_delayTimerExpired = true` (`flexcounterorch.cpp:136`) になり遅延なし。
- Warm-reboot では `SelectableTimer` が起動し、60 秒間 `doTask()` の先頭 `if (!m_delayTimerExpired) return;` (`flexcounterorch.cpp:156-158`) で全 FlexCounter 処理をブロックする。
- **順序依存（warm-reboot 時）**: `FLEX_COUNTER_TABLE|QUEUE = enable` を warm-reboot 中に書き込んでも、最大 60 秒間 `generateQueueMap()` / `addQueueFlexCounters()` が呼ばれない。COUNTERS_DB のキュー統計は 60 秒間更新されない。
- evidence: `flexcounterorch.cpp:44`, `flexcounterorch.cpp:127-136`, `flexcounterorch.cpp:156-158`, `flexcounterorch.cpp:419-430`

### 3. `m_isQueueMapGenerated` ガード — generateQueueMap() は一度だけ実行

- `generateQueueMap()` (`portsorch.cpp:8391-8443`) は先頭で `m_isQueueMapGenerated` を確認し、既に `true` であれば即 `return` する。
- `FLEX_COUNTER_TABLE|QUEUE = enable` と `FLEX_COUNTER_TABLE|QUEUE_WATERMARK = enable` が両方届いた場合、最初の enable を処理したときに `generateQueueMap()` が実行されてフラグが立つ。2 回目の enable は `generateQueueMap()` を素通りするが、`addQueueFlexCounters()` / `addQueueWatermarkFlexCounters()` は別のフラグ (`m_isQueueFlexCountersAdded` / `m_isQueueWatermarkFlexCountersAdded`) で保護されているため正常に動作する。
- **順序依存なし（通常）**: QUEUE と QUEUE_WATERMARK の enable 順序は COUNTERS_DB の最終状態に影響しない。ただし `m_isQueueMapGenerated` がセットされた後に新規ポートが追加されても `generateQueueMap()` は再実行されないため、新規ポートは `createPortBufferQueueCounters()` 経由でのみマッピングが生成される（依存 #4 参照）。
- evidence: `portsorch.cpp:8391-8396`, `portsorch.cpp:8443`

### 4. `BUFFER_QUEUE` → `createPortBufferQueueCounters()` — FLEX_COUNTER_TABLE|QUEUE が先行必須

- ランタイム中に `BUFFER_QUEUE` テーブルへの SET が届くと `PortsOrch` は `createPortBufferQueueCounters()` (`portsorch.cpp:8700-8755`) を呼ぶ。
- この関数内で `flexCounterOrch->getQueueCountersState()` が `true`（= FLEX_COUNTER_TABLE|QUEUE が enable）の場合のみ `addQueueFlexCountersPerPortPerQueueIndex()` を呼んで SAI カウンタを登録する。
- **順序依存**: `BUFFER_QUEUE` を先に書き込み、後から `FLEX_COUNTER_TABLE|QUEUE = enable` にした場合、`BUFFER_QUEUE` 設定時点では `getQueueCountersState()` が `false` のため `addQueueFlexCounters()` は呼ばれない。事後に `enable` を書くと `addQueueFlexCounters(getQueueConfigurations())` が実行され、その時点で非ゼロプロファイルを持つ `BUFFER_QUEUE` エントリを対象にカウンタが追加される。**逆に** `FLEX_COUNTER_TABLE|QUEUE = enable` を先に書き、後から `BUFFER_QUEUE` を追加する場合は `createPortBufferQueueCounters()` 内の条件が満たされるため即時カウンタ追加される。
- **推奨順序**: `BUFFER_QUEUE` を設定してから `FLEX_COUNTER_TABLE|QUEUE = enable` にするか、`enable` が先でも動作するが後者の方が明示的で順序非依存。
- evidence: `portsorch.cpp:8730-8744`, `flexcounterorch.cpp:247-252`

### 5. `isCreateOnlyConfigDbBuffers()` — DEVICE_METADATA の先行読み込み

- `FlexCounterOrch` コンストラクタ (`flexcounterorch.cpp:110-124`) で `DEVICE_METADATA|localhost|create_only_config_db_buffers` を起動時に 1 回読み込み `m_createOnlyConfigDbBuffers` にキャッシュする。
- `getQueueConfigurations()` (`flexcounterorch.cpp:546`) は `isCreateOnlyConfigDbBuffers()` の値によって動作が分岐する:
  - `false`（デフォルト）または VoQ モード: 全ポートの全キューに対してカウンタを有効化（`createAllAvailableBuffersStr` を返す）
  - `true`: `BUFFER_QUEUE` に非ゼロプロファイルが設定されたキューのみ有効化
- **順序依存**: `DEVICE_METADATA|localhost|create_only_config_db_buffers = true` を `FlexCounterOrch` 起動後に変更しても、`handleDeviceMetadataTable()` (`flexcounterorch.cpp:488-521`) が動的に `m_createOnlyConfigDbBuffers` を更新する。ただし、既に `generateQueueMap()` が `m_isQueueMapGenerated = true` でガードされている場合、DEVICE_METADATA の変更は以後の `getQueueConfigurations()` 呼び出しにのみ影響し、既に登録済みのカウンタは変更されない。
- evidence: `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:488-521`, `flexcounterorch.cpp:544-554`

### 6. VoQ システム — egress queue カウンタは順序非依存で常時登録

- `gMySwitchType == "voq"` の場合、`generateQueueMapPerPort()` (`portsorch.cpp:8499-8514`) は `getQueueCountersState()` に関係なく `addQueueFlexCountersPerPortPerQueueIndex()` を直接呼ぶ。
- `getQueueConfigurations()` (`flexcounterorch.cpp:546-551`) も `gMySwitchType == "voq"` で `createAllAvailableBuffersStr` を返し、BUFFER_QUEUE の設定に依存しない。
- **順序依存なし（VoQ）**: VoQ モードでは `FLEX_COUNTER_TABLE|QUEUE = enable` / `BUFFER_QUEUE` の書込み順序に関わらず、`generateQueueMap()` が呼ばれた時点で全 egress queue カウンタが FLEX_COUNTER_DB に登録される。
- evidence: `portsorch.cpp:8499-8514`, `flexcounterorch.cpp:544-551`

### 7. WRED カウンタ登録 — `checkWredCapability()` と `BUFFER_QUEUE` の依存

- `FLEX_COUNTER_TABLE|WRED_ECN_QUEUE = enable` が届くと `addWredQueueFlexCounters(getQueueConfigurations())` が呼ばれる (`flexcounterorch.cpp:279-281`)。
- `addWredQueueFlexCounters()` → `addWredQueueFlexCountersPerPort()` → `addWredQueueFlexCountersPerPortPerQueueIndex()` の呼び出しチェーンで、各ポート・各キューに対して `wred_queue_stat_manager.setCounterIdList()` が呼ばれる。
- `createPortBufferQueueCounters()` 内にも `flexCounterOrch->getWredQueueCountersState()` チェックがあり (`portsorch.cpp:8741-8745`)、BUFFER_QUEUE 追加時点で WRED が enable なら即時追加される。
- **順序依存**: WRED_ECN_QUEUE の有効化は BUFFER_QUEUE 設定の後でも前でも最終的に同じ状態になる（QUEUE 依存 #4 と同じパターン）。ただし ASIC が `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` をサポートしない場合、`checkWredCapability()` で検出されてカウンタは silent に未登録となる点は順序と無関係に適用される。
- evidence: `portsorch.cpp:8741-8745`, `flexcounterorch.cpp:276-281`

### 8. DEL 操作 — COUNTERS_DB マッピングの削除とカウンタ停止

- `removePortBufferQueueCounters()` → `deletePortBufferQueueCounters()` (`portsorch.cpp:8756-8816`) は `BUFFER_QUEUE` エントリの DEL で呼ばれ、`COUNTERS_QUEUE_NAME_MAP` から該当エントリを削除し、`queue_stat_manager.clearCounterIdList()` で FLEX_COUNTER_DB からカウンタ登録を削除する。
- **順序依存**: DEL は即時実行。DEL の前に `FLEX_COUNTER_TABLE|QUEUE = disable` にする必要はなく、BUFFER_QUEUE DEL のみで当該キューのカウンタ収集が停止する。逆に `FLEX_COUNTER_TABLE|QUEUE = disable` を先に書いてもマッピングテーブルは残るため、後で `enable` に戻せば自動的に再開する。
- evidence: `portsorch.cpp:8756-8816`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI OID フェッチ (`initializeQueuesBulk`) → `generateQueueMap()` → マッピング書き込み | 先行必須（allPortsReady 前は doTask がブロック） | FlexCounterOrch が `allPortsReady()` チェックで自動待機 |
| 2 | Warm-reboot 時: 60 秒 delay timer → その間 FlexCounter 処理ブロック | 強制遅延（warm-reboot 固有） | `FLEX_COUNTER_DELAY_SEC=60` は定数。COUNTERS_DB 更新は 60 秒後から再開 |
| 3 | `m_isQueueMapGenerated` ガード: `generateQueueMap()` は初回のみ | 冪等保護（順序非依存） | 新規ポート追加は `createPortBufferQueueCounters()` 経由 |
| 4 | `BUFFER_QUEUE` SET → `FLEX_COUNTER_TABLE\|QUEUE = enable` 先後で挙動差 | 推奨: 同時または BUFFER_QUEUE 先 | どちらの順序でも最終状態は同じ。逆順でも `addQueueFlexCounters()` で追加 |
| 5 | `DEVICE_METADATA.create_only_config_db_buffers` の事後変更 | 以後の `getQueueConfigurations()` にのみ影響。既登録カウンタは変更されない | 既存カウンタを変更するには orchagent 再起動が必要 |
| 6 | VoQ モード: egress queue カウンタは常時登録（FLEX_COUNTER_TABLE / BUFFER_QUEUE 順序無関係） | 順序依存なし | VoQ 固有仕様。`disable` しても収集継続 |
| 7 | WRED_ECN_QUEUE enable と BUFFER_QUEUE の順序 | QUEUE 依存 #4 と同じパターン（どちらが先でも最終状態同じ） | ASIC 非サポートは silent 未登録（順序と無関係） |
| 8 | `BUFFER_QUEUE` DEL → カウンタ即時停止（FLEX_COUNTER_TABLE 状態に依存しない） | 順序依存なし | DEL 前に disable 不要 |
