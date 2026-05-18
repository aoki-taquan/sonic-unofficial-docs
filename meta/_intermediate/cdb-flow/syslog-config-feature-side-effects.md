# syslog-config-feature — Phase F 副次 DB 書込スキャン (side-effects)

対象テーブル: `CONFIG_DB / SYSLOG_CONFIG_FEATURE`
対象スクリプト:

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`

## スキャン結果

### DB 書込スキャン

`containercfgd` (`SyslogHandler`) はイベントループで `ConfigDBConnector.listen()` を呼び、
`SYSLOG_CONFIG_FEATURE` テーブルの変更通知を受け取る。
`update_syslog_config()` (`containercfgd.py:137-161`) を全行精読した結果:

- `config_db` (`ConfigDBConnector`) への `set` / `hset` / `publish` 呼び出し: **0 件**
- APPL_DB / STATE_DB / COUNTERS_DB への接続: **なし**
- `SonicV2Connector` 直接操作: **なし**
- `NotificationProducer` / `ProducerStateTable`: **なし**

CONFIG_DB は購読のみ (read)。他 DB への副次書込は存在しない。

### ファイルシステム書込

`update_syslog_config()` が行うファイルシステム操作:

```python
# containercfgd.py:152-159 (抜粋)
if os.path.exists(self.TMP_SYSLOG_CONF_PATH):
    os.remove(self.TMP_SYSLOG_CONF_PATH)
with open(self.TMP_SYSLOG_CONF_PATH, 'w+') as f:
    output = run_command(['sonic-cfggen', '-d', '-t', TEMPLATE_PATH, '-a', json_args])
    f.write(output)
run_command(['cp', self.TMP_SYSLOG_CONF_PATH, self.SYSLOG_CONF_PATH])
run_command(['supervisorctl', 'restart', 'rsyslogd'])
```

| 操作 | 対象 | 条件 |
|------|------|------|
| 書込 (新規/上書き) | `/tmp/rsyslog.conf` | 常時 (update_syslog_config 呼び出し時) |
| コピー | `/tmp/rsyslog.conf` → `/etc/rsyslog.conf` | 常時 (上記に続いて) |
| プロセス再起動 | `supervisorctl restart rsyslogd` | 常時 (上記に続いて) |
| 削除 | `/tmp/rsyslog.conf` | 次回 update_syslog_config 呼出の冒頭 |

### systemd / supervisor 経路

`containercfgd` は各コンテナ内の supervisor 管理プロセスとして起動する。
CONFIG_DB の `SYSLOG_CONFIG_FEATURE|<service>` 変更検知 → `update_syslog_config()` →
`supervisorctl restart rsyslogd` で同コンテナ内の rsyslogd を再起動する。

コンテナ外 (host, 他コンテナ) への副次影響はない。

## 副次書込まとめ

| 副次 DB | 操作 | キーパターン | フィールド | evidence |
|---------|------|------------|-----------|---------|
| CONFIG_DB | なし | — | — | 読取専用 |
| APPL_DB | なし | — | — | ヒット 0 件 |
| STATE_DB | なし | — | — | ヒット 0 件 |
| FS `/tmp/rsyslog.conf` | write / delete | (固定パス) | rsyslog conf テキスト | `containercfgd.py:152-158` |
| FS `/etc/rsyslog.conf` | write (cp) | (固定パス) | rsyslog conf テキスト | `containercfgd.py:158` |
| supervisor `rsyslogd` | restart | — | — | `containercfgd.py:159` |
