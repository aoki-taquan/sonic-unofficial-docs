# flex-counter-table Phase C — 暗黙参照テーブルスキャンノート

Generated: 2026-05-18  
Target doc: docs/reference/config-db/flex-counter-table.md

対象テーブル: `CONFIG_DB|FLEX_COUNTER_TABLE|<group>`  
Consumer: `orchagent` — `FlexCounterOrch::doTask()`  
スキャン範囲: `flexcounterorch.cpp` 全行、`orchdaemon.cpp:618-628`、`portsorch.cpp generateXxxMap 系`、`saihelper.cpp:884,1047,1075`

---

## 検出した暗黙参照テーブル

### Direction A — FlexCounterOrch が読む側

#### 1. `DEVICE_METADATA|localhost` (`create_only_config_db_buffers`)

`FlexCounterOrch` コンストラクタ (`flexcounterorch.cpp:107-124`) が CONFIG_DB の `DEVICE_METADATA|localhost` を直接読み込んで `create_only_config_db_buffers` フラグを取得する。このフラグが `true` の場合、QUEUE / PG カウンタの対象は `BUFFER_QUEUE` / `BUFFER_PG` テーブルの非ゼロ profile エントリに限定される。

また `FlexCounterOrch` は `DEVICE_METADATA` の購読コンシューマも登録し (`orchdaemon.cpp:622`)、実行時の `DEVICE_METADATA` 変更を `handleDeviceMetadataTable()` で受信して `m_createOnlyConfigDbBuffers` を動的に更新する (`flexcounterorch.cpp:488-537`).

evidence: `orchagent/flexcounterorch.cpp:104-124`, `orchagent/orchdaemon.cpp:620-623`

#### 2. `BUFFER_QUEUE` (APP_DB) — QUEUE / PG カウンタ対象の決定

`create_only_config_db_buffers=true` 時、`getQueueConfigurations()` (`flexcounterorch.cpp:538-620`) が `gBufferOrch->getBufferObjectsWithNonZeroProfile(portQueueKeys, APP_BUFFER_QUEUE_TABLE_NAME)` を呼び、APPL_DB の `BUFFER_QUEUE` テーブルから非ゼロプロファイルを持つ `port:queue` ペアを取得する。この値が FLEX_COUNTER_DB に登録するキューの集合を決定する。

VOQ シャーシモード (`gMySwitchType == "voq"`) では BUFFER_QUEUE を参照せず全キューを一括登録する。

evidence: `orchagent/flexcounterorch.cpp:544-620`

#### 3. `BUFFER_PG` (APP_DB) — PG カウンタ対象の決定

同様に `getPgConfigurations()` (`flexcounterorch.cpp:621-670`) が `APP_BUFFER_PG_TABLE_NAME` から非ゼロプロファイルの PG エントリを取得する。

evidence: `orchagent/flexcounterorch.cpp:623-670`

### Direction B — FlexCounterOrch が書く側

#### 4. `FLEX_COUNTER_DB / FLEX_COUNTER_GROUP_TABLE` — カウンタグループ制御

`setFlexCounterGroupOperation()` / `setFlexCounterGroupPollInterval()` (`saihelper.cpp:884-960`) が `FLEX_COUNTER_GROUP_TABLE|<group>` に `FLEX_COUNTER_STATUS` / `POLL_INTERVAL` / `BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX` を書き込む（`gTraditionalFlexCounter=true` 時）。`false` 時は SAI Redis 属性 `SAI_REDIS_SWITCH_ATTR_FLEX_COUNTER_GROUP` 経由で syncd に通知。

evidence: `orchagent/saihelper.cpp:884`, `orchagent/flexcounterorch.cpp:415-430`

#### 5. `FLEX_COUNTER_DB / FLEX_COUNTER_TABLE` — per-OID カウンタリスト

`startFlexCounterPolling()` (`saihelper.cpp:1047`) が `FLEX_COUNTER_TABLE|<group>:<oid>` に `PORT_COUNTER_ID_LIST` 等のフィールドを書き込む。`stopFlexCounterPolling()` (`saihelper.cpp:1075`) が DEL で削除する。これが syncd FlexCounter モジュールの polling スケジュールに直接影響する。

evidence: `orchagent/saihelper.cpp:1047,1075`

#### 6. `COUNTERS_DB / COUNTERS_*_NAME_MAP` — 名前→OID マッピング

`generatePortCounterMap()` 等が `COUNTERS_PORT_NAME_MAP` / `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` 等を書き込む。これらのマッピングが存在することで counterpoll / テレメトリ系サービスが名前ベースでカウンタを参照できる。

evidence: `orchagent/portsorch.cpp:9102` (`generatePortCounterMap`)

---

## 参照テーブルサマリ

| 参照先テーブル | DB | 方向 | 条件 | evidence |
|--------------|-----|------|------|---------|
| `DEVICE_METADATA\|localhost` | CONFIG_DB | 読み (起動時 + 購読) | 常時。`create_only_config_db_buffers` フラグ取得 | `flexcounterorch.cpp:107-124,488-537` |
| `BUFFER_QUEUE` | APPL_DB | 読み (QUEUE/PG enable 時) | `create_only_config_db_buffers=true` かつ非 VOQ | `flexcounterorch.cpp:544-620` |
| `BUFFER_PG` | APPL_DB | 読み (PG enable 時) | `create_only_config_db_buffers=true` | `flexcounterorch.cpp:623-670` |
| `FLEX_COUNTER_GROUP_TABLE` | FLEX_COUNTER_DB | 書き | 全グループの STATUS/INTERVAL 変化時 | `saihelper.cpp:884` |
| `FLEX_COUNTER_TABLE\|<group>:<oid>` | FLEX_COUNTER_DB | 書き (enable) / 削除 (disable) | enable 後の `generateXxxMap()` 実行時 | `saihelper.cpp:1047,1075` |
| `COUNTERS_*_NAME_MAP` | COUNTERS_DB | 書き | PORT/QUEUE/PG 等の初回 enable 時 | `portsorch.cpp:9102` |
