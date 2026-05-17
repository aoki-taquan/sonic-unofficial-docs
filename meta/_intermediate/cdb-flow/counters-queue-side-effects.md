# COUNTERS_DB QUEUE / PG カウンタ — Phase F 副作用スキャンノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP` / `COUNTERS_PG_PORT_MAP` / `COUNTERS_PG_INDEX_MAP`  
Consumer: `orchagent` / `PortsOrch` + `CounterNameMapUpdater` + `HFTelOrch` + `CounterCheckOrch`  
スキャン範囲: `portsorch.cpp` (generateQueueMap, generateQueueMapPerPort, createPortBufferQueueCounters, deletePortBufferQueueCounters, generatePriorityGroupMap, createPortBufferPgCounters, deletePortBufferPgCounters), `counternameupdater.cpp`, `hftelorch.cpp` (locallyNotify, SUPPORT_COUNTER_TABLES), `countercheckorch.cpp` (addPort, removePort, mcCounterCheck, pfcFrameCounterCheck)

---

## 検出した副作用

### 1. COUNTERS_QUEUE_NAME_MAP / COUNTERS_PG_NAME_MAP 書き込み → HFTelOrch::locallyNotify() カスケード

`CounterNameMapUpdater::setCounterNameMap()` (`counternameupdater.cpp`) は COUNTERS_DB の `COUNTERS_QUEUE_NAME_MAP` または `COUNTERS_PG_NAME_MAP` へ `hset` する前に、`gHFTOrch` が非 null（高周波テレメトリ機能が有効）の場合に `HFTelOrch::locallyNotify()` を同期呼び出しする。

`HFTelOrch::SUPPORT_COUNTER_TABLES` (`hftelorch.cpp:25-30`) には以下がハードコードされている:
- `COUNTERS_PORT_NAME_MAP` → `SAI_OBJECT_TYPE_PORT`
- `COUNTERS_BUFFER_POOL_NAME_MAP` → `SAI_OBJECT_TYPE_BUFFER_POOL`
- `COUNTERS_QUEUE_NAME_MAP` → `SAI_OBJECT_TYPE_QUEUE`
- `COUNTERS_PG_NAME_MAP` → `SAI_OBJECT_TYPE_INGRESS_PRIORITY_GROUP`

`locallyNotify()` (`hftelorch.cpp:106-170`) は:
1. `m_counter_name_cache` をインプロセスで更新する
2. 対応するアクティブな HFT プロファイルがある場合、`profile->setObjectSAIID()` / `profile->delObjectSAIID()` を呼び出し
3. `profile->tryCommitConfig()` で TAM 設定を syncd に送信する

**副作用のトリガーポイント**:
- `generateQueueMap()` / `generateQueueMapPerPort()` → `m_queueCounterNameMapUpdater->setCounterNameMap(queueVector)` (`portsorch.cpp:8524, 8749`)
- `createPortBufferQueueCounters()` → `m_queueCounterNameMapUpdater->setCounterNameMap(queueVector)` (`portsorch.cpp:8749`)
- `deletePortBufferQueueCounters()` → `m_queueCounterNameMapUpdater->delCounterNameMap(name.str())` (`portsorch.cpp:8789`)
- `generatePriorityGroupMap()` → `m_pgCounterNameMapUpdater->setCounterNameMap(pgVector)` (`portsorch.cpp:8882, 8937`)
- `deletePortBufferPgCounters()` → `m_pgCounterNameMapUpdater->delCounterNameMap(name.str())` (`portsorch.cpp:9081`)

**重要な点**: `locallyNotify()` は同期処理。`setCounterNameMap()` の呼び出しコスト（= HFT プロファイル更新 + TAM 設定送信）がスパイクすると、その間 portsorch のメインループがブロックされる。ただし `gHFTOrch` が null（デフォルト: 高周波テレメトリ非有効時）の場合はこの副作用は発生しない。

evidence: `counternameupdater.cpp:21-34`, `hftelorch.cpp:25-30`, `hftelorch.cpp:106-170`

### 2. COUNTERS_QUEUE_NAME_MAP 書き込み → CounterCheckOrch への Port 登録

`generateQueueMap()` (`portsorch.cpp:8525`) および `createPortBufferQueueCounters()` (`portsorch.cpp:8754`) でキューマッピングが書き込まれると同時に `CounterCheckOrch::getInstance().addPort(port)` が呼ばれる。同様に `deletePortBufferQueueCounters()` (`portsorch.cpp:8819`) では `CounterCheckOrch::getInstance().removePort(port)` が呼ばれる。

`CounterCheckOrch` は 5 分間隔 (`COUNTER_CHECK_POLL_TIMEOUT_SEC = 300`) の周期タイマーで:
- `mcCounterCheck()`: ロスレスキュー（PFC 対象）への Multicast フレーム到着を `COUNTERS_DB COUNTERS:<OID>` から読み取り、カウンタ増分を検出すると `SWSS_LOG_WARN` を出力
- `pfcFrameCounterCheck()`: PFC フレームカウンタの異常検出

**副作用**: `BUFFER_QUEUE` 追加でキューマッピングが生成されると、該当ポートが CounterCheckOrch の監視リストに自動登録される。`BUFFER_QUEUE` 削除によりマッピングが削除されると監視リストからも除外される。**このカウンタ監視は FLEX_COUNTER_TABLE の enable/disable 状態に依存しない**（CounterCheckOrch は直接 SAI `sai_get_queue_stats` を呼んで `COUNTERS_DB` から読み取る）。

evidence: `portsorch.cpp:8525, 8754, 8819`, `countercheckorch.cpp:24-50`, `countercheckorch.cpp:224-235`

### 3. COUNTERS_PG_NAME_MAP 書き込み → CounterCheckOrch への Port 登録（PG 系）

`generatePriorityGroupMap()` (`portsorch.cpp:8886, 8941`) での PG マッピング生成時にも `CounterCheckOrch::getInstance().addPort(port)` が呼ばれる。`deletePortBufferPgCounters()` (`portsorch.cpp:9099`) では `removePort()` が呼ばれる。

evidence: `portsorch.cpp:8886, 8941, 9099`, `countercheckorch.cpp:224-235`

### 4. queue_watermark_manager / pg_watermark_manager の READ_AND_CLEAR モード副作用

`queue_watermark_manager` は `StatsMode::READ_AND_CLEAR` で初期化 (`portsorch.cpp:735`)。syncd FlexCounter がウォーターマーク統計をポーリングするたびにハードウェアのウォーターマークレジスタをクリアする。この副作用は FLEX_COUNTER_TABLE|QUEUE_WATERMARK が enable の限り継続し、`watermarkstat` ツールが `PERIODIC_WATERMARKS` テーブルからゼロ値を読むことで確認できる。

`pg_watermark_manager` も同様に `StatsMode::READ_AND_CLEAR` (`portsorch.cpp:736`) で動作し、`PG_WATERMARK` グループが enable の間は PG ウォーターマークレジスタが継続的にクリアされる。

**外部への副作用**: 読み取り API が副作用を持つため、複数の監視ツールが同時に `watermarkstat` を実行すると互いのウォーターマーク値をクリアし合う可能性がある（`USER_WATERMARKS` テーブルを使用する場合は `watermarkstat -c` による明示的クリアまで保持される）。

evidence: `portsorch.cpp:735-736`, FlexCounter.cpp ReadAndClear mode

### 5. WRED 能力登録時の STATE_DB 書き込み副作用

`checkWredCapability()` (`portsorch.cpp:1894-1909`) が WRED/ECN をサポートすると判定したポートのキューに対して `addWredQueueFlexCounters()` を呼んだ後、`QUEUE_COUNTER_CAPABILITIES` テーブルを STATE_DB に書き込む（`schema.h:528` の `STATE_QUEUE_COUNTER_CAPABILITIES_NAME`）。

この STATE_DB 書き込みにより外部監視ツールやほかの orchestrator が WRED サポート状況を参照可能になる。ASIC が WRED をサポートしない場合はこのエントリが存在しないため、外部ツールは `key not found` を「未サポート」として扱う必要がある。

evidence: `portsorch.cpp:1894-1909`, `sonic-swss-common/common/schema.h:528`

---

## 副作用サマリ

| # | トリガー操作 | 副作用 | 条件 |
|---|------------|--------|------|
| 1 | `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` への SET/DEL | `HFTelOrch::locallyNotify()` 同期呼び出し → TAM 設定更新 | `gHFTOrch != null`（HFT 有効時のみ） |
| 2 | `generateQueueMap()` / `createPortBufferQueueCounters()` | `CounterCheckOrch::addPort()` → MC/PFC カウンタ監視リスト登録 | 常時（FLEX_COUNTER_TABLE 状態依存なし） |
| 3 | `deletePortBufferQueueCounters()` / `deletePortBufferPgCounters()` | `CounterCheckOrch::removePort()` → 監視リスト除外 | 常時 |
| 4 | `QUEUE_WATERMARK` / `PG_WATERMARK` FlexCounter ポーリング | ハードウェアウォーターマークレジスタのリセット（READ_AND_CLEAR） | FLEX_COUNTER_TABLE|QUEUE_WATERMARK / PG_WATERMARK が enable 時 |
| 5 | `checkWredCapability()` 成功 + WRED カウンタ追加 | STATE_DB `QUEUE_COUNTER_CAPABILITIES` 書き込み | ASIC が WRED をサポートする場合 |
