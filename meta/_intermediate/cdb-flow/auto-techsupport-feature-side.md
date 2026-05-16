# AUTO_TECHSUPPORT_FEATURE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/auto-techsupport-feature.md` 配下の CONFIG_DB `AUTO_TECHSUPPORT_FEATURE` テーブルに関連する一発実行スクリプト群 (`coredump_gen_handler.py`, `techsupport_cleanup.py`) が、CONFIG_DB 以外の DB へ書込みを行うか。`AUTO_TECHSUPPORT_FEATURE` テーブル自体はイベント起動型で常駐 subscriber を持たないため、書込みは「core dump 発生 / techsupport 完了 / techsupport rotate」の各副次イベント経路で発生する。

## 走査範囲

- `.cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py`
- `.cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py`
- `.cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py` (両 script の共通実装)

## 走査コマンドと結果

### grep: DB 書込 API 呼出

```bash
grep -nE "STATE_DB|set\(|hset|publish|Producer|Table\(|Notification|swsscommon" \
  .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
  .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
  .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py
```

主要ヒット:

- `coredump_gen_handler.py:71` — `db.connect(STATE_DB)` (read/write 両用接続)
- `techsupport_cleanup.py:18` — `db.delete(STATE_DB, TS_MAP + "|" + name)` (techsupport rotate 時のクリーンアップ)
- `techsupport_cleanup.py:54` — `db.connect(STATE_DB)`
- `auto_techsupport_helper.py:60` — `TS_MAP = "AUTO_TECHSUPPORT_DUMP_INFO"` (キー prefix 定義)
- `auto_techsupport_helper.py:305-310` — `write_to_state_db()` の `db.set(STATE_DB, key, ...)` 4 連発
- `auto_techsupport_helper.py:337` — `invoke_ts_command_rate_limited` 内で techsupport 生成成功時に呼ばれる

`coredump_gen_handler.py` 単体には `db.set` / `db.delete` の直接呼出は存在しないが、`invoke_ts_command_rate_limited()` (helper) 経由で `write_to_state_db()` を呼び出すため、間接的に STATE_DB へ書込みが発生する。

## 検出された副次書込

### 1. STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO|<dump-name>` への書込 (techsupport 生成成功時)

**経路**: `coredump_gen_handler.py` → `invoke_ts_command_rate_limited()` → `write_to_state_db()` → `db.set(STATE_DB, ...)`

`auto_techsupport_helper.py:302-310`:

```python
def write_to_state_db(db, timestamp, ts_dump, event_type, event_data, container=None):
    name = strip_ts_ext(ts_dump)
    key = TS_MAP + "|" + name
    db.set(STATE_DB, key, TIMESTAMP, str(timestamp))
    db.set(STATE_DB, key, EVENT_TYPE, event_type)
    for event_data_key, event_data_value in event_data.items():
        db.set(STATE_DB, key, event_data_key, event_data_value)
    if container:
        db.set(STATE_DB, key, CONTAINER, container)
```

| 対象 DB / テーブル | キー | フィールド | 値 |
|------------------|------|----------|----|
| STATE_DB / `AUTO_TECHSUPPORT_DUMP_INFO` | `<dump-name-no-ext>` (例 `sonic_dump_DUT_20260515_123456`) | `timestamp` | `int(time.time())` (Unix epoch 秒, 文字列化) |
| STATE_DB / `AUTO_TECHSUPPORT_DUMP_INFO` | 同上 | `event_type` | `core` (CoreDump 起動) または `memory` (memory_threshold_check 起動) |
| STATE_DB / `AUTO_TECHSUPPORT_DUMP_INFO` | 同上 | `core_dump` | core dump ファイル名 (例 `python3.12345.1715772896.gz`) ※`event_type=core` 時のみ |
| STATE_DB / `AUTO_TECHSUPPORT_DUMP_INFO` | 同上 | `container` | feature/docker 名 (例 `swss`) ※`container` 引数が渡された場合のみ |

書込トリガ: core dump 発生 → `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()` で AUTO_TECHSUPPORT|GLOBAL と AUTO_TECHSUPPORT_FEATURE|<feat> の両 `state` が `enabled`、かつ rate-limit を満たした場合のみ `generate_dump` を起動し、戻った `new_file` が非空なら本書込が走る (`auto_techsupport_helper.py:334-337`)。

### 2. STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO|<dump-name>` の削除 (techsupport rotate 時)

**経路**: `generate_dump` 完了 → `techsupport_cleanup.py` → `clean_state_db_entries()` → `db.delete(STATE_DB, ...)`

`techsupport_cleanup.py:13-18`:

```python
def clean_state_db_entries(removed_files, db):
    if not removed_files:
        return
    for file in removed_files:
        name = strip_ts_ext(file)
        db.delete(STATE_DB, TS_MAP + "|" + name)
```

| 対象 DB / テーブル | 操作 | キー |
|------------------|------|------|
| STATE_DB / `AUTO_TECHSUPPORT_DUMP_INFO` | `delete` | rotate 対象 dump 名 (file system 側で削除された techsupport tar.gz に対応) |

書込トリガ: `AUTO_TECHSUPPORT|GLOBAL.state=enabled` かつ `max_techsupport_limit` が float に変換可能で `>0` の場合のみ、`cleanup_process()` が `/var/dump/` 配下を最古順で削除し、返却された `removed_files` リストの各エントリに対し STATE_DB エントリを 1:1 で削除する。**`AUTO_TECHSUPPORT_FEATURE` の値は本処理では参照されない** (GLOBAL のみ評価)。

### 3. その他

- CONFIG_DB への書込: **なし**。両 script とも CONFIG_DB は `db.get` のみで参照 (`AUTO_TS=AUTO_TECHSUPPORT|GLOBAL` / `FEATURE.format(container)=AUTO_TECHSUPPORT_FEATURE|<feat>`)。
- APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB への書込: **なし**。両 script は `db.connect(CFG_DB)` と `db.connect(STATE_DB)` のみで、他 DB に接続しない (`coredump_gen_handler.py:69-71`, `techsupport_cleanup.py:52-54`)。
- SAI 呼出: **なし**。ASIC は非経由 (techsupport は OS レベルの diagnostic 収集に閉じる)。
- Notification / Pub/Sub: **なし**。`NotificationProducer` / `ProducerStateTable` / `publish` の使用なし。SonicV2Connector の素の `set`/`delete` のみで、keyspace 通知は Redis 側で発火するが購読クライアントは存在しない。

## まとめ (本文 `<!-- side-effects -->` ブロックに転記する内容)

- **STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO|<dump>` への SET** (techsupport 生成成功時、`timestamp`/`event_type`/`core_dump`/`container`)
- **STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO|<dump>` の DELETE** (techsupport rotate 時、GLOBAL の `max_techsupport_limit` 経路)
- CONFIG_DB / APPL_DB / COUNTERS_DB / ASIC_DB への副次書込み: なし
- SAI 呼出: なし

## 証跡

- `sonic-utilities/scripts/coredump_gen_handler.py:1-82` (とくに L69-71 の `db.connect`)
- `sonic-utilities/scripts/techsupport_cleanup.py:1-59` (とくに L13-18 の `clean_state_db_entries`)
- `sonic-utilities/utilities_common/auto_techsupport_helper.py:43-60, 302-338` (TS_MAP 定義 / `write_to_state_db` / `invoke_ts_command_rate_limited`)
