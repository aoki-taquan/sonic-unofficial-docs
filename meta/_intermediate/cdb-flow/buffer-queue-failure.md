# BUFFER_QUEUE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-buffer-queue)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-net/sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-net/sonic-swss/orchagent/bufferorch.cpp`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| key トークン数不正（非 VOQ: 2 個以外） | `bufferorch.cpp processBufferQueue()` L943-946 | `task_invalid_entry` 返却・SAI 未呼び出し | LOG_ERROR "malformed key: Must contain 2 tokens" | `bufferorch.cpp:943-946` |
| key トークン数不正（VOQ: 4 個以外） | `bufferorch.cpp processBufferQueue()` L918-921 | `task_invalid_entry` 返却・SAI 未呼び出し | LOG_ERROR "malformed key: Must contain 4 tokens" | `bufferorch.cpp:918-921` |
| queue index 範囲パース失敗（`parseIndexRange` 失敗） | `bufferorch.cpp processBufferQueue()` L925-927, L950-952 | `task_invalid_entry` 返却（VOQ / 非 VOQ 共通） | なし | `bufferorch.cpp:925-927, 950-952` |
| `BUFFER_PROFILE` 参照が未解決 (`not_resolved`) | `bufferorch.cpp processBufferQueue()` L964-969 | `task_need_retry` 返却・SAI 未呼び出し。`orchagent` は再試行キューに投入 | LOG_INFO "Missing or invalid queue buffer profile reference specified" | `bufferorch.cpp:966-969` |
| `BUFFER_PROFILE` 参照解決が上記以外のエラー | `bufferorch.cpp processBufferQueue()` L972-973 | `task_failed` 返却（致命的失敗・再試行なし） | LOG_ERROR "Resolving queue profile reference failed" | `bufferorch.cpp:972-973` |
| PORT が `gPortsOrch` に未登録（ポート未初期化） | `bufferorch.cpp processBufferQueue()` L1033-1036 | `task_invalid_entry` 返却 | LOG_ERROR "Port with alias:xxx not found" | `bufferorch.cpp:1033-1036` |
| queue index がポートの queue 数を超過（非 VOQ） | `bufferorch.cpp processBufferQueue()` L1061-1064 | `task_invalid_entry` 返却 | LOG_ERROR "Invalid queue index specified" | `bufferorch.cpp:1061-1064` |
| queue index が VoQ 数を超過（VOQ シャーシ） | `bufferorch.cpp processBufferQueue()` L1052-1055 | `task_invalid_entry` 返却 | LOG_ERROR "Invalid voq index specified" | `bufferorch.cpp:1052-1055` |
| queue がロック中 (`port.m_queue_lock[ind] == true`) | `bufferorch.cpp processBufferQueue()` L1066-1070 | `task_need_retry` 返却・`m_partiallyAppliedQueues` に登録。ロック解除後に再適用 | LOG_WARN "Queue X on port Y is locked, will retry" | `bufferorch.cpp:1066-1070` |
| SAI set 失敗 (`sai_queue_api->set_queue_attribute` != SUCCESS) | `bufferorch.cpp processQueuePost()` L1124-1130 | `handleSaiSetStatus(SAI_API_QUEUE, sai_status)` 結果に応じて `task_success` / `task_need_retry` / `task_failed` | LOG_ERROR "Failed to set queue's buffer profile attribute" | `bufferorch.cpp:1124-1130` |
| `buffermgrdyn`: key に port パートが空（`parseObjectNameFromKey` 失敗） | `buffermgrdyn.cpp handleBufferObjectTables()` L3510-3513 | `task_invalid_entry` 返却 | LOG_ERROR "Invalid key format X for BUFFER_QUEUE table" | `buffermgrdyn.cpp:3510-3513` |
| `buffermgrdyn`: key に ids パートが空（queue range 欠損, `keyWithIds=true`） | `buffermgrdyn.cpp handleBufferObjectTables()` L3517-3523 | `task_invalid_entry` 返却 | LOG_ERROR "Invalid key format X for BUFFER_QUEUE table" | `buffermgrdyn.cpp:3517-3523` |
| `buffermgrdyn`: 複数ポートリスト展開時に単一ポートハンドラが `task_need_retry` | `buffermgrdyn.cpp handleBufferObjectTables()` L3546-3547 | 即座に `task_need_retry` を返却・残ポートの処理を打ち切り | なし（個別ハンドラのログに依存） | `buffermgrdyn.cpp:3546-3547` |
| `buffermgrdyn`: 動的バッファ計算中にポートが未準備 (`PORT_READY` 以外) | `buffermgrdyn.cpp` L1485-1488 | 当該 PG/queue エントリをスキップ（continue）・再試行はポート準備後にトリガ | LOG_INFO "Nothing to be done for X since port is not ready" | `buffermgrdyn.cpp:1485-1488` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 時に key が `APP_BUFFER_QUEUE_TABLE` に存在しない | `bufferorch.cpp processBufferQueue()` L1000-1003 | SAI 呼び出しをスキップ（`need_update_sai = false`）・`task_success` 返却 | LOG_INFO "X doesn't not exist, don't need to notify SAI" | `bufferorch.cpp:1000-1003` |
| DEL 時の SAI set 失敗（`SAI_NULL_OBJECT_ID` セット失敗） | `bufferorch.cpp processQueuePost()` L1124-1130 | `handleSaiSetStatus` に委譲 | LOG_ERROR "Failed to set queue's buffer profile attribute" | `bufferorch.cpp:1124-1130` |
| 不明 op コマンド (SET / DEL 以外) | `bufferorch.cpp processBufferQueue()` L1012-1014 | `task_invalid_entry` 返却 | LOG_ERROR "Unknown operation type X" | `bufferorch.cpp:1012-1014` |

### VOQ シャーシ固有の制約

| 条件 | 挙動 | evidence |
|---|---|---|
| VOQ モード時: FlexCounter（queue buffer counter）の追加・削除をスキップ | VOQ では `flexcounterorch` が全 system port / front panel port の queue counter を管理するため、`BUFFER_QUEUE` 変更時の per-queue counter 操作は行わない | `bufferorch.cpp:1134-1136` |
| VOQ モード時: `m_port_ready_list_ref` の初期化ソースが CONFIG_DB（非 VOQ は APPL_DB） | admin-down ポートを ready-list に含めず、初期化待ちのポートを正確に追跡 | `bufferorch.cpp:132-140` |

### 検出ロジック補足

- **`m_partiallyAppliedQueues`**: queue ロック (`m_queue_lock`) 中に `task_need_retry` を返した queue key を保持する集合。ロック解除後のポーリングで再処理される。同一 key で profile 変更がなくても `m_partiallyAppliedQueues` に登録があれば SAI 更新を強制する（`bufferorch.cpp:979-986`）。
- **`task_invalid_entry` と `task_failed` の違い**: `task_invalid_entry` はエントリ自体が不正（永続的な失敗）でキューから破棄される。`task_failed` は予期しない内部エラーで orchagent が致命的として扱う場合がある。`task_need_retry` のみが再投入対象。
- **SAI 呼び出しの bulk 化**: `processBufferQueue` はキューへの `m_queueBulk[op].emplace_back(task)` で一旦バッファし、`processQueuePost` で実際の SAI 呼び出し結果を評価する 2 段構成。SAI 失敗は `processQueuePost` 側で検出される（`bufferorch.cpp:1099-1131`）。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `task_need_retry`（processBufferQueue 内） | 2 | `bufferorch.cpp:969, 1070` |
| `task_invalid_entry`（processBufferQueue 内） | 6 | `bufferorch.cpp:921, 927, 946, 952, 1036, 1055, 1064` |
| `task_failed`（processBufferQueue 内） | 1 | `bufferorch.cpp:973` |
| `task_invalid_entry`（buffermgrdyn handleBufferObjectTables 内） | 2 | `buffermgrdyn.cpp:3513, 3523` |
| `task_need_retry`（buffermgrdyn multi-port loop） | 1 | `buffermgrdyn.cpp:3546-3547` |
| LOG_WARN "locked, will retry" | 1 | `bufferorch.cpp:1068` |
| `m_partiallyAppliedQueues` insert | 1 | `bufferorch.cpp:1069` |

<!-- /failure -->
