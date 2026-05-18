# SYSLOG_CONFIG — Phase F 副次 DB 書込スキャンノート

対象テーブル: `SYSLOG_CONFIG`
Consumer: `hostcfgd` / `RSyslogCfg` (`sonic-host-services/scripts/hostcfgd`)
スキャン範囲: `RSyslogCfg` クラス全行 (L1695-1743)、`rsyslog_handler()` (L2410-2415)、`rsyslog_config_handler()` / `rsyslog_server_handler()` (L2417-2423) を `set(`/`hset(`/`Producer`/`Notification`/`APPL_DB`/`STATE_DB`/`COUNTERS_DB` で grep

---

## 結論: 副次 DB 書込なし

`RSyslogCfg.update_rsyslog_config()` (hostcfgd:1715-1743) が行う外部操作は以下の 2 つのみ:

1. `systemctl reset-failed rsyslog-config rsyslog` (hostcfgd:1732)
2. `systemctl restart rsyslog-config` (hostcfgd:1734)

APPL_DB / STATE_DB / COUNTERS_DB / ASIC_DB への書き込み呼び出しは一切存在しない。

## DB 別スキャン結果

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `RSyslogCfg` クラス内に `ProducerStateTable` / `Table.set()` / `hset` の呼び出しなし (L1695-1743) |
| STATE_DB | なし | `hostcfgd` の `STATE_DB` 参照は `FipsCfg` (L1759-1821) と起動時 `RestartWaiter` (L2160-2162) のみ。`RSyslogCfg` は `state_db_conn` を保持しない |
| COUNTERS_DB | なし | `hostcfgd` 全体に COUNTERS_DB 参照なし。syslog は認証/ロギング経路のため統計テーブルも存在しない |
| ASIC_DB / FLEX_COUNTER_DB | なし | SAI 非経由。rsyslog はコントロールプレーンのみ |
| LOGLEVEL_DB | なし | `hostcfgd` が LOGLEVEL_DB を書くのは起動時の自身のログレベル登録のみ |

## 副作用の範囲（DB 外）

副作用はすべて Linux ホスト OS レベルに閉じる:

- `rsyslog-config.service` が Jinja2 テンプレートを展開して `/etc/rsyslog.conf` を再生成
- `rsyslogd` が再起動（ログ収集への一時的な空白が発生する可能性）
- 各 docker の rsyslog は `RELP` / `imudp` でホスト rsyslog に転送済みのため、ホスト rsyslog 再起動中のログが欠落する可能性がある
