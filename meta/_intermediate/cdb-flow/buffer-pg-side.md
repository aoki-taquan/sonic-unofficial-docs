# BUFFER_PG — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/buffer-pg.md` 配下の CONFIG_DB `BUFFER_PG` テーブル変更時に、`buffermgrd` / `buffermgrdyn` (cfgmgr) および `BufferOrch` (orchagent) が APPL_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB へ副次書き込みを行うか。

## 走査範囲

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp` (createPortBufferPgCounters / addPortBufferPgCounters の実装)

## 走査コマンドと結果

### 1. buffermgrdyn.cpp — STATE_DB / APPL_DB 書込

```bash
grep -n "m_stateBufferProfileTable\|m_stateBufferPoolTable\|m_applBufferProfileTable\|m_applBufferObjectTables\|\.set(\|\.del(" \
  sonic-swss/cfgmgr/buffermgrdyn.cpp | grep -v "//"
```

BUFFER_PG 処理 (`handleSingleBufferPgEntry` → `updateBufferObjectToDb`) により以下が確認された:

- **APPL_DB `BUFFER_PG_TABLE`** (`APP_BUFFER_PG_TABLE_NAME`): `m_applBufferObjectTables[BUFFER_PG].set/del(key, fvVector)` — L928,943,947,958 — profile 値を APPL_DB に set。プロファイル未解決時は del。
- **APPL_DB `BUFFER_PROFILE_TABLE`**: `m_applBufferProfileTable.set(name, fvVector)` — L919 — 動的算出プロファイルを APPL_DB に書き込む (BUFFER_PG 参照時に自動生成されたプロファイル)。
- **STATE_DB `BUFFER_PROFILE_TABLE`**: `m_stateBufferProfileTable.set(name, fvVector)` — L920 — 同プロファイルを STATE_DB にも同時書き込み。

### 2. bufferorch.cpp → portsorch.cpp — COUNTERS_DB / FLEX_COUNTER_DB 書込

`processPriorityGroupPost()` (L1476) が SAI 適用成功後に `createPortBufferPgCounters()` (portsorch.cpp:8889) を呼び出す。

`addPortBufferPgCounters()` → `addPortBufferPgCounters()` 実装 (L8903):

- **COUNTERS_DB `COUNTERS_PG_NAME_MAP`**: `m_pgCounterNameMapUpdater->setCounterNameMap(pgVector)` — L8937 — port alias:pgIndex → SAI OID マッピングを登録。
- **COUNTERS_DB `COUNTERS_PG_PORT_MAP`**: `m_pgPortTable->set("", pgPortVector)` — L8938 — PG OID → port OID マッピング。
- **COUNTERS_DB `COUNTERS_PG_INDEX_MAP`**: `m_pgIndexTable->set("", pgIndexVector)` — L8939 — PG OID → PG index マッピング。
- **FLEX_COUNTER_DB `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP`**: `pg_drop_stat_manager.setCounterIdList(pg_id, CounterType::PRIORITY_GROUP, stats)` — L8995 — drop stat ポーリング登録 (FlexCounterOrch が `getPgCountersState()` == true の場合のみ)。
- **FLEX_COUNTER_DB `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP`**: `pg_watermark_manager.setCounterIdList(pg_id, CounterType::PRIORITY_GROUP, stats)` — L9051 — watermark stat ポーリング登録 (FlexCounterOrch が `getPgWatermarkCountersState()` == true の場合のみ)。

DEL 経路では `removePortBufferPgCounters()` (L9054) が上記と対称的に del/clearCounterIdList を実行。

### 3. buffermgr.cpp (静的モード)

buffermgr.cpp には STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への書き込み API 呼出は確認されなかった (grep 結果 0 件)。APPL_DB `BUFFER_PG_TABLE` への書き込みは `doTask()` 内の ProducerStateTable 経由で発生する。

## 結論

CONFIG_DB `BUFFER_PG` テーブルの変更は以下 4 つの副次 DB に書き込みを生じさせる。

| 副次 DB | テーブル | 書込経路 | 条件 |
|---------|---------|---------|------|
| APPL_DB | `BUFFER_PG_TABLE` | `buffermgrdyn` → `updateBufferObjectToDb()` | 常時 (buffer pool 準備済み) |
| APPL_DB | `BUFFER_PROFILE_TABLE` | `buffermgrdyn` → `programProfileToDb()` | 動的算出プロファイルが新規生成された場合 |
| STATE_DB | `BUFFER_PROFILE_TABLE` | `buffermgrdyn` → `programProfileToDb()` | 同上 (APPL_DB と同時) |
| COUNTERS_DB | `COUNTERS_PG_NAME_MAP`, `COUNTERS_PG_PORT_MAP`, `COUNTERS_PG_INDEX_MAP` | `BufferOrch` → `createPortBufferPgCounters()` | SAI 適用成功 + isCreateOnlyConfigDbBuffers=true |
| FLEX_COUNTER_DB | `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `pg_drop_stat_manager.setCounterIdList()` | 上記 + getPgCountersState()=true |
| FLEX_COUNTER_DB | `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `pg_watermark_manager.setCounterIdList()` | 上記 + getPgWatermarkCountersState()=true |

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| APPL_DB BUFFER_PG_TABLE への set/del | `buffermgrdyn.cpp:928,943,947,958` | 確認 |
| APPL_DB BUFFER_PROFILE_TABLE への set | `buffermgrdyn.cpp:919` | 確認 (動的モード) |
| STATE_DB BUFFER_PROFILE_TABLE への set | `buffermgrdyn.cpp:920` | 確認 (動的モード) |
| COUNTERS_DB PG マップへの書込 | `portsorch.cpp:8937-8939` | 確認 (条件付き) |
| FLEX_COUNTER_DB PG drop stat 登録 | `portsorch.cpp:8995` | 確認 (getPgCountersState=true 時) |
| FLEX_COUNTER_DB PG watermark stat 登録 | `portsorch.cpp:9051` | 確認 (getPgWatermarkCountersState=true 時) |
| buffermgr.cpp での副次 DB 書込 | `buffermgr.cpp` 全体 | 0 件 |
