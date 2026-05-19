# DEVICE_NEIGHBOR_METADATA — Phase G (pubsub) 中間調査

対象ページ: `docs/reference/config-db/device-neighbor-metadata.md`

---

## 調査対象プロセスと通信方式

### bgpcfgd (BGPDataBaseMgr / BGPPeerMgrBase)

**購読 API**: `swsscommon.SubscriberStateTable`  
**ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:49`

```python
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

`BGPDataBaseMgr` は `managers_db.py:4-27` で定義され、`set_handler` で `directory.put()` に書き込む。  
`main.py:76` で `BGPDataBaseMgr("CONFIG_DB", CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME)` として登録される。

- **PSUBSCRIBE パターン**: `__keyspace@4__:DEVICE_NEIGHBOR_METADATA|*`
- **SELECT_TIMEOUT**: 1000 ms (`runner.py:21`)
- **イベントペイロード**: `key, op, fvs = subscriber.pop()` — key にエントリ名、op に `SET`/`DEL`、fvs にフィールド値

### pfcwd

`pfcwd/main.py:98-107` の `get_server_facing_ports()` は `db.get_table('DEVICE_NEIGHBOR_METADATA', ...)` で一括スナップショット取得。  
**Subscribe ではなく一回限りの HGETALL + HGET**。実行時の継続的な購読は行わない。

### その他

- `show interfaces neighbor expected` (`sonic-utilities/show/interfaces/__init__.py`): `get_table` によるスナップショット、購読なし。
- `lldpmgrd`: keyspace 通知経由で変更を受け取る可能性があるが、主要な参照は起動時スナップショット。
- `db_migrator`: マイグレーション実行時の一回限りスナップショット読み込み。

---

## 結論

`DEVICE_NEIGHBOR_METADATA` を **継続的に subscribe する consumer は bgpcfgd (BGPDataBaseMgr) のみ**。  
pfcwd / show コマンド / db_migrator は一回限りのスナップショット取得（HGETALL/HGET）を使用する。
