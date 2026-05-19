# pg-watermark failure-behavior (Phase D) — 調査メモ

## 調査対象

- `sonic-swss/orchagent/flexcounterorch.cpp` — `FlexCounterOrch::doTask(Consumer&)`
- `sonic-swss/orchagent/portsorch.cpp` — `addPriorityGroupWatermarkFlexCounters()`, `addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex()`, `createPortBufferPgCounters()`

## 主な失敗パターン

### 1. 遅延タイマー未満了による処理スキップ

`FlexCounterOrch::doTask()` 冒頭で `m_delayTimerExpired` を確認（`flexcounterorch.cpp:156-159`）。
タイマーが満了していない間は Consumer::m_toSync への蓄積のみ行われ、即座に return する。
エントリは消費されず次回 doTask() で再処理される。

### 2. allPortsReady 未成立による処理スキップ

`gPortsOrch->allPortsReady()` / `gFabricPortsOrch->allPortsReady()` が false の間は return（`flexcounterorch.cpp:164-172`）。
PG_WATERMARK の enable SET は m_toSync に残り、全ポート初期化完了後に自動再処理される。

### 3. 不正なグループキー — サイレント廃棄

`flexCounterGroupMap.count(key) == 0` の場合（`flexcounterorch.cpp:183-188`）:
```
SWSS_LOG_NOTICE("Invalid flex counter group input, %s", key.c_str());
consumer.m_toSync.erase(it++);
```
`FLEX_COUNTER_TABLE` に `PG_WATERMARK` 以外のキーが来た場合はサイレント廃棄。
PG_WATERMARK は `flexCounterGroupMap` に登録済み（`flexcounterorch.cpp:79`）なので正常キーには該当しない。

### 4. 未知フィールド — サイレント廃棄

`POLL_INTERVAL_FIELD`、`BULK_CHUNK_SIZE_FIELD`、`BULK_CHUNK_SIZE_PER_PREFIX_FIELD`、`FLEX_COUNTER_STATUS_FIELD` 以外のフィールドは:
```
SWSS_LOG_NOTICE("Unsupported field %s", field.c_str());
```
（`flexcounterorch.cpp:397`）でログのみ、エントリは破棄されず NOTICE ログのみ。

### 5. FLEX_COUNTER_STATUS が "enable"/"disable" 以外

`value == "enable"` のみで分岐（`flexcounterorch.cpp:235`）。それ以外の値は enable ブロックも disable ブロックも実行されず、`setFlexCounterGroupOperation()` のみが呼ばれてフィールド値がそのまま FlexCounter に転送される。syncd 側でのバリデーション依存。

### 6. BUFFER_PG 未設定時の OID 不登録

`addPriorityGroupWatermarkFlexCounters()` は `getPgConfigurations()` で取得した BUFFER_PG エントリに基づき処理を行う（`portsorch.cpp:8998-9052`）。BUFFER_PG テーブルが空の場合はループ対象がなく FlexCounter への OID 登録がスキップされる（エラーなし・サイレント）。後から BUFFER_PG を追加すると `createPortBufferPgCounters()` 内で `getPgWatermarkCountersState()` が true であれば OID 登録が行われる（`portsorch.cpp:8930-8933`）。

### 7. DEL 操作の挙動

`FLEX_COUNTER_TABLE|PG_WATERMARK` の DEL（削除）は `flexcounterorch.cpp` の doTask() では処理されない。
DEL は `consumer.m_toSync.erase(it++)` で消費されるが、`FLEX_COUNTER_STATUS = disable` と等価の処理（`clearCounterIdList()`）は実行されない。
disable の場合は `setFlexCounterGroupOperation(group, "disable")` が呼ばれ、syncd FlexCounter グループが非活性化される。

## 結論

FlexCounterOrch の PG_WATERMARK ハンドラには `task_need_retry` 相当の明示的 retry 機構はなく、
起動ガード（delay timer / allPortsReady）を超えた後は処理が即座に確定する。
失敗のほとんどは「サイレントスキップ」であり STATE_DB への ERROR_TABLE 書き込みもない。
