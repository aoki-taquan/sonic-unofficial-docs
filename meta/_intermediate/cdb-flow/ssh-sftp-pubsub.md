# ssh-sftp — Phase G pubsub 調査ノート

## 調査対象

`SSH_SFTP` テーブルは CONFIG_DB に存在しない。SFTP サブシステムは `SSH_SERVER|POLICIES` の管理外（OS テンプレート固定）。Phase G では「SFTP に関係する通信メカニズム」として `SSH_SERVER` テーブルへの購読経路を整理する。

## ソース確認

### hostcfgd L2478（subscribe 登録）

```python
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
```

`SSH_SERVER` テーブル専用の subscribe 登録が存在する。`SSH_SFTP` に対応する subscribe は存在しない（テーブル自体が未定義）。

### hostcfgd L2297-2301（ssh_handler）

```python
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file()
    syslog.syslog(syslog.LOG_INFO, 'SSH Update: key: {}, op: {}, data: {}'.format(key, op, data))
```

`ssh_handler` は `SSH_SERVER|POLICIES` の変更をトリガーに `set_policies()` を呼ぶが、`Subsystem sftp` 行は `SSH_CONFIG_NAMES`（L67-75）に含まれないため変更されない。

## 結論

- `SSH_SFTP` テーブルへの購読経路は存在しない（テーブル未定義）
- SFTP サブシステムに対する Redis keyspace 通知・PUBLISH/SUBSCRIBE・swsscommon SubscriberStateTable のいずれも使用されない
- SFTP に影響する唯一の通知経路は `SSH_SERVER` 購読の副産物（sshd_config の再生成時に Subsystem 行が引き継がれるだけ）
- Redis PUBLISH チャネルは使用なし。ConfigDBConnector.subscribe() の keyspace 通知のみ（`SSH_SERVER` テーブルのみ対象）
