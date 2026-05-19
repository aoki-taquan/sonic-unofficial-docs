# HEARTBEAT pubsub 調査証跡 (Phase G)

調査日: 2026-05-19

## 調査対象

- `sonic-buildimage/src/sonic-supervisord-utilities/scripts/supervisor-proc-exit-listener`
- `sonic-buildimage/src/sonic-supervisord-utilities-rs/src/proc_exit_listener.rs`
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`

## 結論

HEARTBEAT テーブルを読む全コンシューマは Redis keyspace notification / ConsumerStateTable / SubscriberStateTable を使用しない。

- supervisor-proc-exit-listener (Python): `ConfigDBConnector.get_table("HEARTBEAT")` を起動時 1 回のみ呼ぶ (L124-135)
- supervisor-proc-exit-listener (Rust): `config_db.get_table(HEARTBEAT_TABLE_NAME)` を起動時 1 回のみ呼ぶ (proc_exit_listener.rs:212-233)
- orchagent.sh: `sonic-db-cli CONFIG_DB hget "HEARTBEAT|orchagent" heartbeat_interval` を起動スクリプト実行時 1 回のみ (orchagent.sh:127-130)
- eventd: CONFIG_DB を直接読まない。ZeroMQ RPC 経由でのみ heartbeat interval を受け取る

CONFIG_DB への HSET 書き込みで Redis keyspace notification は発火するが、受信する購読プロセスが存在しないため通知は捨てられる。
変更の反映には daemon 再起動が必要。
