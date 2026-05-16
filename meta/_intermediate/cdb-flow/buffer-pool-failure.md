# BUFFER_POOL — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-buffer-pool)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `cfgmgr/buffermgr.cpp`, `orchagent/bufferorch.cpp`

### buffermgrdyn — handleBufferPoolTable() 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `xoff` フィールドが `ingress_lossless_pool` 以外のプールに設定 | `handleBufferPoolTable()` L2623-2625 | `xoff` を無視し APPL_DB 書き込みはスキップしない（他フィールドは正常処理） | `LOG_ERROR("Field xoff is supported for %s only...")` | `buffermgrdyn.cpp:2625` |
| SHP 有効化時に SAI がまだ準備できていない (`isSharedHeadroomPoolEnabledInSai()` が false) | `handleBufferPoolTable()` L2573-2576 | `task_need_retry` → Consumer ループが再試行 (backoff あり) | なし (NOTICE ログが上位で出力) | `buffermgrdyn.cpp:2573-2576` |
| SHP 変更後にプロファイルの SAI 同期が未完 (`checkPendingProfilesSyncStatus()`) | `handleBufferPoolTable()` L2603-2607 | `task_need_retry` → `m_configuredSharedHeadroomPoolSize` をロールバックして再試行 | `SWSS_LOG_NOTICE("Retry mode: checking pending profiles")` | `buffermgrdyn.cpp:2583-2607` |
| `op` が `SET`/`DEL` 以外 | `handleBufferPoolTable()` L2665 | `task_invalid_entry` → Consumer が当該エントリを廃棄 | `LOG_ERROR("Unknown operation type %s")` | `buffermgrdyn.cpp:2665` |

### buffermgrdyn — Lua plugin ロード失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `loadLuaScript()` / `loadRedisScript()` が例外 (dynamic buffer model 初期化時) | コンストラクタ L106-123 | `buffermgrd` が起動を中断 (`return`) → buffer 管理デーモンが機能しない | `LOG_ERROR("Lua scripts for buffer calculation were not loaded successfully, buffermgrd won't start")` | `buffermgrdyn.cpp:121` |

### buffermgrdyn — updateBufferPoolFromLuaPlugin() 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| Lua plugin が返した `xoff` 値が MMU サイズを超過 | `updateBufferPoolFromLuaPlugin()` L755-758 | xoff 更新をスキップ (pool size は更新継続) | `LOG_ERROR("Buffer pool %s: Invalid xoff %s, exceeding the mmu size %s, ignored xoff but the pool size will be updated")` | `buffermgrdyn.cpp:757-758` |
| Lua plugin が返した pool `size` 値が MMU サイズを超過 | `updateBufferPoolFromLuaPlugin()` L786-790 | pool サイズ更新をスキップ (`continue`) → APPL_DB は前値のまま | `LOG_ERROR("Buffer pool %s: Invalid size %s, exceeding the mmu size %s")` | `buffermgrdyn.cpp:788-790` |
| 共有バッファプールが未設定の状態で headroom 計算を要求 | `updateBufferPoolFromLuaPlugin()` L684 | headroom 計算をスキップ (silent) | `SWSS_LOG_NOTICE("No shared buffer pool configured")` | `buffermgrdyn.cpp:684` |

### bufferorch — processBufferPool() 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| pool が `m_pendingRemove` フラグ立ちの状態で SET | `processBufferPool()` L407-410 | `task_need_retry` | `SWSS_LOG_NOTICE("Entry %s %s is pending remove, need retry")` | `bufferorch.cpp:409-410` |
| pool `type` フィールドの値が `ingress`/`egress`/`both` 以外 | `processBufferPool()` L457-458 | `task_invalid_entry` → エントリ廃棄 | `LOG_ERROR("Unknown pool type specified:%s")` | `bufferorch.cpp:457-458` |
| pool `mode` フィールドの値が `static`/`dynamic` 以外 | `processBufferPool()` L484-485 | `task_invalid_entry` → エントリ廃棄 | `LOG_ERROR("Unknown pool mode specified:%s")` | `bufferorch.cpp:484-485` |
| 不明フィールド (`percentage` 等) が APPL_DB の pool エントリに含まれる | `processBufferPool()` L499 | フィールドをスキップ (SAI 非反映) → 処理継続 | `LOG_ERROR("Unknown pool field specified:%s, ignoring")` | `bufferorch.cpp:499` |
| SAI `set_buffer_pool_attribute` が `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` | `processBufferPool()` L508-511 | `task_ignore` → ハードウェア非反映のまま成功扱い | `SWSS_LOG_NOTICE("...not implemented. Ignoring it")` | `bufferorch.cpp:508-511` |
| SAI `set_buffer_pool_attribute` がその他エラー | `processBufferPool()` L513-519 | `handleSaiSetStatus()` に委譲 → 通常 `task_need_retry` or `task_failed` | `LOG_ERROR("Failed to modify buffer pool...")` | `bufferorch.cpp:515-519` |
| SAI `create_buffer_pool` 失敗 | `processBufferPool()` L528-535 | `handleSaiCreateStatus()` に委譲 → 通常 `task_need_retry` | `LOG_ERROR("Failed to create buffer pool %s...")` | `bufferorch.cpp:530-534` |
| DEL 時に pool がまだ参照されている | `processBufferPool()` L560-566 | `m_pendingRemove = true` → `task_need_retry` | `SWSS_LOG_NOTICE("Can't remove object %s due to being referenced (%s)")` | `bufferorch.cpp:563-566` |
| SAI `remove_buffer_pool` 失敗 | `processBufferPool()` L573-579 | `handleSaiRemoveStatus()` に委譲 | `LOG_ERROR("Failed to remove buffer pool %s...")` | `bufferorch.cpp:575-578` |
| `op` が `SET`/`DEL` 以外 | `processBufferPool()` L593 | `task_invalid_entry` | `LOG_ERROR("Unknown operation type %s")` | `bufferorch.cpp:593` |

### bufferorch — watermark capability 検出失敗

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `clear_buffer_pool_stats` が `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` | `generateBufferPoolWatermarkCounterIdList()` L322-325 | `noWmClrCapability` ビットセット → 該当 pool の watermark clear を永続的にスキップ (FLEX_COUNTER で `READ` モードのまま) | `SWSS_LOG_NOTICE("Clear watermark failed on %s, rv: %s")` | `bufferorch.cpp:322-325` |
| `loadLuaScript("watermark_bufferpool.lua")` が `runtime_error` | `initFlexCounterGroupTable()` L239-244 | watermark Lua plugin がロードされず FLEX_COUNTER_GROUP が未設定 → watermark 統計が収集されない | `LOG_ERROR("Buffer pool watermark lua script...not set successfully. Runtime error: %s")` | `bufferorch.cpp:244` |

### buffermgr (static model) — 失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| Consumer ループで `task_invalid_entry` | `doTask()` L578-586 | `LOG_ERROR("Failed to process invalid entry, drop it")` → エントリ廃棄 | `LOG_ERROR` | `buffermgr.cpp:585-586` |
| Consumer ループで `task_failed` | `doTask()` L578-586 | `LOG_ERROR("Failed to process table update")` → ループ継続 | `LOG_ERROR` | `buffermgr.cpp:579-580` |

### リトライ・廃棄の判断フロー

```
processBufferPool() / handleBufferPoolTable()
  ↓
  task_need_retry  → Consumer が backoff 後に再試行 (例: SAI pending remove, SHP SAI sync 待ち)
  task_invalid_entry → Consumer が当該エントリを廃棄 (例: 不明な op / type / mode)
  task_ignore      → bufferorch が当該 SET を成功扱いで無視 (例: SAI_STATUS_ATTR_NOT_IMPLEMENTED_0)
  task_success     → 正常完了
```

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `task_need_retry` (BUFFER_POOL 関連) | 6 | `buffermgrdyn.cpp:2575, 2587, 2607; bufferorch.cpp:410, 566` + buffermgr.cpp |
| `task_invalid_entry` (BUFFER_POOL 関連) | 4 | `bufferorch.cpp:458, 485, 594; buffermgrdyn.cpp:2666` |
| `task_ignore` | 1 | `bufferorch.cpp:511` |
| `LOG_ERROR` (BUFFER_POOL 直接) | 9 | buffermgrdyn.cpp:757, 788; buffermgr.cpp:579, 585; bufferorch.cpp:457, 484, 499, 515, 530, 575 |
| Lua plugin ロード失敗 | 2 | buffermgrdyn.cpp:121; bufferorch.cpp:244 |

<!-- /failure -->
