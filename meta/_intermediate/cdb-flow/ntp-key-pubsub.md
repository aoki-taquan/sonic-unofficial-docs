# NTP_KEY — 通信メカニズム (Phase G)

生成日: 2026-05-19

## 調査対象

- `sonic-host-services/scripts/hostcfgd` L2458–2528 (`register_callbacks`, `make_callback`, `start`)
- `sonic-host-services/scripts/hostcfgd` L2387–2391 (`ntp_srv_key_handler`)
- `sonic-host-services/scripts/hostcfgd` L1272–1406 (`NtpCfg` クラス)
- `sonic-host-services/scripts/hostcfgd` L2241–2275 (`load` 初期化スナップショット)

## 購読方式の確認

`ConfigDBConnector.subscribe()` API を使用:

```python
# hostcfgd:2516-2517
self.config_db.subscribe(swsscommon.CFG_NTP_KEY_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

`swsscommon.CFG_NTP_KEY_TABLE_NAME` は `"NTP_KEY"` に解決される（YANG container 名と一致）。

同一ハンドラ (`ntp_srv_key_handler`) が `NTP_SERVER` にも登録されている:

```python
# hostcfgd:2514-2515
self.config_db.subscribe(swsscommon.CFG_NTP_SERVER_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

`NTP_GLOBAL` は別ハンドラ (`ntp_global_handler`) が担当。

## make_callback の動作

```python
# hostcfgd:2458-2466
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

- `data is None` のとき `op="DEL"`
- それ以外は `op="SET"` (`HDEL`/`HSET` の種別は区別しない)
- keyspace 通知のペイロードは操作名のみ。フィールド値は通知後に `get_table()` で全件取得する。

## ntp_srv_key_handler の特異点

```python
# hostcfgd:2387-2391
def ntp_srv_key_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_NOTICE, 'Handling NTP server/key config')
    self.ntpcfg.ntp_srv_key_update(
        self.config_db.get_table(swsscommon.CFG_NTP_SERVER_TABLE_NAME),
        self.config_db.get_table(swsscommon.CFG_NTP_KEY_TABLE_NAME))
```

ハンドラが受け取る `key`/`op`/`data` を個別処理せず、`get_table()` で NTP_KEY と NTP_SERVER の**全件スナップショット**を取得して `ntp_srv_key_update()` に渡す。これは SET/DEL 双方で同一のフルリロードが走ることを意味し、個別フィールドの差分処理は行わない。

## 主ループとリッスン方式

```python
# hostcfgd:2527-2528
def start(self):
    self.config_db.listen(init_data_handler=self.load)
```

`ConfigDBConnector.listen()` が内部で Redis keyspace 通知 PSUBSCRIBE を開始する。CONFIG_DB (DB 4) の `NTP_KEY|*` に対する PSUBSCRIBE パターンは `__keyspace@4__:NTP_KEY|*`。

## 起動時スナップショット

```python
# hostcfgd:2255-2257, 2272
ntp_global = init_data.get(swsscommon.CFG_NTP_GLOBAL_TABLE_NAME)
ntp_servers = init_data.get(swsscommon.CFG_NTP_SERVER_TABLE_NAME)
ntp_keys = init_data.get(swsscommon.CFG_NTP_KEY_TABLE_NAME)
...
self.ntpcfg.load(ntp_global, ntp_servers, ntp_keys)
```

`listen(init_data_handler=self.load)` により、Subscribe ループ開始前に `NtpCfg.load()` がスナップショットをキャッシュに適用する。chrony 設定は起動時テンプレートが担うため、再起動はトリガーしない。

## 他購読者の存在確認

NTP_KEY を購読する他プロセス（orchagent / mgrd / syncd 等）は `sonic-swss/` 内に存在しない。`ConfigDB` レベルの keyspace 通知を購読するのは `hostcfgd` のみ。

## CONFIG_DB DB インデックス

CONFIG_DB = DB 4。keyspace 通知パターン: `__keyspace@4__:NTP_KEY|*`。TTL なし（NTP_KEY は永続エントリ）。
