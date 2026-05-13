# CONFIG_DB 例外条件分析: BUFFER_QUEUE

## Consumer

- `orchagent` の `BufferOrch::doBufferQueueTask`: APPL_DB 経由で各 queue の `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` を更新。

## 例外条件

### 1. key フォーマット不正 → skip
- ソース: `bufferorch.cpp` L158-162 (`initBufferReadyList`)
- key が `<port>|<queue_range>` の 2 トークンでない場合 `SWSS_LOG_ERROR("Wrong format of a table '%s' key '%s'. Skip it")` → continue。

### 2. プロファイル参照未解決 → task_need_retry
- ソース: `bufferorch.cpp` L966-970
- `profile` フィールドに参照する BUFFER_PROFILE が未存在の場合 `SWSS_LOG_INFO("Missing or invalid queue buffer profile reference specified")` → `task_need_retry`。

### 3. プロファイル変更なし → スキップ (task_success)
- ソース: `bufferorch.cpp` L975-985
- profile が変更なく、かつ `m_partiallyAppliedQueues` にキーがない場合 `SWSS_LOG_INFO("Skip setting buffer queue ... since it is not changed")` → `task_success` (SAI 呼び出しなし)。

### 4. queue インデックス範囲外 → task_invalid_entry
- ソース: `bufferorch.cpp` L1063-1065
- 指定インデックスがポートのキュー数を超える場合 `SWSS_LOG_ERROR("Invalid queue index specified:%zd")` → `task_invalid_entry`。VoQ の場合も同様 (`Invalid voq index`)。

### 5. queue ロック中 → task_need_retry (partiallyApplied)
- ソース: `bufferorch.cpp` L1066-1070
- `port.m_queue_lock[ind] == true` の場合 `SWSS_LOG_WARN("Queue ... is locked, will retry")` → `m_partiallyAppliedQueues` に追加して `task_need_retry`。

### 6. zero profile (`_zero_` 含む名前) → flexcounter 登録スキップ
- ソース: `bufferorch.cpp` L1017, L1020
- プロファイル名に `_zero_` が含まれる場合、counter の add/remove を行わない (zero profile はトラフィックなしを意味するため)。

### 7. ポートが未存在 → task_invalid_entry
- ソース: `bufferorch.cpp` L1036-1039
- `gPortsOrch->getPort()` 失敗時 `SWSS_LOG_ERROR("Port with alias:%s not found")` → `task_invalid_entry`。
