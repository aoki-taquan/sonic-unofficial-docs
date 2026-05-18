# state-flex-counter — Phase D 失敗挙動メモ

## 調査対象ソース
- sonic-sairedis/syncd/FlexCounter.cpp
- sonic-swss/orchagent/flexcounterorch.cpp

## 失敗パターン一覧

### 1. FLEX_COUNTER_STATUS 不正値
`FlexCounter::setStatus()` は `statusMap.find(status)` が `cend()` を返した場合
`SWSS_LOG_WARN` のみで `m_enable` を変更しない (FlexCounter.cpp:3082-3084)。
FLEX_COUNTER_DB には不正値がそのまま残るが、ポーリング動作は変化しない。

### 2. allPortsReady() 未到達
`FlexCounterOrch::doTask()` L164-167 でガード。PortsOrch が未準備なら
CONFIG_DB イベント全体を silent defer (m_toSync に残留)。
FLEX_COUNTER_DB への書き込みは一切行われない。

### 3. SAI getStats() 失敗（単体）
`collectData()` 内: `m_vendorSai->getStats()` が `SAI_STATUS_SUCCESS` 以外を返すと
`return false`。該当 OID の COUNTERS_DB エントリは更新されず stale のまま残留。
`SWSS_LOG_ERROR` のみ (FlexCounter.cpp:1252-1256)。

### 4. SAI bulkGetStats() 失敗
`bulkCollectData()` 内: `bulkGetStats()` の戻り値が非 SUCCESS → `SWSS_LOG_WARN`。
その後 per-object `ctx.object_statuses[i]` をチェックし、失敗オブジェクトは
COUNTERS_DB への書き込みをスキップ (`continue`) (FlexCounter.cpp:1341, 1363)。

### 5. BULK_CHUNK_SIZE 不正値
`stoi(value)` が例外を投げると `catch(...)` で捕捉し `SWSS_LOG_ERROR`。
bulkChunkSize は変更されず 0 のまま (FlexCounter.cpp:3181)。

### 6. 未サポートフィールド
GROUP_TABLE に未知フィールドが届いた場合 `SWSS_LOG_ERROR("Field is not supported %s")`
を出力し無視 (FlexCounter.cpp:3236)。FLEX_COUNTER_DB や COUNTERS_DB は変化しない。

### 7. warm-reboot 時 60 秒遅延中の CONFIG_DB 更新
`m_delayTimerExpired == false` の間は doTask() が即 return。
CONFIG_DB の FLEX_COUNTER_TABLE 更新は m_toSync に滞留し
タイマー満了（または cold-start 時の即時フラグ）後に一括処理される。
(flexcounterorch.cpp:44,127-136,155-158)

## COUNTERS_DB への影響まとめ
- SAI 単体 getStats 失敗 → 該当 OID エントリが stale（前回値が残存）
- SAI bulk getStats 失敗 → 失敗 OID はスキップ、成功 OID は更新
- STATUS 不正値 / フィールド不正 → COUNTERS_DB 変化なし（ポーリング継続または停止）
- allPortsReady 未達 → FLEX_COUNTER_DB 未更新、ポーリング自体が起動しない
