# counters-state — Phase B 書込み順依存スキャンノート

対象テーブル: `STATE_DB / PORT_COUNTER_CAPABILITIES`, `STATE_DB / QUEUE_COUNTER_CAPABILITIES`, `STATE_DB / DEBUG_COUNTER_CAPABILITIES`
Consumer (書き込み側): `orchagent` — `portsorch` (`initCounterCapabilities`) / `debugcounterorch` (`publishDropCounterCapabilities`)
スキャン範囲: orchagent/portsorch.cpp, orchagent/debugcounterorch.cpp, orchagent/flexcounterorch.cpp, orchagent/orchdaemon.cpp 全行精読

---

## 検出した順序依存・タイミング依存

### 1. portsorch コンストラクタ内の false 先書き → SAI 問い合わせ更新

- `PortsOrch::PortsOrch()` (portsorch.cpp:753-) の末尾で `initCounterCapabilities(gSwitchId)` が呼ばれる (portsorch.cpp:1107)。
- `initCounterCapabilities()` は **まず全 WRED フィールドを `"false"` で書き込み** (portsorch.cpp:1872-1879)、その後 `sai_query_stats_capability()` の結果でサポート済みフィールドを `"true"` に更新する (portsorch.cpp:1892-1968)。
- **順序依存（自己完結型）**: `"false"` 書き込みと `"true"` 更新は同一コンストラクタ内で連続して実行されるため、portsorch 初期化完了前に portstat 等が STATE_DB を参照すると一時的に全 `"false"` 状態を観測する可能性がある。
- evidence: portsorch.cpp:1850-1968

### 2. portsorch → debugcounterorch の初期化順序保証（orchdaemon）

- `orchdaemon.cpp:232` で `gPortsOrch = new PortsOrch(...)` が実行され、その後 `orchdaemon.cpp:452` で `gDebugCounterOrch = new DebugCounterOrch(...)` が実行される。
- `DebugCounterOrch` コンストラクタ内の `publishDropCounterCapabilities()` (debugcounterorch.cpp:37) は `gPortsOrch->attach(this)` より**前**に呼ばれる。
- 結果として STATE_DB への書き込み順序は確定的:
  1. `PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` ← portsorch コンストラクタ
  2. `DEBUG_COUNTER_CAPABILITIES` ← debugcounterorch コンストラクタ
- evidence: orchdaemon.cpp:232, orchdaemon.cpp:452, debugcounterorch.cpp:27-60

### 3. flexcounterorch の warm-reboot 60 秒遅延と STATE_DB への影響なし

- `FlexCounterOrch` は warm-reboot 時 `m_delayTimerExpired = false` で初期化し、60 秒後にタイマーが切れるまで `doTask()` を実質スキップする (flexcounterorch.cpp:44, 127-137)。
- この遅延は **FLEX_COUNTER_DB への COUNTER_ID_LIST 登録**（つまり syncd へのポーリング命令）を遅らせるためのものであり、`STATE_DB / *_COUNTER_CAPABILITIES` テーブルの書き込みには影響しない。
- `STATE_DB` の 3 テーブルは portsorch / debugcounterorch の**コンストラクタ**で同期的に書かれるため、flexcounterorch の warm-reboot 遅延の影響を受けない。
- また `FlexCounterOrch::bake()` は warm-reboot 調整フェーズで意図的に何もしない (flexcounterorch.cpp:525-535 コメント参照)。
- evidence: flexcounterorch.cpp:44, 127-137, 156-158, 419-431, 525-536

### 4. warm-reboot 時の portsorch bake() と STATE_DB 能力テーブル

- warm-reboot 時、`PortsOrch::bake()` (portsorch.cpp:4338-) は `APP_DB` の `PortConfigDone` / `PortInitDone` をチェックし、ポートテーブルを reconcile する。
- `initCounterCapabilities()` はコンストラクタ呼び出し時点（warm-reboot 開始直後）に実行されるため、reconcile 完了を待たずに STATE_DB を更新する。
- ただし `PORT_COUNTER_CAPABILITIES` / `QUEUE_COUNTER_CAPABILITIES` は SAI プラットフォーム能力（静的情報）を反映するものであり、warm-reboot 前後で変化しない。したがって warm-reboot 時に STATE_DB が一時的に旧値を保持していても実害はない。
- evidence: portsorch.cpp:4338-4470, portsorch.cpp:1107

### 5. generatePortCounterMap() と STATE_DB との独立性

- `portsorch::generatePortCounterMap()` (portsorch.cpp:9102) は `PORT_COUNTER_CAPABILITIES` テーブルを**参照しない**。この関数は `FLEX_COUNTER_DB` にポーリング対象を登録するのみ。
- 逆に `portstat.py` は `PORT_COUNTER_CAPABILITIES` を参照してポーリング対象を決定する。
- **順序依存**: `generatePortCounterMap()` の実行 (flexcounterorch がカウンタ enable を受信したとき) は `initCounterCapabilities()` の完了（portsorch コンストラクタ）より**後**に来るため、portstat が STATE_DB を参照する時点では常に能力情報が書き込み済みとなる。
- evidence: portsorch.cpp:9102-9129, flexcounterorch.cpp:235-240

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `"false"` 先書き → SAI query 完了 → `"true"` 更新 | 自己完結（コンストラクタ内） | 初期化完了前の参照は transient な `"false"` を観測しうる |
| 2 | portsorch 初期化 → debugcounterorch 初期化 | orchdaemon が強制保証 | DebugCounterOrch コンストラクタは gPortsOrch 後に実行される |
| 3 | flexcounterorch warm-reboot 60 秒遅延 | STATE_DB には無影響 | STATE_DB 能力テーブルはコンストラクタで同期書き込み済み |
| 4 | warm-reboot reconcile vs 能力テーブル | 実害なし（静的情報） | プラットフォーム能力は不変のため旧値継続で問題なし |
| 5 | initCounterCapabilities < generatePortCounterMap | 常に保証 | portstat 参照時点では能力テーブル書き込み済み |
