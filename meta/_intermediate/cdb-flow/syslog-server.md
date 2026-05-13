# SYSLOG_SERVER 例外条件調査メモ

ソース: `sonic-host-services/scripts/hostcfgd` (SHA: c5bbbe8b07b96f078fa4b761316627404b01bd04)

## 抽出した例外条件

1. **SYSLOG_CONFIG と合算して変更検知** — `rsyslog_server_handler()` は変更があると `rsyslog_handler()` を呼び出し、
   `SYSLOG_CONFIG` テーブルと `SYSLOG_SERVER` テーブルの両方を再取得してキャッシュと比較する。
   SYSLOG_SERVER のエントリが追加/削除/変更されると必ず `rsyslog-config` サービスが再起動される。

2. **サーバー削除時の挙動** — SYSLOG_SERVER のエントリを DEL すると、次回 `rsyslog_handler()` 実行時に
   `get_table(CFG_SYSLOG_SERVER_TABLE_NAME)` で取得した残エントリのみでテンプレートが再生成される。
   エントリが 0 件になると rsyslog のリモート転送設定が空になる（ローカルログは継続）。

3. **rsyslog 再起動失敗** — `systemctl restart rsyslog-config` が失敗すると
   `"RSyslogCfg: Failed to restart rsyslog service"` を LOG_ERR し、キャッシュを更新せずに return する。
   次回テーブル変更時に再試行される。

4. **IP バリデーションは YANG 層** — key（サーバー IP アドレス）の形式チェックは
   `sonic-syslog.yang` の `inet:ip-address` または `inet:host` 型制約で行われる。
   `hostcfgd` 層での IP アドレス構文チェックは行われない。
