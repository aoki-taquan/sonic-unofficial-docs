# counter-buffer — Phase D: 失敗挙動スキャンノート

対象スラグ: `counter-buffer`
調査日: 2026-05-17 (chore/q67-f-counters-misc2-next)
スキャン対象:
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/watermarkorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/flexcounterorch.cpp`

---

## Phase D: 失敗挙動マトリクス

### bufferorch — BUFFER_POOL SET 処理の失敗経路

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `type` フィールドが `ingress`/`egress` 以外 | `task_invalid_entry`（恒久スキップ） | `SWSS_LOG_ERROR "Unknown pool type specified: ..."` | `bufferorch.cpp:457-458` |
| `mode` フィールドが `static`/`dynamic`/`fallback` 以外 | `task_invalid_entry` | `SWSS_LOG_ERROR "Unknown pool mode specified: ..."` | `bufferorch.cpp:484-485` |
| SAI `set_buffer_pool_attribute` で `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` | `task_ignore`（silent skip） | `SWSS_LOG_NOTICE "Buffer pool SET ... not implemented. Ignoring it"` | `bufferorch.cpp:507-509` |
| SAI `set_buffer_pool_attribute` でその他エラー | `handleSaiSetStatus()` 経由（通常 `task_need_retry`） | `SWSS_LOG_ERROR "Failed to modify buffer pool, name: ..."` | `bufferorch.cpp:513-517` |
| SAI `create_buffer_pool` でエラー | `handleSaiCreateStatus()` 経由（通常 `task_need_retry`） | `SWSS_LOG_ERROR "Failed to create buffer pool ... rv:%d"` | `bufferorch.cpp:530-534` |
| 削除対象プールが他テーブルから参照中 | `task_need_retry`・`m_pendingRemove=true` にセット | `SWSS_LOG_NOTICE "Can't remove object ... due to being referenced"` | `bufferorch.cpp:561-567` |
| SAI `remove_buffer_pool` でエラー | `handleSaiRemoveStatus()` 経由 | `SWSS_LOG_ERROR "Failed to remove buffer pool ... rv:%d"` | `bufferorch.cpp:573-578` |
| 未知の operation type | `task_invalid_entry` | `SWSS_LOG_ERROR "Unknown operation type ..."` | `bufferorch.cpp:593-594` |

### bufferorch — BUFFER_PROFILE SET 処理の失敗経路

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `buffer_pool_field_name` 参照先未作成 (`not_resolved`) | `task_need_retry`（自動リトライ） | `SWSS_LOG_INFO "Missing or invalid pool reference specified"` | `bufferorch.cpp:648-651` |
| プール参照解決で内部エラー | `task_failed`（恒久スキップ） | `SWSS_LOG_ERROR "Resolving pool reference failed"` | `bufferorch.cpp:652` |
| numeric フィールド (`size`/`xon`/`xoff` 等) のパース失敗 | `task_failed` | `SWSS_LOG_ERROR "Failed to parse buffer profile ... invalid value ..."` | `bufferorch.cpp:740-743` |
| `mode` フィールドが `static`/`dynamic`/`fallback` 以外 | `task_failed` | `SWSS_LOG_ERROR "Failed to process buffer profile ... unknown mode ..."` | `bufferorch.cpp:759-763` |
| SAI `set_buffer_profile_attribute` でエラー | `handleSaiSetStatus()` 経由 | `SWSS_LOG_ERROR "Failed to modify buffer profile, name: ..., will retry once"` | `bufferorch.cpp:791-804` |
| SAI `create_buffer_profile` でエラー | `handleSaiCreateStatus()` 経由 | `SWSS_LOG_ERROR "Failed to create buffer profile ... rv:%d"` | `bufferorch.cpp:805-811` |
| 削除対象プロファイルが参照中 | `task_need_retry` | `SWSS_LOG_NOTICE "Can't remove object ... due to being referenced"` | `bufferorch.cpp:843` |

### watermarkorch — 設定更新の失敗経路

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `WATERMARK_TABLE` 以外のキーを受信 | 処理なし（silent skip） | なし | `watermarkorch.cpp:93-116` |
| `interval` 以外のフィールドを受信 | 警告ログのみ・処理継続 | `SWSS_LOG_WARN "Unsupported key: ..."` | `watermarkorch.cpp:110` |
| DEL 操作を受信 | 警告ログのみ・DEL は無視 | `SWSS_LOG_WARN "Unsupported op ..."` | `watermarkorch.cpp:83` |
| 不明 op を受信 | 警告ログのみ | `SWSS_LOG_ERROR "Unknown operation type ..."` | `watermarkorch.cpp:87` |
| 不明 clear request data を受信 | 警告のみ・ウォーターマーク更新なし | `SWSS_LOG_WARN "Unknown watermark clear request data: ..."` | `watermarkorch.cpp:228` |

### watermarkorch — ウォーターマーク clear request の失敗経路

| 失敗条件 | 結果 | evidence |
|----------|------|----------|
| 不明な clear op (`op` が `PERIODIC`/`PERSISTENT`/`USER` 以外) | 警告のみ・クリア実行なし | `watermarkorch.cpp:180` |
| クリア対象キーが COUNTERS_DB に存在しない | `HSET "0"` で新規作成（実質無害） | `watermarkorch.cpp:329` |

### bufferorch — Lua plugin 登録失敗

| 失敗条件 | 結果 | ログ | evidence |
|----------|------|------|----------|
| `watermark_bufferpool.lua` ロード失敗（`runtime_error`） | 例外を catch して継続・Lua plugin 未登録のままポーリング開始 | `SWSS_LOG_ERROR "Buffer pool watermark lua script ... not set successfully. Runtime error: ..."` | `bufferorch.cpp:242-244` |

!!! warning "Lua plugin ロード失敗の無音継続"
    `initFlexCounterGroupTable()` で lua スクリプトのロードが `runtime_error` を投げた場合、catch して `SWSS_LOG_ERROR` を出力した後、処理を継続する。この場合 `BUFFER_POOL_WATERMARK_STAT_COUNTER` グループにはプラグイン SHA が登録されず、syncd は raw SAI 値を書くが Lua による `max()` 集計は機能しない。ウォーターマーク値が PERIODIC/PERSISTENT/USER_WATERMARKS テーブルに書かれないことになる（`COUNTERS:<oid>` 直値のみ）。

### portsorch — SAI 能力照会失敗時の WRED フォールバック

| 失敗条件 | 結果 | evidence |
|----------|------|----------|
| `sai_query_stats_capability()` が `SAI_STATUS_NOT_SUPPORTED` を返す | `wred_queue_stat_ids` を空にして syncd 登録をスキップ。WRED カウンタが全グループで収集されない | `portsorch.cpp:1882-1909` |
| `sai_query_stats_capability()` が成功するが特定フィールドが未サポート | そのフィールドのみ除外。その他は通常どおり | `portsorch.cpp:1895-1905` |

### portsorch — SAI 能力照会失敗時の Buffer Pool クリア能力フォールバック

| 失敗条件 | 結果 | evidence |
|----------|------|----------|
| `sai_buffer_api->clear_buffer_pool_stats()` が `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` を返す | 当該プールのクリアフラグをオフ (`noWmClrCapability |= bitMask`)。`StatsMode` を `READ_AND_CLEAR` にセットしない | `bufferorch.cpp:318-326` |
| 全プールでクリア未対応の場合 | グループ全体が `READ` モード（ウォーターマーク値は単調増加し続ける） | `bufferorch.cpp:332-335` |
| 一部プールのみクリア未対応の場合 | 該当プールのみ per-key `stats_mode=read` を設定。他プールは READ_AND_CLEAR | `bufferorch.cpp:338-356` |

---

## retry パターンサマリ

| ステータス | 代表トリガー | 挙動 |
|------------|------------|------|
| `task_need_retry` | プール/プロファイル参照先未作成、削除対象が参照中、SAI 一時失敗 | `m_toSync` に残し次 `doTask()` で自動再試行。上限なし |
| `task_invalid_entry` | フィールド値不正（type/mode 不明、malformed key） | エントリ削除。retry なし |
| `task_failed` | 参照解決内部エラー、パース失敗、不整合な構成 | エントリ削除。retry なし |
| `task_ignore` | SAI_STATUS_ATTR_NOT_IMPLEMENTED_0（SET 非対応属性） | エントリ削除、エラー扱いなし |

---

## 証跡概要

- `bufferorch.cpp` L400-594 (processBufferPool), L596-886 (processBufferProfile), L2040-2099 (doTask) 精読
- `watermarkorch.cpp` L75-93, L100-116, L160-240, L325-335 精読
- `portsorch.cpp` L1882-1909 (WRED 能力照会), L4779 (isPortReady) 精読
- `flexcounterorch.cpp` L164-169 (allPortsReady guard) 精読
