# zmq side-effects research (Phase F)

## 調査対象

- `sonic-swss/lib/orch_zmq_config.cpp`
- `sonic-swss/fpmsyncd/routesync.cpp`
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2`
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`
- `sonic-buildimage/dockers/docker-sonic-gnmi/gnmi-native.sh`

## 調査結果

### DB 副次書込み
なし。STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB への直接書込みは検出されなかった。

### ファイルシステム副次作用
- `/etc/swss/orch_zmq_tables.conf`: `orch_zmq_tables.conf.j2` が Jinja2 展開でコンテナ起動時に生成。
  `orch_northbond_dash_zmq_enabled != "false"` → 24 DASH テーブル追記。
  `orch_northbond_route_zmq_enabled == "true"` → ROUTE_TABLE / LABEL_ROUTE_TABLE 追記。

### プロセス内部状態変化
- fpmsyncd `RouteSync` のトランスポート選択: `orch_northbond_route_zmq_enabled=true` → `ZmqProducerStateTable`、それ以外 → `ProducerStateTable`。
- gnmi: `subtype==SmartSwitch` のとき `-zmq_port=8100` 付与（`gnmi-native.sh:90-92`）。

### APPL_DB への間接影響
ZMQ 有効時、DASH テーブルおよび ROUTE_TABLE への書込み経路が ZMQ に変わるが、エントリの内容・数は変わらない。
