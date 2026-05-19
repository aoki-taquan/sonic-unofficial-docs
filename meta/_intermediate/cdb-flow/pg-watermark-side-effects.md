# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase F 副次 DB 書込スキャンノート

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
Consumer: `FlexCounterOrch::doTask()`, `PortsOrch` PG watermark 関数群, `WatermarkOrch::doTask()`
スキャン範囲: `orchagent/portsorch.cpp:785-787,872-876,8903-8941,8998-9052,9070-9100`, `orchagent/flexcounterorch.cpp:265-270`, `orchagent/watermarkorch.cpp:41-45,116-141`

---

## 副次 DB 書込一覧

### FLEX_COUNTER_DB 書込（portsorch init 時）

`PortsOrch` コンストラクタ内 `setFlexCounterGroupParameter(PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, ...)` (`portsorch.cpp:872-876`) が orchagent 起動時に以下を書き込む。`FLEX_COUNTER_TABLE|PG_WATERMARK` の SET イベントとは無関係に常時実行される。

| DB | テーブル / キー | フィールド | 値 | タイミング |
|----|----------------|-----------|-----|-----------|
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE\|PG_WATERMARK_STAT_COUNTER` | `POLL_INTERVAL` | `"60000"` | orchagent 起動時（`portsorch.cpp:872-876`） |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE\|PG_WATERMARK_STAT_COUNTER` | `STATS_MODE` | `"READ_AND_CLEAR"` | 同上 |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE\|PG_WATERMARK_STAT_COUNTER` | `PG_PLUGIN_FIELD` | Lua スクリプト（`pgWmSha`）の SHA | 同上 |

### FLEX_COUNTER_DB 書込（enable 時）

`FLEX_COUNTER_TABLE|PG_WATERMARK` の `FLEX_COUNTER_STATUS = enable` を受信した flexcounterorch が `addPriorityGroupWatermarkFlexCounters()` を呼び、各 PG OID に対して以下を書き込む。

| DB | テーブル / キー | フィールド | 値 | タイミング |
|----|----------------|-----------|-----|-----------|
| FLEX_COUNTER_DB | `PG_WATERMARK_STAT_COUNTER:<sai_pg_oid>` | `PG_WATERMARK_STAT_ID_LIST` | `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES,SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES` | `FLEX_COUNTER_STATUS = enable` 受信時（`portsorch.cpp:9051`） |

書込は各 PHY ポートの各 PG インデックス（`BUFFER_PG` 設定あり、かつ `FLEX_COUNTER_TABLE|PG_WATERMARK = enable`）に対して per-OID で実行される。

### FLEX_COUNTER_DB 削除（disable 時）

`FLEX_COUNTER_STATUS = disable` または `BUFFER_PG` DEL イベントで `clearCounterIdList()` が呼ばれると対応エントリが FLEX_COUNTER_DB から削除される。

| DB | テーブル / キー | 操作 | タイミング |
|----|----------------|------|-----------|
| FLEX_COUNTER_DB | `PG_WATERMARK_STAT_COUNTER:<sai_pg_oid>` | DEL | `BUFFER_PG` DEL + `getPgWatermarkCountersState() = true` 時（`portsorch.cpp:9095`） |

### COUNTERS_DB 書込（BUFFER_PG イベント時 — PG_WATERMARK と間接連動）

`BUFFER_PG` テーブルへの SET イベントで `addPortBufferPgCounters()` (`portsorch.cpp:8903`) が呼ばれると COUNTERS_DB マップが更新される。`FLEX_COUNTER_TABLE|PG_WATERMARK` の enable 状態に関わらず常時実行される点に注意。

| DB | テーブル / キー | 操作 | タイミング |
|----|----------------|------|-----------|
| COUNTERS_DB | `COUNTERS_PG_NAME_MAP` | SET `<port>:<pg_index>` → `<sai_pg_oid>` | `BUFFER_PG` SET（`portsorch.cpp:8937`） |
| COUNTERS_DB | `COUNTERS_PG_PORT_MAP` | SET `<sai_pg_oid>` → `<sai_port_oid>` | 同上（`portsorch.cpp:8938`） |
| COUNTERS_DB | `COUNTERS_PG_INDEX_MAP` | SET `<sai_pg_oid>` → `<pg_index>` | 同上（`portsorch.cpp:8939`） |
| COUNTERS_DB | `COUNTERS_PG_NAME_MAP` | DEL `<port>:<pg_index>` | `BUFFER_PG` DEL（`portsorch.cpp:9081`） |

### COUNTERS_DB 書込（syncd ポーリング後 — Lua スクリプト）

syncd の FlexCounter が `READ_AND_CLEAR` モードで PG watermark 値を収集した後、`pgWmSha` Lua スクリプトが COUNTERS_DB に書き込む。

| DB | テーブル | キー | タイミング |
|----|---------|------|-----------|
| COUNTERS_DB | `PERIODIC_WATERMARKS` | `PG_WATERMARK_TABLE:<sai_port_oid>:port` など | 各ポーリングサイクル後（デフォルト 60 秒ごと）。`PERIODIC_WATERMARKS` は telemetry タイマー（デフォルト 120 秒）で自動クリア |
| COUNTERS_DB | `PERSISTENT_WATERMARKS` | 同上 | 同上。明示的なクリアまで保持 |
| COUNTERS_DB | `USER_WATERMARKS` | 同上 | 同上。`watermarkcfg clear pg-*` CLI が APPL_DB 通知でクリア |

### watermarkorch による状態追跡

`FLEX_COUNTER_TABLE|PG_WATERMARK` の enable/disable イベントは watermarkorch の `handleFcConfigUpdate()` （`watermarkorch.cpp:116-141`）も受信し、内部フラグ `m_wmStatus` を更新する。

| 副次動作 | 条件 | タイミング |
|---------|------|-----------|
| `m_telemetryTimer->start()` 呼び出し | `prevStatus == 0 && m_wmStatus != 0`（PG_WATERMARK または QUEUE_WATERMARK が初めて enable になるとき） | `FLEX_COUNTER_STATUS = enable` 受信時（`watermarkorch.cpp:132-135`） |
| `m_telemetryTimer->stop()` 呼び出し | `m_wmStatus == 0`（全 watermark が disable になるとき） | `FLEX_COUNTER_STATUS = disable` 受信時（`watermarkorch.cpp:136-139`） |

---

## 副次 DB 書込サマリ

| DB | 書込あり | 主な書込先 |
|----|---------|-----------|
| FLEX_COUNTER_DB | あり | `FLEX_COUNTER_GROUP_TABLE\|PG_WATERMARK_STAT_COUNTER`（init 時）、`PG_WATERMARK_STAT_COUNTER:<oid>`（enable 時） |
| COUNTERS_DB | あり（間接）| `COUNTERS_PG_NAME_MAP` / `COUNTERS_PG_PORT_MAP` / `COUNTERS_PG_INDEX_MAP`（BUFFER_PG イベント時）、`PERIODIC/PERSISTENT/USER_WATERMARKS`（syncd ポーリング後） |
| APPL_DB | なし | — |
| STATE_DB | なし | — |
| ASIC_DB | なし（直接書込なし。SAI 経由のみ） | — |
