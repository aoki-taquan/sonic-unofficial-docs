# debug-counter — Phase D 失敗挙動・retry/recovery スキャンノート

対象テーブル: `DEBUG_COUNTER` / `DEBUG_COUNTER_DROP_REASON` / `DEBUG_DROP_MONITOR`
Consumer: `DebugCounterOrch` (`sonic-swss/orchagent/debugcounterorch.cpp`)
スキャン範囲: 全行精読 (L1-832)

---

## タスクステータスマッピング

`doTask()` は `task_process_status` を返す内部ヘルパーを呼び出し、
`m_toSync` エントリの残留・削除を決定する。

| ステータス | Consumer 動作 | retry |
|---|---|---|
| `task_success` | エントリを `m_toSync` から削除 | なし |
| `task_ignore` | エントリを `m_toSync` から削除（+ SWSS_LOG_WARN） | なし |
| `task_need_retry` | エントリを `m_toSync` に残す（次 doTask() で再試行） | あり（上限なし） |
| `task_failed` | エントリを `m_toSync` から削除（+ SWSS_LOG_ERROR） | なし |

evidence: `debugcounterorch.cpp:285-306`

---

## 1. DEBUG_COUNTER テーブル SET 系

### 1-1. 未サポートカウンタ種別 → `task_failed`

`installDebugCounter()` L387-391:
`supported_counter_types.find(counter_type) == supported_counter_types.end()` の場合、
`SWSS_LOG_ERROR("Specified counter type '%s' is not supported.")` → `task_failed`。

`supported_counter_types` は起動時に `DropCounter::getSupportedCounterTypes()` で
SAI から取得。SAI が `sai_query_attribute_enum_values_capability` に失敗すると空になり、
全 DEBUG_COUNTER 作成が永続的に `task_failed` となる。
evidence: `debugcounterorch.cpp:387-391; drop_counter.cpp:380-384`

### 1-2. `type` フィールドが空文字 / 不正 → `task_failed`

`getDebugCounterType()` L726-758: `type` キーが `getDebugCounterTypeLookup()` に存在しない場合、
`SWSS_LOG_ERROR("Debug counter type '%s' does not exist")` + `throw std::runtime_error`。
`installDebugCounter()` が catch して `task_failed` を返す。
`type` フィールドが CONFIG_DB に含まれない場合は `counter_type` が空文字 → `supported_counter_types` 未ヒット → `task_failed`。
evidence: `debugcounterorch.cpp:748-758, 385-391, 157-163`

### 1-3. SAI runtime_error（カウンタ作成失敗）→ `task_failed`

`createDropCounter()` 内部で `DropCounter` コンストラクタまたは `installDebugFlexCounters()` が
`std::runtime_error` を throw した場合、`doTask()` の catch ブロックが
`SWSS_LOG_ERROR("Failed to create debug counter '%s'")` → `task_failed`。
evidence: `debugcounterorch.cpp:155-163`

### 1-4. counter 既存の場合 → `task_success`（冪等）

`debug_counters.find(counter_name) != debug_counters.end()` の場合、
`SWSS_LOG_DEBUG("Debug counter '%s' already exists")` → `task_success` で即返す。
更新は行われない。`type` / drop_reason の変更には DEL + 再 SET が必要。
evidence: `debugcounterorch.cpp:374-377`

### 1-5. drop_reason が揃う前の counter 作成 → `task_success`（pending）

`free_drop_reasons` に理由がなければ `free_drop_counters` に保留されて `task_success` を返す。
SAI オブジェクトは作成されない。`show dropcounters` には表示されない。
evidence: `debugcounterorch.cpp:393-398`

---

## 2. DEBUG_COUNTER テーブル DEL 系

### 2-1. 存在しない counter の DEL → `task_ignore`

`uninstallDebugCounter()` L404-416: `debug_counters` に見つからず `free_drop_counters` にも
なければ `SWSS_LOG_ERROR("Debug counter %s does not exist")` → `task_ignore`。
evidence: `debugcounterorch.cpp:404-417`

### 2-2. free_drop_counters 状態の counter DEL → `task_ignore`

`free_drop_counters` にある場合は `deleteFreeCounter()` を呼んで `task_ignore` を返す。
SAI オブジェクトは未作成のため SAI 操作なし。
evidence: `debugcounterorch.cpp:407-412`

### 2-3. SAI runtime_error（カウンタ削除失敗）→ `task_failed`

`uninstallDebugFlexCounters()` 内部で `runtime_error` を throw した場合、
`doTask()` の catch ブロックが `SWSS_LOG_ERROR("Failed to delete debug counter '%s'")` → `task_failed`。
evidence: `debugcounterorch.cpp:167-175`

---

## 3. DEBUG_COUNTER_DROP_REASON テーブル SET 系

### 3-1. 無効な drop_reason（not in SAI enum）→ `task_failed`

`addDropReason()` L443-447: `isDropReasonValid(drop_reason)` が false の場合、
`SWSS_LOG_ERROR("Specified drop reason '%s' is invalid.")` → `task_failed`。
evidence: `debugcounterorch.cpp:443-447`

### 3-2. 未サポートな drop_reason（SAI 非対応）→ `task_failed`

L449-453: `supported_ingress_drop_reasons` / `supported_egress_drop_reasons` に未ヒットの場合、
`SWSS_LOG_ERROR("Specified drop reason '%s' is not supported.")` → `task_failed`。
evidence: `debugcounterorch.cpp:449-454`

### 3-3. counter 未存在時の drop_reason 追加 → `task_success`（pending）

`debug_counters.find(counter_name)` が `end()` の場合、`addFreeDropReason()` に蓄積して
`reconcileFreeDropCounters()` を呼ぶ。両方揃えば SAI 作成。`task_success` を返す。
evidence: `debugcounterorch.cpp:456-466`

### 3-4. SAI runtime_error（追加失敗）→ `task_failed`

`createDropCounter()` などが `runtime_error` を throw した場合、
`SWSS_LOG_ERROR("Failed to add drop reason '%s' to counter '%s'")` → `task_failed`。
evidence: `debugcounterorch.cpp:191-198`

---

## 4. DEBUG_COUNTER_DROP_REASON テーブル DEL 系

### 4-1. 最後の drop_reason の削除 → `task_ignore`

`removeDropReason()` L497-500: `drop_reasons.size() <= 1` の場合、
`SWSS_LOG_WARN("Attempted to remove all drop reasons from counter '%s'")` → `task_ignore`。
evidence: `debugcounterorch.cpp:497-501`

### 4-2. 無効な drop_reason DEL → `task_failed`

`removeDropReason()` L483-485: `isDropReasonValid(drop_reason)` が false の場合 → `task_failed`。
evidence: `debugcounterorch.cpp:483-485`

### 4-3. counter 未存在時の drop_reason DEL → `task_success`

`debug_counters` に見つからない場合 `deleteFreeDropReason()` を呼んで `task_success` を返す。
evidence: `debugcounterorch.cpp:488-492`

---

## 5. DEBUG_DROP_MONITOR テーブル

### 5-1. 不正な status 値 → `task_failed`

`"enabled"` / `"disabled"` 以外の値:
`SWSS_LOG_ERROR("The status of drop counter monitor was not recognized: %s.")` → `task_failed`。
evidence: `debugcounterorch.cpp:256-259`

### 5-2. 不正な config_name → `task_failed`

`"status"` 以外のキー:
`SWSS_LOG_ERROR("Config for drop counter monitor was not recognized: %s.")` → `task_failed`。
evidence: `debugcounterorch.cpp:262-265`

---

## 6. retry なし（`task_need_retry` 未使用）の確認

`debugcounterorch.cpp` の全コードをスキャンした結果、`task_need_retry` を返す箇所は存在しない。
依存解決の失敗（counter 未存在時の drop_reason 追加など）はすべて `task_success`（pending）か
`task_failed` で処理され、自動 retry は実装されていない。
orchagent 再起動時は CONFIG_DB の全エントリを replay して `reconcileFreeDropCounters()` で自動復元する。
evidence: 全コードスキャン完了
