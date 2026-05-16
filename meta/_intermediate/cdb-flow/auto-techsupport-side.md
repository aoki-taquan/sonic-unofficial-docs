# auto-techsupport — Phase F 副次 DB 書込スキャン

対象テーブル: `CONFIG_DB / AUTO_TECHSUPPORT`、`CONFIG_DB / AUTO_TECHSUPPORT_FEATURE`
対象スクリプト:

- `sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-utilities/scripts/techsupport_cleanup.py`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py` (共通ヘルパ)

> 注: タスク文書では `sonic-host-services/scripts/` を起点と記載されているが、当該スクリプトの実体は `sonic-utilities` リポの `scripts/` 配下に存在する（`sonic-host-services` には auto-techsupport 系の Cfg ハンドラは存在せず、coredump-compress / techsupport_cleanup のラッパも sonic-utilities 側）。本スキャンでは実コードのパスに従う。

## スキャン手順

1. helper の DB シンボル定数を抽出:

   ```text
   grep -n "^[A-Z_]* =" auto_techsupport_helper.py
   ```

   結果:

   - `CFG_DB = "CONFIG_DB"`
   - `STATE_DB = "STATE_DB"`
   - `AUTO_TS = "AUTO_TECHSUPPORT|GLOBAL"`
   - `FEATURE = "AUTO_TECHSUPPORT_FEATURE|{}"`
   - `TS_MAP = "AUTO_TECHSUPPORT_DUMP_INFO"`
   - field keys: `TIMESTAMP = "timestamp"`, `EVENT_TYPE = "event_type"`,
     `CORE_DUMP = "core_dump"`, `CONTAINER = "container_name"`
   - event 値: `EVENT_TYPE_CORE = "core"`, `EVENT_TYPE_MEMORY = "memory"`

2. 3 ファイル全行に対し書込系 API (`db.set`, `db.delete`, `db.hset`,
   `Producer`, `Notification`, `publish`) を grep:

   ```text
   grep -nE "db\.(set|delete|hset|hmset)|Producer|Notification|publish" \
        coredump_gen_handler.py techsupport_cleanup.py auto_techsupport_helper.py
   ```

   ヒット (実コード行):

   - `auto_techsupport_helper.py:305`  `db.set(STATE_DB, key, TIMESTAMP, str(timestamp))`
   - `auto_techsupport_helper.py:306`  `db.set(STATE_DB, key, EVENT_TYPE, event_type)`
   - `auto_techsupport_helper.py:308`  `db.set(STATE_DB, key, event_data_key, event_data_value)`
   - `auto_techsupport_helper.py:310`  `db.set(STATE_DB, key, CONTAINER, container)`
   - `techsupport_cleanup.py:18`       `db.delete(STATE_DB, TS_MAP + "|" + name)`
   - 他リポ書込 (`CFG_DB` / `APPL_DB` 系) ヒット **0 件**
   - `Producer` / `Notification` / `publish` ヒット **0 件**

3. 読み取り系 (`db.get`, `db.get_all`, `db.keys`) は副次書込判定の対象外。
   参考までに本タスクで確認した読み取り:

   - `db.get(CFG_DB, AUTO_TS, CFG_STATE)`  (state 判定)
   - `db.get(CFG_DB, AUTO_TS, CFG_CORE_USAGE)` / `CFG_MAX_TS` / `COOLOFF`
   - `db.get(CFG_DB, FEATURE.format(container), CFG_STATE)` / `COOLOFF`
   - `db.keys(STATE_DB, TS_MAP+"*")` / `db.get_all(STATE_DB, ts_key)` (`get_ts_map`)

## 副次書込まとめ

| 副次 DB | 書込/削除 | キーパターン | 書込フィールド | 呼出元 | evidence |
|---|---|---|---|---|---|
| STATE_DB | set (新規/更新) | `AUTO_TECHSUPPORT_DUMP_INFO\|<ts_dump_name>` | `timestamp` / `event_type` / `core_dump` (event=core 時) / `container_name` (任意) | `write_to_state_db()` ← `invoke_ts_command_rate_limited()` ← `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()` | `auto_techsupport_helper.py:302-310`, `coredump_gen_handler.py:46-60` |
| STATE_DB | delete | `AUTO_TECHSUPPORT_DUMP_INFO\|<name>` | (エントリ全削除) | `clean_state_db_entries()` ← `handle_techsupport_creation_event()` | `techsupport_cleanup.py:13-18,43-44` |
| CONFIG_DB | なし | — | — | — | 読み取りのみ (`db.get(CFG_DB, ...)` 計 8 箇所、書込 0 件) |
| APPL_DB | なし | — | — | — | スクリプト 3 本に `APPL_DB` 文字列なし、`APPL_DB` を引数とする `db.set/db.delete` 呼出 0 件 |
| COUNTERS_DB / FLEX_COUNTER_DB | なし | — | — | — | SAI 非経由 (段階 3 トレース: APPL→SAI なし) |
| ASIC_DB / LOGLEVEL_DB | なし | — | — | — | 同上 |
| 通知チャネル (`__keyspace@*__` 以外の publish) | なし | — | — | — | `Notification` / `publish` ヒット 0 件 |

## エントリのライフサイクル

```
CONFIG_DB AUTO_TECHSUPPORT|GLOBAL.state=enabled
  + critical-process core dump 発生
  → coredump_gen_handler.py: handle_core_dump_creation_event()
    → invoke_ts_command_rate_limited()
      → verify_rate_limit_intervals()  (STATE_DB を read)
      → invoke_ts_cmd()                (show techsupport 起動)
      → write_to_state_db()            ★ STATE_DB に dump メタを set
  + max_techsupport_limit 超過時
  → techsupport_cleanup.py: handle_techsupport_creation_event()
    → cleanup_process()                (ファイル削除、削除一覧を返却)
    → clean_state_db_entries()         ★ STATE_DB の対応エントリを delete
```

## 結論

- CONFIG_DB `AUTO_TECHSUPPORT` 系の主購読者は **STATE_DB `AUTO_TECHSUPPORT_DUMP_INFO`
  テーブルへの per-dump メタ書込/削除** という副次効果を持つ。
- それ以外の DB (APPL_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB / LOGLEVEL_DB)
  への副次書込は **存在しない**。
- 副次書込キーはダンプ名 (`sonic_dump_*` から `.tar.gz` 拡張子除去) を `|` 区切りで
  付与するパターンで、`get_ts_map()` を介して container 単位 rate-limit 判定の
  入力に再利用される — STATE_DB が単なるログではなく rate-limit 状態保持の役割を
  兼ねている点に注意。
