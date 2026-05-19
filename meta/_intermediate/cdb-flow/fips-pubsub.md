# FIPS — Phase G pubsub 調査メモ

## 調査対象

- `sonic-host-services/scripts/hostcfgd` L2456-2509 (register_callbacks)、L2433-2436 (fips_config_handler)、L2527-2528 (start/listen)
- 調査日: 2026-05-19

## 購読メカニズム

`hostcfgd` の `HostConfigDaemon.register_callbacks()` が `ConfigDBConnector.subscribe('FIPS', make_callback(self.fips_config_handler))` を呼ぶ。

これは **Redis keyspace 通知 (PSUBSCRIBE `__keyspace@4__:FIPS|*`)** を使用する `ConfigDBConnector.subscribe()` 方式であり、`swsscommon.SubscriberStateTable` や `ConsumerStateTable` は使用しない。

## 購読者一覧

| 購読者 | 購読 API | DB | テーブル | ハンドラ |
|--------|---------|----|---------|---------| 
| `hostcfgd` (`HostConfigDaemon`) | `ConfigDBConnector.subscribe()` | CONFIG_DB (dbId=4) | `FIPS` | `fips_config_handler` → `FipsCfg.fips_handler` → `FipsCfg.load()` + `update()` |

`FIPS` テーブルを購読する他プロセスは存在しない。

## 特記事項：fips_config_handler の HGETALL 再取得

```python
# hostcfgd:2433-2436
def fips_config_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_INFO, 'FIPS table handler...')
    data = self.config_db.get_table("FIPS")   # keyspace 通知の data は捨て、全テーブルを再取得
    self.fipscfg.fips_handler(data)
```

keyspace 通知ペイロード（引数 `data`）は即座に破棄され、`config_db.get_table("FIPS")` で CONFIG_DB 全体を **HGETALL** し直す。個別フィールドの差分は使用しない。これにより、フィールド更新が複数到着しても最終状態のみを処理する（デバウンス効果あり）。

## 起動時スナップショット

`daemon.start()` は `config_db.listen(init_data_handler=self.load)` (hostcfgd:2527-2528) を呼ぶ。`listen()` は Subscribe ループ開始前に `init_data_handler` として `HostConfigDaemon.load()` を一度呼び出す。`load()` の内部で `fips_cfg = init_data.get('FIPS', {})` → `self.fipscfg.load(fips_cfg)` が実行され (hostcfgd:2254,2271)、起動時に既存 CONFIG_DB エントリを一括適用する。

## make_callback の動作

```python
def make_callback(func):
    def callback(table, key, data):
        if data is None:
            op = "DEL"
            data = {}
        else:
            op = "SET"
        return func(key, op, data)
    return callback
```

- `data is None` → `op = "DEL"`（キー削除）
- それ以外 → `op = "SET"`

ただし `fips_config_handler` は `op` の値を使用しておらず、常に `config_db.get_table("FIPS")` で全テーブルを取得するため DEL/SET の区別は実質的に無意味。
