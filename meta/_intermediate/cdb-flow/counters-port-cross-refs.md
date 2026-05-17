# COUNTERS_PORT — Phase C 暗黙参照テーブル スキャンノート

対象テーブル: `COUNTERS_PORT_NAME_MAP` / `COUNTERS:<port_oid>` / `COUNTERS_RATES:<port_oid>`
Consumer: `orchagent` / `PortsOrch` + `FlexCounterOrch` (`sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/flexcounterorch.cpp`)
スキャン範囲: `generatePortCounterMap()`, `initCounterCapabilities()`, `doTask()` (FlexCounterOrch), `portstat.py` (sonic-utilities)

---

## 暗黙参照テーブル一覧

### 1. `APP_DB:PORT_TABLE|PortInitDone` — 起動完了ガード

- `FlexCounterOrch::doTask()` (`flexcounterorch.cpp:164-166`) は `gPortsOrch->allPortsReady()` が `false` の間 return。
- `allPortsReady()` (`portsorch.cpp:1685`) は `APP_DB:PORT_TABLE|PortInitDone` の存在で `true` になる。
- **方向**: 読み取り（存在確認）。`PortInitDone` が無い状態で `FLEX_COUNTER_TABLE|PORT` へ enable を書いても `doTask` は何もしない。
- evidence: `flexcounterorch.cpp:164-166`, `portsorch.cpp:1685-1687`

### 2. `STATE_DB:PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_*` — WRED カウンタ収集可否判定

- `PortsOrch::initCounterCapabilities()` (`portsorch.cpp:1850-1980`) は `sai_query_stats_capability()` でハードウェア能力を問い合わせ、その結果を `STATE_DB:PORT_COUNTER_CAPABILITIES` テーブルに書き込む。
- `portstat.py` (`portstat.py:297-329`) は `PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_GREEN_DROP_COUNTER` 等を STATE_DB から読み取り、`isSupported` が `"false"` の場合は `counter_bucket_dict` から該当 SAI フィールドを除外する。
- **方向**: 書き込み（`portsorch` → `STATE_DB`）+ 読み取り（`portstat.py` ← `STATE_DB`）。
- **効果**: ASIC が WRED drop counter をサポートしない場合、`counterpoll port enable` を実行しても WRED フィールドは `portstat` 表示に現れない（silent skip）。
- evidence: `portsorch.cpp:1876-1879`, `portsorch.cpp:1928-1980`, `portstat.py:297-329`

### 3. `COUNTERS_DB:COUNTERS_PORT_NAME_MAP` — ポート名 → SAI OID マッピング

- `PortsOrch` コンストラクタ (`portsorch.cpp:759`) で `CounterNameMapUpdater` を初期化し、ポート作成時に `<alias>:<OID>` を `COUNTERS_PORT_NAME_MAP` に書き込む。
- `portstat.py` はこのマップを読み取ってポート名と OID を対応付け、`COUNTERS:<OID>` のカウンタ値を取得する。
- **方向**: 書き込み（`portsorch` → `COUNTERS_DB`）+ 読み取り（`portstat.py` / `sonic-db-cli` ← `COUNTERS_DB`）。
- **効果**: マップは counterpoll enable/disable に関係なく常時更新される。ポート削除時は該当エントリが除去される（`portsorch.cpp:4312`）。
- evidence: `portsorch.cpp:759`, `portstat.py:142-144`

### 4. `FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<OID>` — syncd ポーリング登録

- `port_stat_manager.setCounterIdList()` が syncd の `FLEX_COUNTER_DB` に `COUNTER_ID_LIST` を書き込むことでポーリングが開始される。
- `FlexCounterOrch::doTask()` の enable 処理 (`flexcounterorch.cpp:237-241`) から `gPortsOrch->generatePortCounterMap()` → `port_stat_manager.setCounterIdList()` の順で呼ばれる。
- **方向**: 書き込み（`portsorch` → `FLEX_COUNTER_DB`）。
- evidence: `flexcounterorch.cpp:237-241`, `portsorch.cpp:9118-9119`

### 5. `CONFIG_DB:DEVICE_METADATA|localhost.create_only_config_db_buffers` — PORT カウンタには非影響

- PORT カウンタ登録は `getQueueConfigurations()` / `getPgConfigurations()` を使わないため、`create_only_config_db_buffers` フラグの影響を受けない。
- `generatePortCounterMap()` は `m_portList` の全 PHY ポートに対して無条件にカウンタを登録する。
- **方向**: 参照なし（PORT カウンタはバッファ設定非依存）。
- evidence: `portsorch.cpp:9111-9119`

---

## 参照関係サマリ

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `APP_DB:PORT_TABLE\|PortInitDone` | 読み取り（存在確認）— 起動ブロック | 常時。`allPortsReady()` = false の間 `doTask` が全リターン | `flexcounterorch.cpp:164-166`, `portsorch.cpp:1685-1687` |
| `STATE_DB:PORT_COUNTER_CAPABILITIES\|WRED_ECN_PORT_*` | 書き込み（`portsorch`）/ 読み取り（`portstat.py`） | WRED drop counter の ASIC サポート有無を反映。`portstat` 表示の WRED フィールドの silent skip 判定 | `portsorch.cpp:1876-1879,1928-1980`, `portstat.py:297-329` |
| `COUNTERS_DB:COUNTERS_PORT_NAME_MAP` | 書き込み（`portsorch`）/ 読み取り（`portstat.py`） | 常時。counterpoll 状態に依存しない | `portsorch.cpp:759`, `portstat.py:142-144` |
| `FLEX_COUNTER_DB:PORT_STAT_COUNTER_FLEX_COUNTER_GROUP:<OID>` | 書き込み（`port_stat_manager`） | `FLEX_COUNTER_TABLE\|PORT = enable` 受信後 | `flexcounterorch.cpp:237-241`, `portsorch.cpp:9118-9119` |
