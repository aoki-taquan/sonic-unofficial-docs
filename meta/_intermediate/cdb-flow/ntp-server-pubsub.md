# NTP_SERVER — 通信メカニズム (Phase G)

生成日: 2026-05-19

## 調査対象

- `sonic-host-services/scripts/hostcfgd` L2511–2517 (`subscribe` 登録)
- `sonic-host-services/scripts/hostcfgd` L2387–2391 (`ntp_srv_key_handler`)
- `sonic-host-services/scripts/hostcfgd` L1366–1406 (`NtpCfg.ntp_srv_key_update`)
- `sonic-host-services/scripts/hostcfgd` L2241–2275 (`load` 初期化スナップショット)
- `sonic-host-services/scripts/hostcfgd` L111–112 (SIGHUP 無視)
- `sonic-host-services/scripts/hostcfgd` L2527–2528 (`config_db.listen()`)

## 購読方式

`ConfigDBConnector.subscribe()` API を使用:

```python
# hostcfgd:2514-2515
self.config_db.subscribe(swsscommon.CFG_NTP_SERVER_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

`swsscommon.CFG_NTP_SERVER_TABLE_NAME` は `"NTP_SERVER"` に解決される。

`NTP_KEY` も同一ハンドラ (`ntp_srv_key_handler`) に登録されている:

```python
# hostcfgd:2516-2517
self.config_db.subscribe(swsscommon.CFG_NTP_KEY_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

`NTP` (global) は別ハンドラ (`ntp_global_handler`) が担当。

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

- `data is None` のとき `op="DEL"`、それ以外は `op="SET"`
- 個別フィールドの差分は持たない。key/op のみが通知に含まれる。

## ntp_srv_key_handler の特異点

```python
# hostcfgd:2387-2391
def ntp_srv_key_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_NOTICE, 'Handling NTP server/key config')
    self.ntpcfg.ntp_srv_key_update(
        self.config_db.get_table(swsscommon.CFG_NTP_SERVER_TABLE_NAME),
        self.config_db.get_table(swsscommon.CFG_NTP_KEY_TABLE_NAME))
```

- 受け取った `key`/`op`/`data` を無視し、**NTP_SERVER と NTP_KEY の全件スナップショット**を `get_table()` で再取得
- NTP_SERVER の変更でも NTP_KEY の変更でも、同一のフルリロードが走る
- 個別エントリの差分処理は行わない

## キャッシュガード (差分チェック)

```python
# hostcfgd:1383-1386
if self.cache['servers'] == ntp_servers and self.cache['keys'] == ntp_keys:
    syslog.syslog(syslog.LOG_NOTICE, 'NtpCfg: Nothing to update')
    return
```

- 前回キャッシュと全件が同一であれば `systemctl restart chrony` を抑制
- 差分があれば問答無用でフルリスタート（フィールドレベルの差分判定は行わない）

## 主ループとリッスン方式

```python
# hostcfgd:2527-2528
def start(self):
    self.config_db.listen(init_data_handler=self.load)
```

`ConfigDBConnector.listen()` が内部で Redis keyspace 通知 PSUBSCRIBE を開始する。
CONFIG_DB (DB 4) の `NTP_SERVER|*` に対するパターンは `__keyspace@4__:NTP_SERVER|*`。

## 起動時スナップショット

```python
# hostcfgd:2255-2257, 2272
ntp_servers = init_data.get(swsscommon.CFG_NTP_SERVER_TABLE_NAME)
ntp_keys = init_data.get(swsscommon.CFG_NTP_KEY_TABLE_NAME)
...
self.ntpcfg.load(ntp_global, ntp_servers, ntp_keys)
```

`listen(init_data_handler=self.load)` により、Subscribe ループ開始前に `NtpCfg.load()` がスナップショットをキャッシュに適用する。起動時の chrony 再起動はトリガーしない（chrony は起動設定ファイルから読む）。

## SIGHUP の扱い

```python
# hostcfgd:111-112
def signal_handler(sig, frame):
    if sig == signal.SIGHUP:
        syslog.syslog(syslog.LOG_INFO, "HostCfgd: signal 'SIGHUP' is caught and ignoring..")
```

- hostcfgd は SIGHUP を受け取っても**何もしない**
- NTP_SERVER 変更は必ず `systemctl restart chrony`（フルリスタート）
- SIGHUP によるホットリロードは採用されていない

## 他購読者の確認

NTP_SERVER を購読する他プロセス（orchagent / syncd / mgrd 等）は `sonic-swss/` および `sonic-sairedis/` 内に存在しない。CONFIG_DB の keyspace 通知を購読するのは `hostcfgd` のみ。

## CONFIG_DB DB インデックス

CONFIG_DB = DB 4。keyspace 通知パターン: `__keyspace@4__:NTP_SERVER|*`。TTL なし（NTP_SERVER は永続エントリ、YANG `max-elements 10` で上限制約あり）。
