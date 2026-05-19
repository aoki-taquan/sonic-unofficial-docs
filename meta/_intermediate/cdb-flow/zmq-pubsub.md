# zmq — 通信メカニズム (pubsub) 調査メモ

## 調査対象

`docs/reference/config-db/zmq.md` Phase G 追加分。
`orch_northbond_dash_zmq_enabled` / `orch_northbond_route_zmq_enabled` / `orchagent_zmq_port` フィールドの
CONFIG_DB からの読み取り方式（subscribe か一回限り hget か）を調査する。

## 調査ファイル

- `sonic-swss/lib/orch_zmq_config.cpp` — `get_feature_status()`, `create_local_zmq_client()`
- `sonic-swss/orchagent/orchdaemon.cpp` — `get_feature_status()` 呼び出し箇所
- `sonic-swss/fpmsyncd/routesync.cpp` — `create_local_zmq_client()` 呼び出し箇所
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` — ZMQ アドレス決定スクリプト

## 結果

### SubscriberStateTable / ConsumerStateTable は使用しない

`get_feature_status()` (`orch_zmq_config.cpp:81-104`) は `DBConnector config_db("CONFIG_DB", 0)` を
一時的に生成して `config_db.hget("DEVICE_METADATA|localhost", feature)` を 1 回のみ呼び出す。
`SubscriberStateTable` / `ConsumerStateTable` / keyspace PSUBSCRIBE は一切使用しない。

呼び出し箇所:
- `orchdaemon.cpp:334` — `create_zmq_server(ORCH_ZMQ_PORT, ...)` 内から
- `orchdaemon.cpp:1329` — `get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true)` 直接呼び出し
- `routesync.cpp:155` — `create_local_zmq_client(ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED, false)` 内から

いずれも orchagent / fpmsyncd の**起動時初期化コード**内に位置し、main ループ以降での再評価は行われない。

### redis Pub/Sub イベントは発生しない

CONFIG_DB `DEVICE_METADATA|localhost` の ZMQ フィールド変更時に:
1. `DEVICE_METADATA_CHANNEL@4` への keyspace PUBLISH は Redis が自動送出するが
2. orchagent / fpmsyncd はこのチャネルを PSUBSCRIBE していない
3. 変更は実行中のプロセスに通知されない

### orchagent コンテナ起動時の j2 テンプレート読み取り

`docker-init.j2` が `sonic-cfggen` で `orch_zmq_tables.conf.j2` を展開する際は、
`sonic-cfggen` が直接 CONFIG_DB を `hgetall` して読み取る（Python swsscommon 経由）。
こちらも subscribe ではなく一回限りのバッチ読み取り。

### DPU の orchagent_zmq_port

`orchagent.sh` が `sonic-db-cli CONFIG_DB hget "DPU|<name>" orchagent_zmq_port` で
起動引数に埋め込む形式。こちらも起動時一回限り。

## 結論

ZMQ 関連 CONFIG_DB フィールドは全て **起動時一回限りの `hget` 同期読み取り**で評価される。
orchagent / fpmsyncd は実行中に CONFIG_DB の変更を subscribe せず、
`SubscriberStateTable` / `ConsumerStateTable` のいずれも使用しない。
フィールド変更を反映するには orchagent コンテナ（または fpmsyncd）の再起動が必要。

## evidence

- `sonic-swss/lib/orch_zmq_config.cpp:81-104` — `get_feature_status()`: 一時 DBConnector + hget。subscribe なし
- `sonic-swss/orchagent/orchdaemon.cpp:334,1329` — 起動時初期化内での呼び出し
- `sonic-swss/fpmsyncd/routesync.cpp:155` — コンストラクタ初期化リスト内での呼び出し
