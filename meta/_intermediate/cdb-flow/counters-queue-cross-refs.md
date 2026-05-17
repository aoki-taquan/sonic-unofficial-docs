# COUNTERS_DB QUEUE / PG カウンタ — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/counters-queue.md`
解析日: 2026-05-17
根拠ソース: `sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/flexcounterorch.cpp`

---

## 目的

`COUNTERS_DB` の Queue / PG カウンタ収集処理（主に `FlexCounterOrch` と `PortsOrch`）が
CONFIG_DB テーブルを処理する際に暗黙的に参照・依存する他テーブルのキー / フィールドを
網羅する。

---

## 1. FLEX_COUNTER_TABLE — カウンタ収集の制御元

### 参照箇所

`FlexCounterOrch::doTask()` — `flexcounterorch.cpp:240-281`

```cpp
// FLEX_COUNTER_TABLE|QUEUE の FLEX_COUNTER_STATUS = enable を受けて
// generateQueueMap() / addQueueFlexCounters() を呼び出す
if (op == "SET")
{
    if (groupName == CFG_QUEUE_FLEX_COUNTER_GROUP)
    {
        gPortsOrch->generateQueueMap(getQueueConfigurations());
        gPortsOrch->addQueueFlexCounters(getQueueConfigurations());
    }
    ...
}
```

`FlexCounterOrch::getQueueCountersState()` — `flexcounterorch.cpp:453`

```cpp
bool FlexCounterOrch::getQueueCountersState() const
{
    // m_queueCountersState は FLEX_COUNTER_TABLE|QUEUE の FLEX_COUNTER_STATUS を反映
    return m_queueCountersState;
}
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `createPortBufferQueueCounters()` の FLEX_COUNTER_DB 登録判断 | `FLEX_COUNTER_TABLE` (CONFIG_DB) | `FLEX_COUNTER_TABLE\|QUEUE` | `getQueueCountersState()` が `true`（= `enable`）の場合のみ SAI カウンタを FLEX_COUNTER_DB に登録。`false` の場合はマッピングのみ書込み | `portsorch.cpp:8731`, `flexcounterorch.cpp:453-461` |
| `createPortBufferQueueCounters()` の Watermark 登録 | `FLEX_COUNTER_TABLE` (CONFIG_DB) | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | `getQueueWatermarkCountersState()` が `true` の場合のみ Watermark FlexCounter を登録 | `portsorch.cpp:8736-8738` |
| `createPortBufferQueueCounters()` の WRED 登録 | `FLEX_COUNTER_TABLE` (CONFIG_DB) | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | `getWredQueueCountersState()` が `true` の場合のみ WRED FlexCounter を登録 | `portsorch.cpp:8741-8745` |
| `createPortBufferPgCounters()` の PG_DROP 登録 | `FLEX_COUNTER_TABLE` (CONFIG_DB) | `FLEX_COUNTER_TABLE\|PG_DROP` | `getPgCountersState()` が `true` の場合のみ PG ドロップカウンタを登録 | `portsorch.cpp:8925-8927` |
| `createPortBufferPgCounters()` の PG_WATERMARK 登録 | `FLEX_COUNTER_TABLE` (CONFIG_DB) | `FLEX_COUNTER_TABLE\|PG_WATERMARK` | `getPgWatermarkCountersState()` が `true` の場合のみ PG Watermark カウンタを登録 | `portsorch.cpp:8930-8933` |

---

## 2. BUFFER_QUEUE — キュー範囲フィルタ

### 参照箇所

`FlexCounterOrch::getQueueConfigurations()` — `flexcounterorch.cpp:538-608`

```cpp
// create_only_config_db_buffers=true かつ非 VoQ の場合
gBufferOrch->getBufferObjectsWithNonZeroProfile(portQueueKeys, APP_BUFFER_QUEUE_TABLE_NAME);
// 非ゼロプロファイルが設定されたキューのみカウンタ登録対象にする
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `getQueueConfigurations()` のキュー範囲決定 | `BUFFER_QUEUE` (APPL_DB 経由) | `BUFFER_QUEUE\|<port>:<queue_range>` | `DEVICE_METADATA.create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つキューのみを FlexCounter 登録対象とする。`false`（デフォルト）または VoQ では全キューを対象 | `flexcounterorch.cpp:545-554` |

---

## 3. BUFFER_PG — PG 範囲フィルタ

### 参照箇所

`FlexCounterOrch::getPgConfigurations()` — `flexcounterorch.cpp:609-660`

```cpp
// create_only_config_db_buffers=true の場合
gBufferOrch->getBufferObjectsWithNonZeroProfile(portPgKeys, APP_BUFFER_PG_TABLE_NAME);
// 非ゼロプロファイル付き PG のみカウンタ登録対象
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `getPgConfigurations()` の PG 範囲決定 | `BUFFER_PG` (APPL_DB 経由) | `BUFFER_PG\|<port>:<pg_range>` | `DEVICE_METADATA.create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つ PG のみを FlexCounter 登録対象とする | `flexcounterorch.cpp:620-623` |

---

## 4. DEVICE_METADATA — バッファモード切替

### 参照箇所

`FlexCounterOrch` コンストラクタ — `flexcounterorch.cpp:110-124`

```cpp
m_deviceMetadataConfigTable.hget("localhost", "create_only_config_db_buffers", createOnlyConfigDbBuffersValue);
m_createOnlyConfigDbBuffers = (createOnlyConfigDbBuffersValue == "true");
```

`FlexCounterOrch::handleDeviceMetadataTable()` — `flexcounterorch.cpp:488-521`

```cpp
// 実行時に DEVICE_METADATA の変更を購読して m_createOnlyConfigDbBuffers を動的更新
if (field == "create_only_config_db_buffers")
    m_createOnlyConfigDbBuffers = (value == "true");
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `getQueueConfigurations()` / `getPgConfigurations()` のモード分岐 | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` フィールド `create_only_config_db_buffers` | `true` → BUFFER_QUEUE / BUFFER_PG 非ゼロプロファイル対象のみ。`false`（デフォルト未設定） / VoQ → 全キュー / PG を対象。実行時変更は `handleDeviceMetadataTable()` で反映されるが既登録カウンタは変更されない | `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:488-521`, `flexcounterorch.cpp:544-554` |

---

## 5. PORT (APP_PORT_TABLE) — OID フェッチ前提

### 参照箇所

`PortsOrch::initializeQueuesBulk()` — `portsorch.cpp:6583-6598`

```cpp
// initializePorts() の中で全ポートの SAI OID を取得して m_queue_ids にキャッシュ
// これが完了しないと generateQueueMap() のループが 0 回で終わる
```

### 依存内容

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 参照箇所 |
|---|---|---|---|---|
| `generateQueueMap()` の前提条件 | `PORT` (APP_PORT_TABLE) | `APP_PORT_TABLE\|<port_name>` | `allPortsReady()` が true になって初めて `FlexCounterOrch::doTask()` が実行される。ポートの SAI OID（`port.m_queue_ids`）が取得済みでなければ `generateQueueMap()` の結果は空 | `portsorch.cpp:6583-6598`, `flexcounterorch.cpp:164-167` |

---

## 6. cross-refs ブロック（最終形）

以下を `docs/reference/config-db/counters-queue.md` の `<!-- /ordering -->` 直後に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

<!-- evidence: sonic-swss/orchagent/portsorch.cpp (createPortBufferQueueCounters,
     createPortBufferPgCounters, addPortBufferQueueCounters, initializeQueuesBulk),
     sonic-swss/orchagent/flexcounterorch.cpp (getQueueConfigurations, getPgConfigurations,
     getQueueCountersState, getPgCountersState, handleDeviceMetadataTable) -->

`FlexCounterOrch` / `PortsOrch` がキュー・PG カウンタを処理する際に暗黙的に参照する
他テーブルを示す。YANG の leafref として定義されたものはなく、コードのみで表現された
依存関係である。

| 参照元処理 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---|---|---|---|---|
| `createPortBufferQueueCounters()` の FlexCounter 登録判断 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|QUEUE` | `getQueueCountersState()=true`（`FLEX_COUNTER_STATUS=enable`）のときのみ SAI カウンタを FLEX_COUNTER_DB に登録。`false` の場合は COUNTERS_QUEUE_NAME_MAP へのマッピングのみ書込み | `portsorch.cpp:8731`, `flexcounterorch.cpp:453` |
| `createPortBufferQueueCounters()` の Watermark 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` | `getQueueWatermarkCountersState()=true` の場合のみ Watermark FlexCounter を登録 | `portsorch.cpp:8736-8738` |
| `createPortBufferQueueCounters()` の WRED 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|WRED_ECN_QUEUE` | `getWredQueueCountersState()=true` の場合のみ WRED FlexCounter を登録 | `portsorch.cpp:8741-8745` |
| `createPortBufferPgCounters()` の PG_DROP 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|PG_DROP` | `getPgCountersState()=true` の場合のみ PG ドロップカウンタを登録 | `portsorch.cpp:8925-8927` |
| `createPortBufferPgCounters()` の PG_WATERMARK 登録 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_TABLE\|PG_WATERMARK` | `getPgWatermarkCountersState()=true` の場合のみ PG Watermark カウンタを登録 | `portsorch.cpp:8930-8933` |
| `getQueueConfigurations()` のキュー範囲決定 | [`BUFFER_QUEUE`](buffer-queue.md) | `BUFFER_QUEUE\|<port>:<queue_range>` | `create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つキューのみ FlexCounter 登録対象。`false`（デフォルト）または VoQ モードでは全キューを対象 | `flexcounterorch.cpp:545-554` |
| `getPgConfigurations()` の PG 範囲決定 | [`BUFFER_PG`](buffer-pg.md) | `BUFFER_PG\|<port>:<pg_range>` | `create_only_config_db_buffers=true` の場合、非ゼロプロファイルを持つ PG のみ FlexCounter 登録対象 | `flexcounterorch.cpp:620-623` |
| `getQueueConfigurations()` / `getPgConfigurations()` のモード分岐 | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` フィールド `create_only_config_db_buffers` | バッファモード切替フラグ。`true` → BUFFER_QUEUE / BUFFER_PG 限定。`false`（デフォルト）→ 全対象。実行時変更は `handleDeviceMetadataTable()` で反映されるが既登録カウンタは変更されない | `flexcounterorch.cpp:110-124`, `flexcounterorch.cpp:508-513` |
| `generateQueueMap()` の前提 | `PORT` | `APP_PORT_TABLE\|<port_name>` | `allPortsReady()` が false の間 `FlexCounterOrch::doTask()` は即 return。ポートの SAI OID（`port.m_queue_ids`）が確定しないと `generateQueueMap()` のループが 0 回で終わる | `portsorch.cpp:6583-6598`, `flexcounterorch.cpp:164-167` |

### 解決タイミング

- **FLEX_COUNTER_TABLE**: `FlexCounterOrch::doTask()` が即時評価。`enable` 書込み時点でカウンタ登録処理が実行される（allPortsReady 後）。
- **BUFFER_QUEUE / BUFFER_PG**: `getQueueConfigurations()` / `getPgConfigurations()` が呼ばれるたびに `gBufferOrch->getBufferObjectsWithNonZeroProfile()` で動的に再取得される（`create_only_config_db_buffers=true` 時のみ）。
- **DEVICE_METADATA**: コンストラクタで 1 回読込み + `handleDeviceMetadataTable()` で動的更新。既登録カウンタへの遡及適用はなく、orchagent 再起動が必要。
- **PORT**: `allPortsReady()` による自動待機。portsorch が全ポート初期化完了後に `FlexCounterOrch` のキュー処理がアンブロックされる。
<!-- /cross-refs -->
```
