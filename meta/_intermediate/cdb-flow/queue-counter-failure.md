# queue-counter Phase D — 失敗挙動調査メモ

調査日: 2026-05-18
対象: COUNTERS_DB QUEUE カウンタ（portsorch + flexcounterorch）

## 調査対象コード

- `sonic-swss/orchagent/portsorch.cpp` (ref:4305596156d7)
- `sonic-swss/orchagent/flexcounterorch.cpp` (ref:4305596156d7)

## 失敗経路一覧

### A. SAI Queue OID フェッチ失敗 (`initializeQueuesBulk`)

`initializeQueuesBulk()` (portsorch.cpp:6854) は 2 段階バルク操作:
1. `SAI_PORT_ATTR_QOS_NUMBER_OF_QUEUES` の bulk GET
2. `SAI_PORT_ATTR_QOS_QUEUE_LIST` の bulk GET

どちらかが `SAI_STATUS_SUCCESS` 以外を返した場合:
- `handleSaiGetStatus(SAI_API_PORT, status)` を呼んでから
- `throw runtime_error("PortsOrch initialization failure.")` を投げる

この例外は `PortsOrch` コンストラクタから `orchestrator` 層まで伝播し、orchagent プロセスが abort する。systemd が再起動。

ポートの Queue OID リストが存在しない場合: `port.m_queue_ids.size() == 0` なら QUEUE_LIST バルク GET をスキップ（続行）。

### B. FlexCounter グループ初期化の runtime_error

`portsorch.cpp:820-840` の try-catch ブロック:
- `PortsOrch` コンストラクタで FlexCounter グループ（`setFlexCounterGroupPollInterval` 等）設定時に `runtime_error` が発生しうる
- catch して `SWSS_LOG_ERROR("Port flex counter groups were not set successfully: %s", e.what())` を記録
- **例外を飲み込んで継続**。FlexCounter グループが不完全な状態で起動する可能性がある

### C. create_only_config_db_buffers 読み込み失敗

`flexcounterorch.cpp:120-125`:
- `DEVICE_METADATA|localhost` から `create_only_config_db_buffers` を読み込む際の `system_error` はキャッチして `SWSS_LOG_ERROR` 記録後継続
- フォールバック: `m_createOnlyConfigDbBuffers = false`（全キューカウンタ有効）
- **CONFIG_DB 読み込み失敗でも orchagent は落ちない**

### D. BUFFER_QUEUE キー解析失敗

`flexcounterorch.cpp:555-605` の `getQueueConfigurations()`:
- トークン分割結果が 2 要素でない: `SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]")` → `continue`（スキップ）
- キューインデックスが範囲外: `std::invalid_argument` 例外を catch して `SWSS_LOG_ERROR("Invalid queue index [%s] for port [%s]")` → `continue`
- **どちらも silent skip**（そのポート/キューのカウンタが有効化されないが、orchagent は継続）

### E. WRED capability クエリ失敗

`portsorch.cpp:1882-1920` の `initCounterCapabilities()`:
- `sai_query_stats_capability()` が `SAI_STATUS_BUFFER_OVERFLOW` → リサイズして再クエリ
- 再クエリも失敗 or 初回が `SUCCESS` 以外 → `SWSS_LOG_NOTICE("Queue stat capability get failed: ...")` → 全フラグが `"false"` のまま
- `COUNTERS_DB` への `COUNTERS:<oid>` WRED フィールド書き込みは行われない（silent non-addition）

### F. Queue Type 取得失敗 (`getQueueTypeAndIndex`)

`portsorch.cpp:3635-3660`:
- `sai_queue_api->get_queue_attribute()` が `SAI_STATUS_SUCCESS` 以外 → `handleSaiGetStatus()` → `return false`
- 不明な queue type → `throw runtime_error("Got unsupported queue type")` → orchagent abort

### G. Warm-reboot delay timer 中の FLEX_COUNTER_TABLE 受信

`flexcounterorch.cpp:156-158`: `m_delayTimerExpired == false` の間は `doTask()` が即 `return`。
- `enable` イベントを受信しても `generateQueueMap()` 等は呼ばれない
- 60 秒後にタイマー満了時に自動再処理（`m_toSync` は保持されている）

## COUNTERS_DB への影響まとめ

| 失敗シナリオ | COUNTERS_DB 書き込み | orchagent 状態 |
|---|---|---|
| SAI Queue OID フェッチ失敗 | `COUNTERS_QUEUE_NAME_MAP` 等が未書き込み | abort → systemd 再起動 |
| FlexCounter グループ初期化失敗 | FlexCounter 不完全設定、ポーリング停止の可能性 | 継続（ログのみ） |
| `create_only_config_db_buffers` 読み込み失敗 | `false`（全キュー対象）にフォールバック | 継続 |
| BUFFER_QUEUE キー解析失敗 | 当該キーのカウンタが未登録 | 継続（ログのみ） |
| WRED capability クエリ失敗 | WRED フィールドが `COUNTERS:<oid>` に追加されない | 継続（NOTICE ログ） |
| 不明 Queue Type | マッピング書き込み不完全 | abort → systemd 再起動 |
| warm-reboot delay 中 enable 受信 | 60 秒後に自動再処理 | 正常（設計上の遅延） |
