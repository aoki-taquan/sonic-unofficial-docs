# SSH_SERVER テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SSH_SERVER` テーブル。

## 1. 購読 API — `ConfigDBConnector.subscribe()` (channel ベースではない)

`hostcfgd` は `swsscommon.SubscriberStateTable` を**直接は使わず**、`swsscommon` Python ラッパ `ConfigDBConnector` の `subscribe(table, callback)` でハンドラを登録する。

```python
# sonic-host-services/scripts/hostcfgd:2478
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
# ...
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` の PSUBSCRIBE) を購読し、テーブル名にマッチしたコールバックへ `(key, op, data)` をディスパッチする。
- channel ベースの `PUBLISH/SUBSCRIBE` (`ConsumerStateTable` 形式) は使用していない。CONFIG_DB は publisher (sonic-cfggen / `config ssh-server`) が `HSET` するのみで明示的な `PUBLISH` を行わず、Redis 側の keyspace notification が変更を通知する。
- TTL は CONFIG_DB の全エントリで設定されない（CONFIG_DB は永続前提）。
- `SSH_SERVER` を購読する他のプロセスは **なし**（grep 確認: `sonic-swss/`, `sonic-gnmi/`, `sonic-sairedis/` に `SSH_SERVER` 購読コードが 0 件）。

## 2. キー単位ディスパッチ

`make_callback()` は以下のラッパを生成する:

```python
# hostcfgd:2454-2466
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

- `key`: `SSH_SERVER|POLICIES` の右辺 (`POLICIES`)。シングルトンテーブルのため常に `POLICIES` のみ。
- `op`: `data is None` の場合 `DEL`、それ以外は `SET`（`HSET` / `DEL` の Redis 操作種別は区別しない）。
- `data`: 通知後に hostcfgd が **HGETALL で再取得した** dict（keyspace 通知本体には値は含まれず操作名のみ）。

## 3. ssh_handler の動作

```python
# hostcfgd:2297-2300
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
    syslog.syslog(syslog.LOG_INFO, 'SSH Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

- `sshscfg.policies_update(key, data)` → `SshServer.set_policies(key, data)` — sshd_config 全フィールドを更新し `systemctl restart ssh` を実行。
- `pamLimitsCfg.update_config_file()` — `max_sessions` を PAM limits ファイルに反映。
- `op=DEL` 時の明示的なフォールバック処理なし（`policies_update` は `data={}` で全フィールド不在として処理される）。

## 4. 起動時スナップショット

`config_db.listen(init_data_handler=self.load)` (hostcfgd:2528) の `init_data_handler` として `HostConfigDaemon.load()` が呼ばれ、Subscribe ループ開始前に `SSH_SERVER` テーブル全体を `init_data['SSH_SERVER']` で一括スナップショット取得して `sshscfg.load()` を適用する（hostcfgd:2265）。

## 5. 外部購読者

`SSH_SERVER` テーブルを購読するプロセスは `hostcfgd` のみ。`orchagent` (sonic-swss) / `mgrd` / `gNMI translib` には `SSH_SERVER` 向けの Consumer / Subscriber は存在しない。

## 証跡

- `sonic-host-services/scripts/hostcfgd:2454-2466` — `make_callback()`
- `sonic-host-services/scripts/hostcfgd:2478` — `config_db.subscribe('SSH_SERVER', ...)`
- `sonic-host-services/scripts/hostcfgd:2528` — `config_db.listen(init_data_handler=self.load)`
- `sonic-host-services/scripts/hostcfgd:2297-2300` — `ssh_handler()`
- `sonic-host-services/scripts/hostcfgd:2265` — `sshscfg.load(ssh_server)`
