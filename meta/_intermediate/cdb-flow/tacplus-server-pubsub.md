# TACPLUS_SERVER — Phase G: pubsub 調査メモ

## 調査対象

`sonic-host-services/scripts/hostcfgd` (コミット c5bbbe8b07b96f078fa4b761316627404b01bd04)

## Subscribe 登録の確認

```
hostcfgd:2471  self.config_db.subscribe('TACPLUS', make_callback(self.tacacs_global_handler))
hostcfgd:2472  self.config_db.subscribe('TACPLUS_SERVER', make_callback(self.tacacs_server_handler))
```

`ConfigDBConnector.subscribe()` は内部で `PSUBSCRIBE __keyspace@<dbId>__:<TABLE>|*` を登録する。
`swsscommon.SubscriberStateTable` / `ConsumerStateTable` は使用しない。

## listen / init_data_handler の確認

```
hostcfgd:2528  self.config_db.listen(init_data_handler=self.load)
```

`listen()` は subscribe ループ開始前に `init_data_handler` (= `HostConfigDaemon.load`) を呼び出す。
`load_independent_config()` が `init_data['TACPLUS_SERVER']` / `init_data['TACPLUS']` を `AaaCfg.load()` に渡す（hostcfgd:2221-2230）。

## ハンドラ実装の確認

```python
# hostcfgd:2303-2308
def tacacs_server_handler(self, key, op, data):
    self.aaacfg.tacacs_server_update(key, data)
    log_data = copy.deepcopy(data)
    if 'passkey' in log_data:
        log_data['passkey'] = obfuscate(log_data['passkey'])
    syslog.syslog(LOG_INFO, 'TACPLUS_SERVER update: key: {}, op: {}, data: {}'.format(...))

# hostcfgd:2310-2315
def tacacs_global_handler(self, key, op, data):
    self.aaacfg.tacacs_global_update(key, data)
    ...
    syslog.syslog(LOG_INFO, 'TACPLUS Global update: ...')
```

## tacacs_server_update() の実装

```python
# hostcfgd:473-481
def tacacs_server_update(self, key, data, modify_conf=True):
    if data == {}:                      # DEL 操作
        if key in self.tacplus_servers:
            del self.tacplus_servers[key]
    else:                               # SET 操作
        self.tacplus_servers[key] = data
    if modify_conf:
        self.modify_conf_file()
```

## make_callback() の op 判定

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

`DEL` 時は `data={}` が渡るため `tacacs_server_update()` の `data == {}` 分岐でキーを削除する。

## PAM 再生成の流れ

```
CONFIG_DB TACPLUS_SERVER キー変更 (HSET / DEL)
  → Redis keyspace PUBLISH "__keyspace@4__:TACPLUS_SERVER|<ip>"
  → ConfigDBConnector.listen() がパターンマッチ
  → make_callback() で (key, op={SET|DEL}, data) 生成
     (keyspace 通知のペイロードは操作名のみ; 値は HGETALL で再取得)
  → tacacs_server_handler(key, op, data)       [hostcfgd:2303-2308]
     → AaaCfg.tacacs_server_update(key, data)  [hostcfgd:473-481]
          → self.tacplus_servers 更新
          → modify_conf_file()                 [hostcfgd:641-870]
               → TACPLUS_SERVER × TACPLUS|global をマージ
               → priority でソート (int変換; 不正値で ValueError)
               → common-auth-sonic.j2 / tacplus_nss.conf.j2 でテンプレ展開
               → /etc/pam.d/common-auth-sonic (atomic rename)
               → /etc/tacplus_nss.conf
               → /etc/nsswitch.conf の passwd 行書換
               → notify_audisp_tacplus_reload_config() → SIGHUP
```

## TACPLUS_SERVER 以外の購読者

TACPLUS_SERVER を CONFIG_DB から直接 subscribe する他のプロセスは存在しない。
（grep `TACPLUS_SERVER` across orchagent, syncd, bgpd, etc. → 0 ヒット。
  PAM モジュール自体は Redis を subscribe せず、/etc/pam.d/common-auth-sonic を認証時に読む）

## 起動時スナップショット

`AaaCfg.load(aaa, tac_global_conf, tacplus_conf, ...)` (hostcfgd:399-417) は
subscribe ループ開始前に全テーブルのスナップショットを一括適用する。
`TACPLUS_SERVER` は `tacplus_conf` として渡され `tacacs_server_update(row, data, modify_conf=False)` で
メモリに反映。最後に `modify_conf_file()` を 1 回呼ぶ（hostcfgd:417）。
