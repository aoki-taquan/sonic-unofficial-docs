# SERIAL_CONSOLE / SSH_SERVER — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SERIAL_CONSOLE` テーブルおよび `SSH_SERVER` テーブル。
Consumer: `hostcfgd` (`SerialConsoleCfg`, `SshServer`, `PamLimitsCfg` クラス)

## 1. 購読 API — `ConfigDBConnector.subscribe()` (channel ベースではない)

`hostcfgd` は `swsscommon.SubscriberStateTable` を**直接は使わず**、`ConfigDBConnector.subscribe(table, callback)` でハンドラを登録する。

```python
# sonic-host-services/scripts/hostcfgd:2478,2481
self.config_db.subscribe('SSH_SERVER',      make_callback(self.ssh_handler))
self.config_db.subscribe('SERIAL_CONSOLE',  make_callback(self.serial_console_config_handler))
# hostcfgd:2528
self.config_db.listen(init_data_handler=self.load)
```

- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` の PSUBSCRIBE) を購読し、テーブル名マッチ時にコールバックへ `(key, op, data)` をディスパッチする。
- `ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE) は使用しない。CONFIG_DB は `HSET` のみで変更され、Redis keyspace notification が通知を生成する。
- CONFIG_DB の全エントリに TTL は設定されない（永続前提）。

## 2. キー単位ディスパッチ

`make_callback()` は以下のラッパを生成する (hostcfgd:2454-2466):

```python
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

- `key`: `POLICIES` 固定（両テーブルとも `|POLICIES` のシングルトンキー）。
- `op`: `data is None` なら `DEL`、それ以外は `SET`。`HSET` / `HDEL` の Redis 操作種別自体は区別しない。
- `data`: keyspace 通知後に hostcfgd が HGETALL で再取得した dict。

## 3. 各ハンドラの動作

| 購読テーブル | ハンドラ (hostcfgd) | 呼び出しメソッド | 副作用 |
|-------------|---------------------|--------------------|--------|
| `SSH_SERVER` | `ssh_handler` (hostcfgd:2297) | `SshServer.policies_update()` → `modify_conf_file()` → `set_policies()` + `PamLimitsCfg.update_config_file()` | `/etc/ssh/sshd_config` 書き換え → `systemctl restart ssh`; PAM limits 更新 |
| `SERIAL_CONSOLE` | `serial_console_config_handler` (hostcfgd:2438) | `SerialConsoleCfg.update_serial_console_cfg()` | キャッシュ差分検出 → `service serial-config restart` |

## 4. サービス再起動トリガー

| トリガー | 操作 | コード |
|---------|------|--------|
| `SSH_SERVER\|POLICIES` 変化 (sshd -T 検証成功) | `systemctl restart ssh` | hostcfgd:1154 |
| `SSH_SERVER\|POLICIES` 変化 (`max_sessions` 含む) | `/etc/security/limits.d/` 更新 (PAM limits) | hostcfgd:1418-1441 |
| `SERIAL_CONSOLE\|POLICIES` 変化 (キャッシュ差分時) | `service serial-config restart` | hostcfgd:2035 |

## 5. 起動時スナップショット

`hostcfgd` は `config_db.listen(init_data_handler=self.load)` (hostcfgd:2528) で Subscribe ループ開始前に `HostConfigDaemon.load()` を一度呼び出し、`init_data['SSH_SERVER']` / `init_data.get('SERIAL_CONSOLE', {})` を一括スナップショットで読み込んで適用する。

- `wait_till_system_init_done()` 完了後に `SshServer.load()` / `SerialConsoleCfg.load()` が適用され、その後 Subscribe ループへ入る (hostcfgd:2237, 2265, 2273)。
- ループ開始後に届く keyspace 通知はすべて差分更新として処理される。

## 6. keyspace 通知パターン

| Redis 通知 | hostcfgd 受信 |
|-----------|---------------|
| `__keyspace@4__:SSH_SERVER\|POLICIES` `hset` | `ssh_handler("POLICIES", SET, {...})` |
| `__keyspace@4__:SSH_SERVER\|POLICIES` `del` | `ssh_handler("POLICIES", DEL, {})` |
| `__keyspace@4__:SERIAL_CONSOLE\|POLICIES` `hset` | `serial_console_config_handler("POLICIES", SET, {...})` |
| `__keyspace@4__:SERIAL_CONSOLE\|POLICIES` `del` | `serial_console_config_handler("POLICIES", DEL, {})` |

dbId は CONFIG_DB の通常 4 (sonic-swss-common の `database_config.json` 既定)。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `SSH_SERVER` / `SERIAL_CONSOLE` テーブルは `swsscommon.ConsumerStateTable` (channel ベース) の購読者なし。`hostcfgd` のみが keyspace 通知経由で購読。
- `NotificationProducer` でこれらテーブルに関連する通知を出す箇所は SONiC ソース内になし。
- 結論: 両テーブルは **CONFIG_DB → hostcfgd (keyspace 通知) → ファイル書き換え / サービス再起動** の一方向で完結し、APPL_DB / STATE_DB / ASIC_DB を経由しない。

## 8. 参考行番号 (sonic-host-services/scripts/hostcfgd)

- 2454-2466: `make_callback`
- 2478, 2481: `subscribe('SSH_SERVER', ...)` / `subscribe('SERIAL_CONSOLE', ...)`
- 2528: `self.config_db.listen(init_data_handler=self.load)`
- 2297-2300: `ssh_handler`
- 2438-2440: `serial_console_config_handler`
- 1045-1175: `SshServer` クラス
- 2013-2043: `SerialConsoleCfg` クラス
- 1407-1480: `PamLimitsCfg` クラス
