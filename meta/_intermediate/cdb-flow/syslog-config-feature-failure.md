# SYSLOG_CONFIG_FEATURE — failure モード調査 (Phase D)

調査日: 2026-05-17
対象コード: `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`

## 障害経路の洗い出し

### 1. `handle_config` 内の汎用 try/except

`SyslogHandler.handle_config()` は `update_syslog_config()` を try/except で囲んでいる (L120-125)。
例外が発生した場合、`logger.log_error('Failed to config syslog for container {} with data {} - {}')` を出力して **silent return** する。
CONFIG_DB への書き込みは既に完了済みのため、DB と実際の rsyslog 設定が不一致となる。

### 2. `sonic-cfggen` コマンド失敗

`run_command(['sonic-cfggen', '-d', '-t', '...rsyslog-container.conf.j2', '-a', json_args])` が `subprocess.CalledProcessError` を raise した場合、`handle_config` の外側 try/except に到達して ERR ログが記録される。
- 一時ファイル `/tmp/rsyslog.conf` は作成されるが内容が空または不完全のまま残る可能性がある。
- `current_interval` / `current_burst` は更新されないため、次回同じ値が書き込まれても再試行されない（冪等性なし）。

### 3. `supervisorctl restart rsyslogd` 失敗

`run_command(['supervisorctl', 'restart', 'rsyslogd'])` が失敗した場合も同様に汎用 except が吸収する。
rsyslogd は旧設定で動作し続けるが、`current_interval` / `current_burst` は更新されない。
次回変更時に再び `update_syslog_config()` が呼ばれ再試行される（フィールド値が変わった場合のみ）。

### 4. `/etc/rsyslog.conf` 読み取り失敗（起動時）

`parse_syslog_conf()` は `__init__` で呼ばれ、ファイルが存在しない場合は `FileNotFoundError` が try/except の外側で raise される。
containercfgd 起動時にクラッシュし、CONFIG_DB 変更を受け付けられなくなる。

### 5. `handle_init_data` の例外伝播

`handle_init_data()` には独立した try/except がなく、例外は `ContainerConfigDaemon.init_data_handler()` に伝播する。
`init_data_handler()` の呼び出し元（swsscommon listen ループ）がどう扱うかはライブラリ実装に依存。

## サマリ

| 障害 | 検出方法 | 回復方法 |
|------|---------|---------|
| `sonic-cfggen` 失敗 | ERR ログ | 設定値を変更して再書き込み |
| `supervisorctl` 失敗 | ERR ログ | 設定値を変更して再書き込み |
| `/etc/rsyslog.conf` 不在 | containercfgd クラッシュ | コンテナ再起動 |
| DB と rsyslog 設定の乖離 | `docker exec <svc> cat /etc/rsyslog.conf` で確認 | 設定値を変更して再書き込み |
