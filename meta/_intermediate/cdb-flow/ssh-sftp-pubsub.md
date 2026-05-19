# SSH SFTP サブシステム — 通信メカニズム (Phase G) 解析メモ

対象: `SSH_SFTP` テーブルは存在しない。SFTP サブシステムに関連する CONFIG_DB 購読経路は `SSH_SERVER` テーブルを購読する `hostcfgd` 経由のみ。

## 1. SSH_SFTP 専用テーブルの不在

`sonic-net/sonic-buildimage` の YANG / CONFIG_DB スキーマに `SSH_SFTP` テーブルは定義されていない。Redis keyspace 上に `SSH_SFTP|*` キーは存在せず、購読対象となるチャネルも存在しない。

## 2. SSH_SERVER 経由の間接的な通知経路

SFTP サブシステムに間接影響を与える唯一の CONFIG_DB 購読経路は `SSH_SERVER|POLICIES`:

```python
# sonic-host-services/scripts/hostcfgd:2478
self.config_db.subscribe('SSH_SERVER', make_callback(self.ssh_handler))
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

`ConfigDBConnector.listen()` が Redis の **keyspace 通知** (`PSUBSCRIBE "__keyspace@4__:*"`) を購読し、`SSH_SERVER|*` に一致するイベント（`hset`/`del`）を `ssh_handler()` にディスパッチする。`SSH_CONFIG_NAMES`（hostcfgd:67-75）に `Subsystem` キーが存在しないため、ディスパッチ後の `set_policies()` でも SFTP サブシステムは変更されない。

## 3. 通知メカニズムの詳細

| 項目 | 値 |
|------|----|
| 購読方式 | `ConfigDBConnector.subscribe()` による keyspace 通知 (PSUBSCRIBE) |
| keyspace パターン | `__keyspace@4__:*` (CONFIG_DB dbId=4、全キーを包括) |
| テーブル絞り込み | `listen()` ループ内で `table in self.handlers` 条件判定（`SSH_SERVER` 登録済みのみコールバック発火） |
| channel ベース PUBLISH | **使用しない**（CONFIG_DB は `HSET` のみ。ConsumerStateTable 形式ではない） |
| TTL | CONFIG_DB 全エントリで未設定（永続前提） |
| SFTP 専用チャンネル | **なし** |

## 4. 外部購読者

`SSH_SERVER` テーブルを購読するプロセスは `hostcfgd` のみ。SFTP サブシステムを直接購読する orchagent / translib / gnmi への購読コードは sonic-swss / sonic-gnmi いずれにも存在しない（grep 確認）。

## 証跡

- `sonic-host-services/scripts/hostcfgd:2478` — `config_db.subscribe('SSH_SERVER', ...)`
- `sonic-host-services/scripts/hostcfgd:2528` — `config_db.listen(init_data_handler=self.load)`
- `sonic-swss-common/common/configdb.h:101` — `self.pubsub.psubscribe("__keyspace@{}__:*".format(self.get_dbid(self.db_name)))`
- `sonic-host-services/scripts/hostcfgd:67-75` — `SSH_CONFIG_NAMES`（`Subsystem` キーなし → SFTP 行は変更されない）
