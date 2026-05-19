# ssh-sftp pubsub 調査ノート (Phase G)

## 調査対象

- `sonic-host-services/scripts/hostcfgd`
- テーブル: `SSH_SFTP`（存在しない）、`SSH_SERVER`（間接影響）

## 結論

`SSH_SFTP` テーブルは CONFIG_DB に定義されていない。SFTP サブシステムを直接購読するプロセスは存在しない。

- `hostcfgd` は `SSH_SERVER` テーブルを `ConfigDBConnector.subscribe()` で購読している（L2478）
- SFTP に影響する変更は `SSH_SERVER` 経由のみ（暗号スイート・ポート・セッション上限）
- `Subsystem sftp` 行自体は `SSH_CONFIG_NAMES` (L67-75) に含まれず、keyspace 通知によって変更されない

## 購読登録コード

```python
# hostcfgd L2478
config_db.subscribe('SSH_SERVER', self.ssh_handler)
```

## ハンドラ

```python
# hostcfgd L2297-2299
def ssh_handler(self, key, op, data):
    self.sshscfg.policies_update(key, data)
    self.pamLimitsCfg.update_config_file(self.config_db)
```

## SFTP 行が変更されない根拠

`SSH_CONFIG_NAMES` (L67-75) に `Subsystem` キーなし。`set_policies()` は `SSH_CONFIG_NAMES` のキーのみを sshd_config に書き込む。

## 通知方式

Redis keyspace 通知 (`PSUBSCRIBE __keyspace@4__:SSH_SERVER|*`)。`swsscommon.SubscriberStateTable` は使用しない。
