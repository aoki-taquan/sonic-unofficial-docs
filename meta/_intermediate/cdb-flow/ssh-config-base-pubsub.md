# ssh-config-base — Phase G 通信メカニズム 調査ノート

## 調査対象

- `sonic-host-services/scripts/hostcfgd`

## ConfigDBConnector.subscribe() 呼び出し

`HostConfigDaemon.__init__()` は `ConfigDBConnector()` を使用し (`hostcfgd:2166`)、`config_db.connect(wait_for_init=True, retry_on=True)` で接続する (`hostcfgd:2167`)。

購読登録 (`hostcfgd:2478`):

```python
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
```

`ConfigDBConnector.subscribe()` は Redis keyspace 通知（`__keyspace@4__:SSH_SERVER|*` パターン）を利用する。

## ssh_handler コールバック

```python
# hostcfgd L2297-2302
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
    syslog.syslog(syslog.LOG_INFO, 'SSH Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

- `SshServer.policies_update()` → `set_policies()` で `/etc/ssh/sshd_config` 更新 + `systemctl restart ssh`
- `PamLimitsCfg.update_config_file()` で PAM limits ファイル更新

## 購読者の有無

- `SSH_SERVER` テーブルを購読する他のデーモン: **なし**
- orchagent は `SSH_SERVER` を購読しない（SAI 非経由のホスト機能）
- syncd / STATE_DB / APPL_DB への書き込み: **なし**

## 起動時一括読み取り

`HostConfigDaemon.load()` → `SshServer.load(ssh_server)` で起動時に CONFIG_DB の既存エントリを一括取得し `set_policies()` を実行 (`hostcfgd:2201-2202`)。
