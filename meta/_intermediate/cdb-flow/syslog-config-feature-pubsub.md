# SYSLOG_CONFIG_FEATURE — Phase G 通信メカニズム調査ノート

## 調査対象

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-syslog.yang`
- `sonic-utilities/config/syslog.py`

## 購読方式の特定

### containercfgd (SyslogHandler) — 常駐 daemon / subscribe+listen

`ContainerConfigDaemon.run()` の実装 (containercfgd.py L44-52):

```python
config_db = ConfigDBConnector()
config_db.connect(wait_for_init=True, retry_on=True)
for table_name, handler in self.handlers.items():
    config_db.subscribe(table_name, handler.handle_config)
config_db.listen(init_data_handler=self.init_data_handler)
```

- `ConfigDBConnector.subscribe()` は Redis keyspace 通知 (`__keyevent@<dbId>__:hset` / `__keyevent@<dbId>__:hdel`) を利用して変更をリアルタイム受信する。
- `config_db.listen()` は swsscommon の `ConfigDBConnector.listen()` — 内部で Redis `psubscribe` を実行し、イベントループで `handle_config` コールバックを呼ぶ。
- `wait_for_init=True` により CONFIG_DB の初期化完了 (`__keyevent@<dbId>__:set` + init 完了通知) を待つ。
- `init_data_handler` で起動時スナップショット (`HGETALL` 等) を受け取り、既存エントリを即時反映。

### hostcfgd — 購読しない

`sonic-host-services/` および `sonic-buildimage/files/hostcfgd.py` を `SYSLOG_CONFIG_FEATURE` で grep:
- ヒットなし。hostcfgd は `SYSLOG_CONFIG|GLOBAL` のみ購読し、per-feature テーブルには触れない。

### 他の購読者 — なし

`sonic-utilities/` および `sonic-swss/` で `SYSLOG_CONFIG_FEATURE` を subscribe/listen するコードは存在しない。

## Redis primitive の特定

| フェーズ | API | Redis コマンド | タイミング |
|---------|-----|---------------|----------|
| 起動時初期化 | `ConfigDBConnector.listen(init_data_handler=...)` | `HGETALL SYSLOG_CONFIG_FEATURE|*` (全エントリスナップショット) | daemon 起動直後 |
| 変更受信 | `ConfigDBConnector.subscribe()` + `listen()` | `psubscribe __keyevent@<dbId>__:*` → HGETALL | DB 書き込みイベント検知時 |
| 設定適用 | `SyslogHandler.update_syslog_config(data)` | — (sonic-cfggen 呼び出しのみ) | 変更 or 初期化時 |

## トリガ経路 (シーケンス)

```
CLI: config syslog rate-limit-container <service> --interval N --burst M
  ↓  sonic-utilities/config/syslog.py
  ↓  cfgdb.mod_entry("SYSLOG_CONFIG_FEATURE", service_name, {rate_limit_interval: N, rate_limit_burst: M})
     → Redis HSET SYSLOG_CONFIG_FEATURE|<service> rate_limit_interval N rate_limit_burst M

CONFIG_DB (Redis) ── keyspace notification ──▶ containercfgd (SyslogHandler.handle_config)
  ├─ key == service_name? → True (自コンテナのエントリのみ処理)
  ├─ update_syslog_config(data)
  │    ├─ new_interval = data.get('rate_limit_interval', '0')
  │    ├─ new_burst    = data.get('rate_limit_burst', '0')
  │    ├─ 変更なし? → LOG_NOTICE + return (no-op)
  │    ├─ sonic-cfggen -d -t /usr/share/sonic/templates/rsyslog-container.conf.j2 → /tmp/rsyslog.conf
  │    ├─ cp /tmp/rsyslog.conf /etc/rsyslog.conf
  │    └─ supervisorctl restart rsyslogd
  └─ current_interval, current_burst 更新
```

## 特記事項

- **per-container 分離**: 各コンテナが独自に `containercfgd` インスタンスを実行し、`service_name` で自分向けエントリのみ処理する。同一 Redis への接続だが実質的に分離。
- **APPL_DB / STATE_DB 非使用**: 全経路が CONFIG_DB のみ。pub/sub チャンネルや Notification 機構は不使用。
- **keyspace 通知**: Redis 側では `__keyevent@<dbId>__:hset` 等が発行されるが、`ConfigDBConnector.subscribe()` が内部で `psubscribe` してこれを受信する。

## 証拠箇所

- `containercfgd.py` L44-61 (`run()` / `init_data_handler`)
- `containercfgd.py` L112-135 (`SyslogHandler.handle_config` / `handle_init_data`)
- `containercfgd.py` L137-161 (`update_syslog_config`)
