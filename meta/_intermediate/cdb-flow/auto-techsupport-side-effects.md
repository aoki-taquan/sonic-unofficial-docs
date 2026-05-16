# auto-techsupport — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / AUTO_TECHSUPPORT`、`CONFIG_DB / AUTO_TECHSUPPORT_FEATURE`
対象スクリプト:

- `sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py`

## スキャン結果

### STATE_DB 書込

`write_to_state_db()` (`auto_techsupport_helper.py:302-310`) が
`invoke_ts_command_rate_limited()` → `handle_core_dump_creation_event()` 経由で呼出。

```python
# auto_techsupport_helper.py:302-310
def write_to_state_db(db, timestamp, ts_dump, event_type, event_data, container=None):
    name = strip_ts_ext(ts_dump)
    key = TS_MAP + "|" + name          # "AUTO_TECHSUPPORT_DUMP_INFO|<ts_dump_name>"
    db.set(STATE_DB, key, TIMESTAMP, str(timestamp))
    db.set(STATE_DB, key, EVENT_TYPE, event_type)
    for event_data_key, event_data_value in event_data.items():
        db.set(STATE_DB, key, event_data_key, event_data_value)
    if container:
        db.set(STATE_DB, key, CONTAINER, container)
```

書込フィールド:

| フィールド定数 | 値 | 内容 |
|---|---|---|
| `TIMESTAMP` | `"timestamp"` | Unix epoch (int) |
| `EVENT_TYPE` | `"event_type"` | `"core"` または `"memory"` |
| `CORE_DUMP` | `"core_dump"` | core ファイル名 (event=core 時) |
| `CONTAINER` | `"container_name"` | container 名 (任意) |

STATE_DB エントリの削除:

`techsupport_cleanup.py` の `clean_state_db_entries()` が `db.delete(STATE_DB, TS_MAP + "|" + name)` でエントリを削除。

### ファイルシステム `/var/dump`

- **write**: `invoke_ts_cmd()` が `show techsupport --silent --global-timeout 60 --since <since>` をサブプロセス実行 → `/var/dump/sonic_dump_*tar*` を生成。
- **delete**: `cleanup_process()` (`auto_techsupport_helper.py:171-197`) が `os.remove()` で古いダンプファイルを削除。

### systemd 経路

`coredump-compress.service` が kernel coredump イベントを受けて本スクリプトを起動:

```
systemd → coredump-compress.service
  → ExecStart: coredump_gen_handler.py <core_name> <container>
    → handle_core_dump_creation_event()
    → handle_coredump_cleanup()
```

### APPL_DB / その他 DB への副次書込

0 件。`Producer` / `Notification` / `publish` も使用なし。

## 副次書込まとめ

| 副次 DB | 操作 | キーパターン | フィールド | evidence |
|---|---|---|---|---|
| STATE_DB | set | `AUTO_TECHSUPPORT_DUMP_INFO\|<ts_dump_name>` | `timestamp`, `event_type`, `core_dump`, `container_name` | `auto_techsupport_helper.py:302-310` |
| STATE_DB | delete | `AUTO_TECHSUPPORT_DUMP_INFO\|<name>` | (全削除) | `techsupport_cleanup.py:13-18` |
| FS `/var/dump` | write | `sonic_dump_*tar*` | techsupport アーカイブ | `auto_techsupport_helper.py:232-254` |
| FS `/var/dump` | delete | `sonic_dump_*` (古いファイル) | — | `auto_techsupport_helper.py:171-197` |
| CONFIG_DB | なし | — | — | 読取専用 |
| APPL_DB | なし | — | — | ヒット 0 件 |
