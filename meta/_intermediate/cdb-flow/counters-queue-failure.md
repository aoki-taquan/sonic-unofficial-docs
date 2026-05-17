# COUNTERS_DB QUEUE / PG カウンタ — Phase D 失敗挙動スキャンノート

対象テーブル: `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` / `COUNTERS:<OID>` および FlexCounter ポーリング経路  
Consumer: `FlexCounterOrch` + `PortsOrch` (sonic-swss/orchagent/flexcounterorch.cpp, portsorch.cpp)  
スキャン範囲: `flexcounterorch.cpp` 全行、`portsorch.cpp` の `initializeQueuesBulk`, `generateQueueMap`, `generateQueueMapPerPort`, `addQueueFlexCounters`, `createPortBufferQueueCounters`, `createPortBufferPgCounters`, `deletePortBufferQueueCounters` 精読

---

## 検出した失敗パターン

### 1. `initializeQueuesBulk()` — SAI エラーで orchagent クラッシュ

`initializeQueuesBulk()` (portsorch.cpp:6875-6938) は起動時に一括で全ポートの Queue 数と Queue OID リストを SAI から取得する。いずれかのポートで SAI 呼び出しが失敗すると即座に `throw runtime_error("PortsOrch initialization failure.")` を投げる。

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to get number of queues for port %s rv:%d", port.m_alias.c_str(), status);
    handleSaiGetStatus(SAI_API_PORT, status);
    throw runtime_error("PortsOrch initialization failure.");
}
```

同様に Queue OID リスト取得失敗時も `throw runtime_error("PortsOrch initialization failure.")` を投げる (portsorch.cpp:6928)。

**影響**: orchagent プロセスがクラッシュし、supervisor が再起動する。`port.m_queue_ids` が空のまま残り、COUNTERS_DB へのマッピングが生成されない。  
**retry**: 自動的に orchagent 再起動。  
**recovery**: SAI ドライバ / ASIC ドライバ側の問題であることが多い。`show system-memory` / syncd ログを確認。

---

### 2. `getQueueTypeAndIndex()` — SAI エラーで該当キューをスキップ（silent）

`generateQueueMapPerPort()` 内の `getQueueTypeAndIndex()` (portsorch.cpp:3641-3657) は Queue OID から type と index を取得する。SAI 失敗時は `return false` を返し、呼び出し元でそのキューをスキップする（マッピングに含まれない）。

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to get queue type and index for queue %" PRIu64 " rv:%d", queue_id, status);
    task_process_status handle_status = handleSaiGetStatus(SAI_API_QUEUE, status);
    if (handle_status != task_process_status::task_success)
    {
        return false;  // 呼び出し元でキューをスキップ
    }
}
```

不正な queue type（`sai_queue_type_string_map` に存在しない値）の場合は `throw runtime_error("Got unsupported queue type")` で orchagent クラッシュ (portsorch.cpp:3656)。

**影響**: SAI 一時エラーの場合、特定の Queue エントリが `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_TYPE_MAP` / `COUNTERS_QUEUE_INDEX_MAP` に現れない。queuestat でそのキューの列が欠落する。retry なし（`generateQueueMap()` は一度きり実行）。  
**recovery**: orchagent 再起動で `m_isQueueMapGenerated` フラグがリセットされ、再実行される。

---

### 3. 不正な BUFFER_QUEUE キー形式 — SWSS_LOG_ERROR で該当エントリをスキップ

`getQueueConfigurations()` 内のキー解析 (flexcounterorch.cpp:558-562):

```cpp
auto toks = tokenize(portQueueKey, ':');
if (toks.size() != 2)
{
    SWSS_LOG_ERROR("Invalid BUFFER_QUEUE key: [%s]", portQueueKey.c_str());
    continue;
}
```

また、キューインデックスが範囲外または数値でない場合 (flexcounterorch.cpp:597-601):

```cpp
} catch (std::invalid_argument const& e) {
    SWSS_LOG_ERROR("Invalid queue index [%s] for port [%s]", configPortQueues.c_str(), configPortName.c_str());
    continue;
}
```

**影響**: 不正キーのエントリは FlexCounter 登録対象から除外される（silent skip）。当該 BUFFER_QUEUE 設定が存在しても、そのキューのカウンタは `FLEX_COUNTER_DB` に登録されず COUNTERS_DB に現れない。他エントリの処理は継続する。  
**retry**: なし。CONFIG_DB 側のキー形式を修正して再設定する必要がある。

---

### 4. 不正な BUFFER_PG キー形式 — 同様にスキップ

`getPgConfigurations()` でも同様のキー検証を行い (flexcounterorch.cpp:630, 662)、不正な BUFFER_PG キーや PG インデックスは `SWSS_LOG_ERROR` を出力してスキップする。

**影響**: 不正 BUFFER_PG エントリの PG カウンタが FLEX_COUNTER_DB に登録されない。pg-drop / watermarkstat で該当 PG の列が欠落する。

---

### 5. 不正な FLEX_COUNTER_TABLE グループキー — 即削除（retry なし）

`FlexCounterOrch::doTask()` (flexcounterorch.cpp:183-188) は `flexCounterGroupMap` に存在しないキーを受信した場合、即エントリ削除する：

```cpp
if (!flexCounterGroupMap.count(key))
{
    SWSS_LOG_NOTICE("Invalid flex counter group input, %s", key.c_str());
    consumer.m_toSync.erase(it++);
    continue;
}
```

**影響**: `FLEX_COUNTER_TABLE|QUEUE` 以外の未知キー（タイポ等）は CONFIG_DB から書き込まれても処理されず即削除。エラーログは NOTICE レベル。`FLEX_COUNTER_DB` / COUNTERS_DB への影響なし。

---

### 6. `allPortsReady()` が false の間は全 FlexCounter 処理を保留

`FlexCounterOrch::doTask()` (flexcounterorch.cpp:164-167) は `gPortsOrch->allPortsReady()` が false の間即 return する。

**影響**: `portsyncd` 異常終了等で `allPortsReady()` が永遠に true にならない場合、`FLEX_COUNTER_TABLE|QUEUE = enable` の書き込みを処理できない。COUNTERS_DB のキュー / PG マッピングが生成されない。  
**診断**: `swssmon`（`show platform syseeprom` / Redis `EVENTS_DB` 等）で allPortsReady の到達を確認。

---

### 7. Warm-reboot 60 秒遅延タイマー満了前の処理不可

`FlexCounterOrch` コンストラクタ (flexcounterorch.cpp:127-136) が Warm-reboot 時にタイマーを起動し、60 秒間すべての doTask() をブロックする。

**影響**: Warm-reboot 中 60 秒以内に `FLEX_COUNTER_TABLE|QUEUE = enable` の書き込みを行っても処理されない。既存のキュー / PG カウンタの再登録が最大 60 秒遅延する。  
**recovery**: タイマー満了後に自動的に処理が再開される。

---

### 8. `setCounterIdList()` — Redis 接続断で orchagent クラッシュ

`queue_stat_manager.setCounterIdList()` / `pg_stat_manager.setCounterIdList()` は FLEX_COUNTER_DB への Redis `hset` を行う。Redis 接続断等では `RedisReply` の例外が捕捉されずに throw され、orchagent プロセス全体がクラッシュする。

**影響**: Redis 障害時はすべてのカウンタ収集が停止する。supervisor による orchagent 再起動後に復旧する。

---

### 9. WRED 能力チェック失敗 — silent 非登録

`isPortStatSupported()` (portsorch.cpp:655-687) は `sai_query_stats_capability` で WRED stat のサポートを確認する。`SAI_STATUS_SUCCESS` 以外の場合は `return false` を返し、WRED 統計は FLEX_COUNTER_DB に登録されない（エラーログなし）。

**影響**: ASIC が WRED/ECN 統計をサポートしない場合、`FLEX_COUNTER_TABLE|WRED_ECN_QUEUE = enable` にしても COUNTERS_DB に WRED フィールドが現れない（silent）。`queuestat` や `counterpoll show` では STATUS が enable に見えるが実カウンタはゼロのまま。

---

## 失敗パターンサマリ

| # | 失敗箇所 | 挙動 | retry | 影響範囲 |
|---|---------|------|-------|---------|
| 1 | `initializeQueuesBulk()` SAI エラー | orchagent クラッシュ | supervisor 自動再起動 | 全 Queue マッピング生成失敗 |
| 2 | `getQueueTypeAndIndex()` SAI エラー | 当該 Queue のみスキップ（silent） | orchagent 再起動で再試行 | 特定 Queue の COUNTERS_DB 欠落 |
| 3 | 不正 BUFFER_QUEUE キー形式 | 当該エントリスキップ | なし（キー修正要） | 特定 Queue の FlexCounter 未登録 |
| 4 | 不正 BUFFER_PG キー形式 | 当該エントリスキップ | なし（キー修正要） | 特定 PG の FlexCounter 未登録 |
| 5 | 不正 FLEX_COUNTER_TABLE キー | 即エントリ削除 | なし | Queue カウンタ収集不可 |
| 6 | `allPortsReady()` 永続 false | 全 FlexCounter 処理保留 | portsyncd 復旧で自動再開 | COUNTERS_DB マッピング未生成 |
| 7 | Warm-reboot 遅延タイマー | 60 秒間全処理ブロック | 60 秒後自動解除 | 起動後 60 秒間カウンタ更新なし |
| 8 | Redis 接続断 (`setCounterIdList`) | orchagent クラッシュ | supervisor 自動再起動 | 全カウンタ収集停止 |
| 9 | WRED 能力チェック SAI エラー | WRED 統計 silent 非登録 | なし（ASIC 依存） | WRED/ECN カウンタが常にゼロ |
