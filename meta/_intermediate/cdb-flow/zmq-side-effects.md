# ZMQ CONFIG_DB フィールド — 副次 DB 書込 (Phase F) 調査ノート

## 調査対象ファイル

- `sonic-swss/lib/orch_zmq_config.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-buildimage/dockers/docker-orchagent/docker-init.j2` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-swss/orchagent/orchdaemon.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 調査日

2026-05-19

## 主要な発見

### 1. 設定フィールドは起動時一回読み取り（購読なし）

`get_feature_status()` (`orch_zmq_config.cpp:81-104`) は orchagent 起動時の `OrchDaemon` コンストラクタで一度だけ呼ばれる。`DEVICE_METADATA|localhost` を `hget` するが、その後は CONFIG_DB の変更を購読しない。実行中の変更は orchagent 再起動まで無視される。

### 2. `/etc/swss/orch_zmq_tables.conf` はコンテナ起動時に生成

`docker-init.j2:15` が `sonic-cfggen -d -t orch_zmq_tables.conf.j2,/etc/swss/orch_zmq_tables.conf` を実行。この時点の CONFIG_DB 値からファイルを生成する。

`orch_zmq_tables.conf.j2` の条件分岐:
- `orch_northbond_dash_zmq_enabled != "false"` → DASH テーブル 24 種を追記
- `orch_northbond_route_zmq_enabled == "true"` → ROUTE_TABLE / LABEL_ROUTE_TABLE を追記

### 3. APPL_DB / STATE_DB / ASIC_DB への直接書き込みなし

ZMQ 設定フィールドの変化は DB への副次書き込みを一切引き起こさない。

### 4. APPL_DB への間接的な経路変化

ZMQ 有効時、gNMI / fpmsyncd は `ZmqProducerStateTable` を使い orchagent に直接送信する。APPL_DB Redis には書き込まれない。無効時は通常の `ProducerStateTable` → APPL_DB → orchagent (Redis Pub/Sub) 経路を使う。

## 証跡コード参照

- `docker-init.j2:15`: `sonic-cfggen ... -t orch_zmq_tables.conf.j2,/etc/swss/orch_zmq_tables.conf`
- `orch_zmq_config.cpp:18-33`: `load_zmq_tables()` — `/etc/swss/orch_zmq_tables.conf` を読み込み
- `orch_zmq_config.cpp:81-104`: `get_feature_status()` — CONFIG_DB hget のみ（購読なし）
- `orch_zmq_config.cpp:117-145`: `createProducerStateTable()` — ZmqClient 有無で ZmqProducerStateTable と ProducerStateTable を切り替え
- `orch_zmq_tables.conf.j2:1-29`: DASH / ROUTE テーブルのフラグ条件分岐
