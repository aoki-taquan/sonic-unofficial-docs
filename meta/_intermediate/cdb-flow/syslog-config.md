# SYSLOG_CONFIG 例外条件調査メモ

ソース: `sonic-host-services/scripts/hostcfgd` (SHA: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 抽出した例外条件

1. **rsyslog-config サービス再起動失敗** — `RSyslogCfg.update_rsyslog_config()` が
   `systemctl reset-failed rsyslog-config rsyslog` または `systemctl restart rsyslog-config` に失敗すると、
   `"RSyslogCfg: Failed to restart rsyslog service"` を LOG_ERR してキャッシュ更新を行わずに return する。
   設定は CONFIG_DB 上は変更されているが rsyslog には反映されない。

2. **変更なしはノーオペレーション** — `SYSLOG_CONFIG` と `SYSLOG_SERVER` の両テーブルを合わせてキャッシュと比較し、
   変更がなければ `systemctl restart` をスキップする。

3. **YANG must 制約違反は DB 層でブロック** — `welf_firewall_name` は `format != 'standard'` の must 制約を持ち、
   `format = standard` のまま `welf_firewall_name` を書き込もうとすると YANG バリデーションレイヤーで拒否される
   （`hostcfgd` レベルでは追加チェックなし）。
