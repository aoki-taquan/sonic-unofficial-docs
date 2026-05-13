# CONFIG_DB 例外条件分析: DEBUG_COUNTER

## Consumer

- `orchagent` の `DebugCounterOrch`: DEBUG_COUNTER テーブルと `DEBUG_COUNTER|DROP_REASON` テーブルを subscribe。SAI drop counter オブジェクトを生成・管理し、flex counter で計測。

## 例外条件

### 1. allPortsReady 未到達 → 全更新ペンディング
- ソース: `debugcounterorch.cpp` L137-140
- `gPortsOrch->allPortsReady()` が false の間は doTask() が即リターン。ポート初期化完了まで全 DEBUG_COUNTER 更新が保留。

### 2. 未サポートカウンタ種別 → task_failed
- ソース: `debugcounterorch.cpp` L389
- `counter_type` が `supported_counter_types` に含まれない場合 `SWSS_LOG_ERROR("Specified counter type '%s' is not supported.")` → `task_failed`。

### 3. 無効な drop_reason → task_failed
- ソース: `debugcounterorch.cpp` L445
- `isDropReasonValid()` が false の場合 `SWSS_LOG_ERROR("Specified drop reason '%s' is invalid.")` → `task_failed`。

### 4. 未サポートな drop_reason → task_failed
- ソース: `debugcounterorch.cpp` L451-453
- ingress / egress どちらの `supported_*_drop_reasons` にも含まれない場合 `SWSS_LOG_ERROR("Specified drop reason '%s' is not supported.")` → `task_failed`。

### 5. counter 未存在への drop_reason 追加 → free_drop_counters で保留
- ソース: `debugcounterorch.cpp` L460-465
- DEBUG_COUNTER エントリよりも先に DROP_REASON 更新が来た場合、`free_drop_reasons` に保存し、後で counter 作成時に `reconcileFreeDropCounters()` で適用 (順序非依存)。

### 6. 最後の drop_reason の削除 → task_ignore
- ソース: `debugcounterorch.cpp` L476-479
- drop_reasons が 1 件のときに `removeDropReason()` を呼ぶと `SWSS_LOG_WARN("Attempted to remove all drop reasons from counter")` → `task_ignore` (drop counter は最低 1 つの理由が必要)。

### 7. 不明テーブル名 → エラーログ + task_ignore
- ソース: `debugcounterorch.cpp` L282
- 認識されないテーブル名の更新が来た場合 `SWSS_LOG_ERROR("Received update from unknown table")` → `task_ignore`。

### 8. 更新はべき等
- ソース: `debugcounterorch.cpp` L128-130
- 失敗した更新はシステム状態を変更しない (atomic-like)。同一リクエストの繰り返しは同一結果。
