# orchagent-state Phase F — 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-18 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/orchagent-state.md` がカバーする STATE_DB テーブル群
（`WARM_RESTART_TABLE` / `PORT_TABLE` / `FDB_TABLE` / `VRF_OBJECT_TABLE` / `FIPS_MACSEC_POST_TABLE`）
の書込み主体 (`orchagent`: `portsorch`, `fdborch`, `vrforch`, `macsecpost`) が、
これらの STATE_DB テーブル**以外**の DB (APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB / EVENT など)
に副次的な書込みを行うかを全数走査する。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/portsorch.cpp`
- `.cache/sonic-sources/sonic-swss/orchagent/fdborch.cpp`
- `.cache/sonic-sources/sonic-swss/orchagent/vrforch.cpp`
- `.cache/sonic-sources/sonic-swss/orchagent/macsecpost.cpp`
- `.cache/sonic-sources/sonic-swss/orchagent/orchdaemon.cpp`

## 走査結果

### 1. portsorch — APPL_DB (APP_PORT_TABLE)

`portsorch.cpp:770`: `m_portTable = unique_ptr<Table>(new Table(db, APP_PORT_TABLE_NAME));`
→ APPL_DB `APP_PORT_TABLE` へ直接書き込む。

書込みサイト:
- L3890: `m_portTable->set(port.m_alias, tuples)` — flap_count + last_down/up_time (oper DOWN/UP 変化時)
- L3930: `m_portTable->set(port.m_alias, tuples)` — oper_status 変化通知 (`updateDbPortOperStatus()`)
- L4403: `m_portTable->del(key)` — ポート削除時のエントリ削除 (`removePort()`)
- L6643: `m_portTable->hset(port.m_alias, "oper_status", "down")` — link down 検出時
- L6656: `m_portTable->hset(port.m_alias, "flap_count", flapCount)` — flap カウント更新
- L11244/11259: gearbox `system_oper_status` / `line_oper_status` 書込み (`updateGearboxPortOperStatus()`)

### 2. portsorch — COUNTERS_DB

`portsorch.cpp:758`: `m_counter_db = shared_ptr<DBConnector>(new DBConnector("COUNTERS_DB", 0));`
→ COUNTERS_DB に複数のマップ/テーブルを書き込む。

| COUNTERS_DB テーブル | 操作 | タイミング |
|---------------------|------|-----------|
| `COUNTERS_PORT_NAME_MAP` | `setCounterNameMap(alias, port_id)` / `delCounterNameMap(alias)` | ポート追加 (L4118) / 削除 (L4312) |
| `COUNTERS_LAG_NAME_MAP` | LAG エントリ管理 | LAG 操作時 (L762-767) |
| `COUNTERS_SYSTEM_PORT_NAME_MAP` | システムポートマップ | VoQ システムポート追加時 |
| `COUNTERS_PORT_SERDES_ID_TO_PORT_ID_MAP` | `serdes_id → port_id` マッピング | ポート追加時 (L4140-4143) |
| `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_QUEUE_PORT_MAP` / `COUNTERS_QUEUE_INDEX_MAP` / `COUNTERS_QUEUE_TYPE_MAP` | キュー OID マップ | Queue 初期化時 |
| `COUNTERS_PG_NAME_MAP` / `COUNTERS_PG_PORT_MAP` / `COUNTERS_PG_INDEX_MAP` | PG OID マップ | PG 初期化時 |
| `COUNTERS_VOQ_NAME_MAP` | VoQ マップ | VoQ 使用時 |

### 3. portsorch — FLEX_COUNTER_DB

`FlexCounterManager` (`port_stat_manager` / `port_phy_attr_manager` / `port_phy_serdes_attr_manager` /
`queue_stat_manager` / `queue_watermark_manager` / `pg_watermark_manager` /
`pg_drop_stat_manager` / `wred_port_stat_manager` / `wred_queue_stat_manager`) 経由で
FLEX_COUNTER_DB の counter ID list / group parameter を書き込む。

主要サイト:
- L4147: `port_stat_manager.setCounterIdList(port_id, CounterType::PORT, ...)` — ポート追加時
- L3954: `port_stat_manager.clearCounterIdList(port_id)` — ポート削除時
- L8614: `queue_stat_manager.setCounterIdList(queue_ids[idx], ...)` — Queue カウンタ登録
- L8995: `pg_drop_stat_manager.setCounterIdList(pg_ids[idx], ...)` — PG drop カウンタ登録
- L9051: `pg_watermark_manager.setCounterIdList(pg_ids[idx], ...)` — PG watermark カウンタ登録

### 4. portsorch — EVENT (event_publish)

`portsorch.cpp:3798, 7101`: `event_publish(g_events_handle, "if-state", &params);`
→ `sonic-events` フレームワーク経由でインタフェース状態変化イベントを発行する。
DB への直接書込みではなく pub/sub イベントとして送出される。

### 5. fdborch — ASIC_DB (SAI API 経由) と STATE_DB (MCLAG_REMOTE_FDB_TABLE)

- `fdborch.cpp:129, 163`: `m_mclagFdbStateTable.del(key)` — MCLAG remote→local MAC 移動時に `STATE_DB MCLAG_REMOTE_FDB_TABLE` からエントリ削除（本ページの `FDB_TABLE` ではなく別テーブルへの副次操作）。
- SAI `create_fdb_entry` / `remove_fdb_entry` / `flush_fdb_entries` は ASIC_DB 経由だが、orchagent の直接 DB 書込みには含めない（SAI 経由は syncd 責務）。
- APPL_DB への直接書込みはなし（`APPL_DB FLUSHFDBREQUEST` は *consumer* 側として購読するのみ）。

### 6. vrforch — 副次書込みなし

- `vrforch.cpp` に `APPL_DB` / `COUNTERS_DB` / `FLEX_COUNTER` / `ASIC_DB` への直接書込みは検出されなかった。
- SAI `sai_router_api->create/remove_virtual_router` は ASIC_DB 経由（syncd 責務）。

### 7. macsecpost — 副次書込みなし

- `macsecpost.cpp` は STATE_DB `FIPS_MACSEC_POST_TABLE` への書込みのみ。
- 他 DB への副次書込みはなし。

## 結論

| 書込み主体 | 副次 DB | テーブル / グループ | トリガ |
|-----------|---------|---------------------|--------|
| `portsorch` | APPL_DB | `APP_PORT_TABLE` (`oper_status` / `flap_count` / `last_up/down_time` / gearbox oper_status) | SAI ポート状態変化ノーティフィケーション |
| `portsorch` | COUNTERS_DB | `COUNTERS_PORT_NAME_MAP` / LAG / Queue / PG / VoQ OID マップ | ポート / LAG / Queue / PG 追加・削除 |
| `portsorch` | FLEX_COUNTER_DB | `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` ほか複数グループ | ポート追加・削除・FlexCounter 有効化 |
| `fdborch` | STATE_DB | `MCLAG_REMOTE_FDB_TABLE` (del のみ) | MCLAG remote → local MAC 移動 |
| `vrforch` | — | なし | — |
| `macsecpost` | — | なし | — |
