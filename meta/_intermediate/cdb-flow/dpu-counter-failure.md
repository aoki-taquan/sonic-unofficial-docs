# DPU カウンタ Phase D — 失敗挙動・retry / recovery スキャンノート

Generated: 2026-05-19
Target doc: docs/reference/config-db/dpu-counter.md

対象テーブル: `FLEX_COUNTER_TABLE|ENI` / `FLEX_COUNTER_TABLE|DASH_METER`
Consumer: `orchagent` — `FlexCounterOrch::doTask()` + `DashOrch` / `DashCounter<>`
スキャン範囲: `flexcounterorch.cpp:145-417`、`dashcounter.h:23-71`

---

## 失敗パターン一覧

### 1. warm-reboot 60 秒遅延タイマー → m_toSync 全保留

`FlexCounterOrch` コンストラクタは warm-reboot 時のみ 60 秒のタイマーを設定し、満了まで `doTask(Consumer&)` が即 return する (`flexcounterorch.cpp:156-159`)。

- **挙動**: ENI / DASH_METER への SET が `m_toSync` に保持される
- **上限**: `FLEX_COUNTER_DELAY_SEC = 60` 秒
- **復旧**: 自動（60 秒後に `doTask(SelectableTimer&)` が `m_delayTimerExpired = true`）
- **cold-start では発生しない**: コンストラクタで即 `m_delayTimerExpired = true`

### 2. `allPortsReady() = false` → m_toSync 保留（自動回復）

`gPortsOrch && !gPortsOrch->allPortsReady()` が真の間、`doTask()` は即 return (`flexcounterorch.cpp:164-167`)。

- **挙動**: PortInitDone 前の全エントリが `m_toSync` に保留
- **DPU 特記**: DPU ノードでは `gPortsOrch` が nullptr になる場合があり、この場合ガードはスキップされる
- **復旧**: 自動（portsyncd が PortInitDone を発行した時点で一括処理）

### 3. 無効グループキー → 即削除・retry なし

`flexCounterGroupMap.count(key) == 0` の場合 `NOTICE` ログ後にエントリ即削除 (`flexcounterorch.cpp:183-187`)。

- **挙動**: `NOTICE` ログ + `m_toSync.erase()` → retry なし
- **ENI / DASH_METER への影響**: `flexCounterGroupMap` に両キーは登録済みのため通常発生しない
- **復旧**: 正しいキーで再書き込みが必要

### 4. 未サポートフィールド → silent skip

`FLEX_COUNTER_STATUS` / `POLL_INTERVAL` / `BULK_CHUNK_SIZE` 以外のフィールドは `NOTICE` ログのみ (`flexcounterorch.cpp:395-398`)。

- **挙動**: `NOTICE` 出力のみ。他フィールドの処理は継続
- **復旧**: 不要（設計上の silent skip）

### 5. NULL OID ガード → WARN + silent return

`DashCounter::addToFC()` は `oid == SAI_NULL_OBJECT_ID` の場合 `WARN` を出力して即 return (`dashcounter.h:30-34`)。

- **挙動**: `WARN` ログ + `setCounterIdList` 未呼び出し
- **復旧**: 自動（ENI が有効 OID で再登録された時点で `addToFC` が正常実行）

### 6. `handleStatusUpdate` の冪等ガード → silent no-op

`fc_status` の変化がない場合（`enable` → `enable` 連続等）、`refreshStats` をスキップ (`dashcounter.h:65-70`)。

- **挙動**: no-op。FLEX_COUNTER_DB は変更されない
- **復旧**: 不要（設計上冪等。`enable_counters.py` の再実行でも重複投入なし）

---

## 失敗パターンサマリ

| # | トリガー | ログレベル | FLEX_COUNTER_DB への影響 | 自動回復 | 証拠 |
|---|---------|---------|----------------------|---------|------|
| 1 | warm-reboot 60 秒タイマー未満了 | なし（silent 保留） | なし（m_toSync 保留） | 自動（60 秒後） | flexcounterorch.cpp:156 |
| 2 | `allPortsReady() = false` | なし（silent 保留） | なし（m_toSync 保留） | 自動（PortInitDone 後） | flexcounterorch.cpp:164 |
| 3 | 無効グループキー | NOTICE | なし | なし（再書き込み要） | flexcounterorch.cpp:183 |
| 4 | 未サポートフィールド | NOTICE | なし（他フィールド継続） | 不要 | flexcounterorch.cpp:395 |
| 5 | ENI OID が SAI_NULL_OBJECT_ID | WARN | なし（addToFC 即 return） | 自動（ENI 再登録時） | dashcounter.h:30 |
| 6 | `enable` → `enable` 連続（fc_status 変化なし） | なし（silent no-op） | なし | 不要（冪等設計） | dashcounter.h:65 |
