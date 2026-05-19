# ZMQ — Phase F 副次 DB 書込 調査ノート

## 調査対象

- `sonic-swss/lib/orch_zmq_config.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/fpmsyncd/routesync.cpp`
- `sonic-swss-common/common/zmqserver.cpp`
- 調査日: 2026-05-19

## 調査方法

各ソースファイルを `AppTable`, `ProducerStateTable`, `StateTable`, `hset(`, `set(`, `APPL_DB`, `STATE_DB`, `COUNTERS_DB`, `FLEX_COUNTER_DB` でスキャンして副次書込みを確認。

## APPL_DB 書込み

なし。`orch_zmq_config.cpp` は `get_feature_status()` / `create_zmq_server()` / `create_local_zmq_client()` / `load_zmq_tables()` のみを実装し、APPL_DB への直接書込みはない。

ZMQ チャネルが有効な場合、orchagent は ZmqConsumerStateTable 経由でメッセージを受信し APPL_DB テーブルを処理するが、これは ZMQ フィールドの「変化」による副次書込みではなく、ZMQ トランスポート経由で届いた操作の結果である。

## STATE_DB 書込み

なし。`orch_zmq_config.cpp` 全体に STATE_DB 書込みなし。ZMQ サーバ/クライアントの状態（接続・切断）は STATE_DB に記録されない。

## ASIC_DB / FLEX_COUNTER_DB / COUNTERS_DB 書込み

なし。ZMQ はトランスポート層のみを担い SAI を直接呼び出さない。

## 間接的副作用（ファイル書込み）

`orch_zmq_tables.conf.j2` テンプレートが orchagent コンテナ起動前（`orchagent.sh` 実行時）に CONFIG_DB フラグを参照し `/etc/swss/orch_zmq_tables.conf` を生成する:

- `orch_northbond_dash_zmq_enabled != "false"` → DASH テーブル 22 種を conf に追記
- `orch_northbond_route_zmq_enabled == "true"` → `ROUTE_TABLE` / `LABEL_ROUTE_TABLE` を conf に追記

これはファイルシステムへの書込みであり DB 書込みではない。

## Evidence

- `sonic-swss/lib/orch_zmq_config.cpp` — grep: AppTable/ProducerStateTable/StateTable 0 ヒット
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2` — conf ファイル生成テンプレート
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` — コンテナ起動スクリプト
