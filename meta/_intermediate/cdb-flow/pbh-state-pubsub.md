# pbh-state pubsub (Phase G) — 調査ノート

## 対象テーブル

`STATE_DB PBH_CAPABILITIES`

## 書き込み側の通信方式

`PbhCapabilities` は `swsscommon::Table` を使って STATE_DB へ直接書き込む (`pbhcap.cpp:289`)。

```cpp
// pbhcap.cpp:288-289
DBConnector PbhCapabilities::stateDb(PBH_STATE_DB_NAME, PBH_STATE_DB_TIMEOUT);
Table PbhCapabilities::capTable(&stateDb, STATE_PBH_CAPABILITIES_TABLE_NAME);
```

`Table::set()` は Redis `HSET` を実行するのみで、`ProducerStateTable` のような
チャネル PUBLISH を伴わない。書き込み後に `__keyspace@6__:PBH_CAPABILITIES|*` への
keyspace 通知は Redis サーバー設定次第で発火しうるが、それを購読するプロセスは
現行実装に存在しない。

## 読み取り側 (sonic-utilities) の通信方式

`config/plugins/pbh.py` の `pbh_capabilities_query()` は
`db.get_all(sdb_id, "PBH_CAPABILITIES|<key>")` で `HGETALL` を実行する。
これはコマンド実行時の **ワンショットスナップショット** であり、継続的な購読は行わない。

```python
# pbh.py:492-498
def pbh_capabilities_query(db, key):
    sdb_id = db.STATE_DB
    sdb_sep = db.get_db_separator(sdb_id)
    cap_map = db.get_all(sdb_id, "{}{}{}".format(
        str(PBH_CAPABILITIES_SDB), sdb_sep, str(key)))
    if not cap_map:
        return None
    return cap_map
```

## 購読プロセスの不在

`PBH_CAPABILITIES` を `SubscriberStateTable` / `ConsumerStateTable` /
`ConfigDBConnector.subscribe()` で継続購読するプロセスは sonic-swss / sonic-utilities /
sonic-host-services のいずれにも存在しない。

## 購読方式サマリ

| コンポーネント | 方式 | API | タイミング |
|--------------|------|-----|---------|
| `PbhCapabilities` (orchagent) | STATE_DB 書き込み専用 | `Table::set()` — チャネル PUBLISH なし | orchagent 起動時 1 回のみ |
| `config pbh *` (sonic-utilities) | スナップショット読み取り | `db.get_all()` → Redis `HGETALL` | `config pbh` サブコマンド実行時のみ |

継続的 pub/sub 経路は存在しない。

## ソース証跡

- `sonic-swss/orchagent/pbh/pbhcap.cpp:288-289` — `Table` (非 ProducerStateTable) 宣言
- `sonic-swss/orchagent/pbh/pbhcap.cpp:381,405,420,437` — `Table::set()` 呼び出し
- `sonic-utilities/config/plugins/pbh.py:492-498` — `pbh_capabilities_query()` 実装
- `sonic-utilities/config/plugins/pbh.py:670,781,1090,1218,1351` — 各サブコマンドの呼び出し箇所
