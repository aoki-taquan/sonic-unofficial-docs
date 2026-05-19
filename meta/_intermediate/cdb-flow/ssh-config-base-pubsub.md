# ssh-config-base — Phase G pubsub 調査証跡

## 調査対象

- テーブル: `SSH_SERVER|POLICIES`
- ハンドラプロセス: `hostcfgd` (`sonic-host-services/scripts/hostcfgd`)

## 購読方式

`hostcfgd` は `ConfigDBConnector.subscribe()` + `listen()` による **Redis keyspace 通知** で `SSH_SERVER` テーブルの変更を受信する。`swsscommon.SubscriberStateTable` / `ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE) は使用しない。

```python
# hostcfgd L2478
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
```

```python
# hostcfgd L2534
self.config_db.listen(init_data_handler=self.load)
```

## 起動時スナップショット

`listen(init_data_handler=self.load)` により Subscribe ループ開始前に `self.load()` が呼ばれ、`init_data['SSH_SERVER']` を一括スナップショットとして取得・適用する。

```python
# hostcfgd L2244
ssh_server = init_data['SSH_SERVER']
...
# hostcfgd L2265
self.sshscfg.load(ssh_server)
```

`SshServer.load()` → `policies_update()` → `set_policies()` で sshd_config に書き込む。

## 変更時ハンドラ

```python
# hostcfgd L2297-2299
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
```

keyspace 通知ペイロードは操作名 (`hset`/`del`) のみ。フィールド値は `HGETALL` で再取得される。

## 他プロセスによる購読

`SSH_SERVER` テーブルを購読する他プロセスは存在しない。`orchagent` / `syncd` / `mgrd` 等は SSH 設定を購読しない。

## サービス再起動トリガー

変更ハンドラ内で `sshd -T` 検証成功後に `systemctl restart ssh` を呼ぶ（`hostcfgd` L1154）。
