# ssh-config — Phase G: 通信メカニズム調査ノート

対象テーブル: `SSH_SERVER`
ソース: `sonic-net/sonic-host-services/scripts/hostcfgd` (コミット c5bbbe8b)

## 購読 API 種別

`SSH_SERVER` テーブルへの変更通知は `hostcfgd` が `ConfigDBConnector.subscribe()` + `listen()` で登録する
Redis keyspace 通知 (PSUBSCRIBE `__keyspace@<dbId>__:SSH_SERVER|*`) で配信される。
`swsscommon.SubscriberStateTable` や `ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE) は使用しない。

```
# hostcfgd:2478
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))

# hostcfgd:2528 (start)
self.config_db.listen(init_data_handler=self.load)
```

## 起動時スナップショット vs. ランタイム購読

- 起動時: `load(init_data)` が `init_data['SSH_SERVER']` を一括スナップショットとして `sshscfg.load(ssh_server)` に渡す (hostcfgd:L2245,L2265)
- ランタイム: `ssh_handler(key, op, data)` が keyspace 通知で逐次呼び出される (hostcfgd:L2297-2299)

## ハンドラシグネチャと make_callback ラッパー

```python
# hostcfgd:make_callback (L2454-2466)
def make_callback(func):
    def callback(table, key, data):
        if data is None:
            op = "DEL"
            data = {}
        else:
            op = "SET"
        return func(key, op, data)
    return callback

# hostcfgd:L2297-2299
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
    syslog.syslog(syslog.LOG_INFO, 'SSH Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

## keyspace 通知フロー

```
config ssh-server set authentication-retries 5
  ↓ HSET "SSH_SERVER|POLICIES" authentication_retries "5"
Redis keyspace PUBLISH "__keyspace@4__:SSH_SERVER|POLICIES"  "hset"
  ↓ ConfigDBConnector.listen() がパターンマッチ
make_callback() で (key, op, data) を生成 (data は None でない → op=SET)
  ↓ HGETALL "SSH_SERVER|POLICIES"  ← 通知後に全フィールド取得
ssh_handler(key="POLICIES", op=SET, data={authentication_retries:"5", ...})
  ↓ SshServer.policies_update() → set_policies()
  ↓ /etc/ssh/sshd_config 更新 + systemctl restart ssh
  ↓ PamLimitsCfg.update_config_file() → /etc/security/limits.conf 更新
```

## 他プロセスの購読有無

`SSH_SERVER` テーブルを購読するプロセスは `hostcfgd` のみ。
orchagent / syncd / translib のいずれも `SSH_SERVER` を参照しない。
`show ssh-server policies` (sonic-utilities) は CONFIG_DB を直接読む (`hgetall`)。

## TTL

CONFIG_DB は永続前提のため TTL は設定されない。

## サービス再起動トリガー

- `SshServer.set_policies()` 成功時: `systemctl restart ssh` (hostcfgd:L1154)
- `PamLimitsCfg.render_conf_file()` 呼び出し: `ssh` サービス再起動なし (PAM limits.conf の読み替えのみ)
- DEL 操作時: `len(ssh_policies) == 0` のため `set_policies()` 未呼出、ssh 再起動なし

## Evidence

- hostcfgd:2478 (`subscribe('SSH_SERVER', ...)`)
- hostcfgd:2528 (`config_db.listen(init_data_handler=self.load)`)
- hostcfgd:2245,2265 (`sshscfg.load(ssh_server)` in `load()`)
- hostcfgd:2297-2299 (`ssh_handler`)
- hostcfgd:2454-2466 (`make_callback` definition)
