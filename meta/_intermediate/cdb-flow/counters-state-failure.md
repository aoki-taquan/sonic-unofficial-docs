# counters-state Phase D — 失敗挙動スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/counters-state.md

対象テーブル: `STATE_DB / PORT_COUNTER_CAPABILITIES`, `QUEUE_COUNTER_CAPABILITIES`, `DEBUG_COUNTER_CAPABILITIES`
書き込み元: `portsorch::initCounterCapabilities()`, `debugcounterorch::publishDropCounterCapabilities()`
スキャン範囲: `portsorch.cpp:1850-1968`, `debugcounterorch.cpp:315-363`, `debug_counter/drop_counter.cpp:298-446`

---

## 失敗シナリオ一覧

### 1. `sai_query_stats_capability(SAI_OBJECT_TYPE_QUEUE, ...)` 失敗

**コード箇所**: `portsorch.cpp:1882-1922`

```
status = sai_query_stats_capability(switchId, SAI_OBJECT_TYPE_QUEUE, &queue_stats_capability);
if (status == SAI_STATUS_BUFFER_OVERFLOW) { ... 再実行 ... }
if (status == SAI_STATUS_SUCCESS) { ... 更新 ... }
else { SWSS_LOG_NOTICE("Queue stat capability get failed: ..."); }
```

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| SAI query 失敗 (非 `SAI_STATUS_SUCCESS`) | `SWSS_LOG_NOTICE` のみ。全 QUEUE_COUNTER_CAPABILITIES フィールドが `"false"` のまま残存 | `queuestat` で WRED キューカウンタが常に `N/A` |
| `SAI_STATUS_BUFFER_OVERFLOW` 後に再実行も失敗 | 上記同様。`SWSS_LOG_NOTICE` のみ | 同上 |
| orchagent エラー終了 | なし（継続動作） | — |

### 2. `sai_query_stats_capability(SAI_OBJECT_TYPE_PORT, ...)` 失敗

**コード箇所**: `portsorch.cpp:1929-1968`

同様の構造。失敗時は `SWSS_LOG_NOTICE("Port stat capability get failed: ...")` のみ。

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| SAI query 失敗 | `SWSS_LOG_NOTICE` のみ。全 PORT_COUNTER_CAPABILITIES フィールドが `"false"` のまま | `portstat` で WRED ポートカウンタが常に `N/A` |
| orchagent エラー終了 | なし | — |

### 3. `getSupportedDropReasons()` 失敗

**コード箇所**: `drop_counter.cpp:305-312`

```
if (sai_query_attribute_enum_values_capability(...) != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("This device does not support querying drop reasons");
    return {};
}
```

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| SAI query 失敗 | 空集合返却 → `publishDropCounterCapabilities` で `drop_reasons.empty()` 判定 → テーブル書き込みスキップ | `DEBUG_COUNTER_CAPABILITIES` テーブルが空 / `show debug-counter capabilities` が何も表示しない |

### 4. `getSupportedCounterTypes()` 失敗

**コード箇所**: `drop_counter.cpp:346-399`

```
status = sai_query_attribute_enum_values_capability(..., SAI_DEBUG_COUNTER_ATTR_TYPE, ...);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("This device does not support querying drop counters");
    return {};
}
```

また SAI メタデータ null check で失敗した場合も `SWSS_LOG_ERROR` + 空集合返却:
```
if (!meta) { SWSS_LOG_ERROR("SAI BUG: metadata null pointer ..."); return {}; }
```

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| SAI query 失敗 | `SWSS_LOG_NOTICE` + 空集合返却 → 全 counter_type がスキップ → テーブル空 | 上記同様 |
| SAI メタデータ null (SAI バグ) | `SWSS_LOG_ERROR` + 空集合返却 → テーブル空 | 同上。ログに `SAI BUG` が記録される |

### 5. `getSupportedDebugCounterAmounts()` が 0 返却

**コード箇所**: `drop_counter.cpp:432-446`

```
if (sai_object_type_get_availability(...) != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("This device does not support querying the number of drop counters");
    return 0;
}
```

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| SAI availability query 失敗 | `SWSS_LOG_NOTICE` + 0 返却 → `num_counters == "0"` → テーブル書き込みスキップ | 対応 counter_type が `DEBUG_COUNTER_CAPABILITIES` から欠落 |
| プラットフォームが debug counter リソースを枯渇している場合 | count が減少し、場合によっては 0 → 書き込みスキップ | 注: コード内コメント「may change due to resource allocation in other parts of the system」(drop_counter.cpp:425-431) |

### 6. `STATE_DB` 接続失敗

**コード箇所**: `portsorch.cpp:789-794`, `debugcounterorch.cpp:30-31`

```cpp
// portsorch
m_state_db = shared_ptr<DBConnector>(new DBConnector("STATE_DB", 0));
m_queueCounterCapabilitiesTable = unique_ptr<Table>(new Table(m_state_db.get(), ...));
m_portCounterCapabilitiesTable  = unique_ptr<Table>(new Table(m_state_db.get(), ...));

// debugcounterorch
m_stateDb(new DBConnector("STATE_DB", 0)),
m_debugCapabilitiesTable(new Table(m_stateDb.get(), STATE_DEBUG_COUNTER_CAPABILITIES_NAME)),
```

| 条件 | 挙動 | ユーザーへの影響 |
|------|------|----------------|
| STATE_DB 接続失敗 | `DBConnector` / `Table` コンストラクタが例外 → orchagent プロセスクラッシュ | SONiC 起動失敗。`systemctl status swss` でエラー確認可 |

---

## 失敗挙動サマリ

| # | 失敗箇所 | ログレベル | orchagent 継続 | STATE_DB への影響 | 見え方 |
|---|---------|-----------|--------------|-----------------|--------|
| 1 | SAI Queue stats capability query | `SWSS_LOG_NOTICE` | 継続 | QUEUE_COUNTER_CAPABILITIES 全フィールド `"false"` | WRED キューカウンタ N/A |
| 2 | SAI Port stats capability query | `SWSS_LOG_NOTICE` | 継続 | PORT_COUNTER_CAPABILITIES 全フィールド `"false"` | WRED ポートカウンタ N/A |
| 3 | SAI drop reason capability query | `SWSS_LOG_NOTICE` | 継続 | DEBUG_COUNTER_CAPABILITIES テーブル空 | `show debug-counter capabilities` 空表示 |
| 4 | SAI counter type query | `SWSS_LOG_NOTICE` / `SWSS_LOG_ERROR` | 継続 | 同上 | 同上 |
| 5 | SAI debug counter availability query | `SWSS_LOG_NOTICE` | 継続 | 対応 counter_type エントリ欠落 | 同上（一部欠落） |
| 6 | STATE_DB 接続失敗 | 例外クラッシュ | クラッシュ | 書き込みなし | orchagent 起動失敗 |
