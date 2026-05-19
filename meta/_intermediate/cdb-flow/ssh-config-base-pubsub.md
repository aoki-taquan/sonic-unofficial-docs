# SSH_SERVER テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SSH_SERVER` テーブル（`SSH_SERVER|POLICIES` シングルトン）。

## 1. 購読 API — `ConfigDBConnector.subscribe()` (keyspace 通知ベース)

`hostcfgd` は `swsscommon.ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE) を**使わず**、`swsscommon` Python ラッパ `ConfigDBConnector.subscribe()` でハンドラを登録する。

```python
# sonic-host-services/scripts/hostcfgd:2478
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
# ...
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

- `ConfigDBConnector.listen()` が内部で Redis **keyspace 通知** (`__keyspace@4__:SSH_SERVER|*` を PSUBSCRIBE) を購読し、マッチしたコールバックへ `(key, op, data)` をディスパッチする。
- CONFIG_DB は永続前提のため TTL は設定されない。
- `NotificationProducer` / `PUBLISH` による明示的な通知は送出されない。

## 2. make_callback のラッパ構造

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

- `key`: `SSH_SERVER|POLICIES` の右辺 `POLICIES`。
- `op`: `data is None` なら `DEL`、それ以外は `SET`（Redis 操作種別は区別しない）。
- `data`: keyspace 通知後に hostcfgd が `HGETALL` で再取得した dict（通知ペイロードは操作名のみ）。

## 3. ssh_handler — ハンドラ呼び出しシーケンス

```python
# hostcfgd:2297-2299
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
    syslog.syslog(syslog.LOG_INFO, 'SSH Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

処理フロー:
1. `SshServer.policies_update('POLICIES', data)` が `ports` を `,` 区切りリストに変換して `self.policies` を更新し、`modify_conf_file()` → `set_policies()` で `/etc/ssh/sshd_config` を書き換える。
2. `PamLimitsCfg.update_config_file()` が `max_sessions` に基づき PAM limits ファイルを再生成する。
3. `syslog` に `INFO` レベルで key/op/data を記録する。

## 4. 購読者一覧

| 購読者 | 購読 API | 購読テーブル | ハンドラ |
|--------|---------|------------|--------|
| `hostcfgd` (`SshServer` + `PamLimitsCfg`) | `ConfigDBConnector.subscribe()` | `SSH_SERVER` | `ssh_handler` |

`hostcfgd` 以外で `SSH_SERVER` テーブルを購読するプロセスは存在しない。`orchagent` / `syncd` / `mgrd` などは `SSH_SERVER` テーブルを参照しない（SSH は SAI 非経由でスイッチ ASIC と無関係）。

## 5. keyspace 通知パターン

| Redis 通知 | hostcfgd 受信 |
|-----------|-------------|
| `__keyspace@4__:SSH_SERVER\|POLICIES` `hset` | `ssh_handler("POLICIES", SET, {...})` |
| `__keyspace@4__:SSH_SERVER\|POLICIES` `del`  | `ssh_handler("POLICIES", DEL, {})` |

dbId は CONFIG_DB の通常 4（`database_config.json` 既定）。

## 6. 起動時スナップショット

`config_db.listen(init_data_handler=self.load)` (hostcfgd:2528) により Subscribe ループ開始前に `HostConfigDaemon.load()` が呼ばれる。

```python
# hostcfgd:2245,2265
ssh_server = init_data['SSH_SERVER']
self.sshscfg.load(ssh_server)
```

`SshServer.load()` は `POLICIES` キーが存在すれば `policies_update('POLICIES', ...)` を `modify_conf=False` で呼び（ファイル書き換えを遅延）、最後に `modify_conf_file()` でまとめて適用する。これにより起動直後に既存の `SSH_SERVER|POLICIES` エントリが `sshd_config` に反映される。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `SSH_SERVER` テーブルは `swsscommon.ConsumerStateTable` (channel ベース) の購読者なし。
- `NotificationProducer` で SSH_SERVER 関連通知を出す箇所はなし。
- 結論: `SSH_SERVER` は **CONFIG_DB → hostcfgd (keyspace 通知) → ファイル書き換え + PAM limits** の一方向で完結し、APPL_DB / STATE_DB の中継・通知パスを持たない。

## 8. 参考行番号

- `sonic-host-services/scripts/hostcfgd`
  - 2458-2466: `make_callback`
  - 2478: `subscribe('SSH_SERVER', ...)`
  - 2528: `self.config_db.listen(init_data_handler=self.load)`
  - 2297-2299: `ssh_handler`
  - 2245, 2265: `HostConfigDaemon.load()` の SSH_SERVER 取得 + `SshServer.load()`
  - 1045-1075: `SshServer.load()` + `policies_update()`
