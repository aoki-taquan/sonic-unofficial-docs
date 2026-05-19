# zmq cross-refs — Phase C 調査証跡

## 調査対象
- `sonic-swss/lib/orch_zmq_config.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/lib/orch_zmq_config.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/fpmsyncd/routesync.cpp`
- `sonic-buildimage/dockers/docker-orchagent/orch_zmq_tables.conf.j2`
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`

## 主要な参照関係

### DEVICE_METADATA → orch_northbond_dash_zmq_enabled

`get_feature_status("orch_northbond_dash_zmq_enabled", true)` が起動時に
`DEVICE_METADATA|localhost` を `hget` する (orch_zmq_config.cpp:88)。

### DEVICE_METADATA → orch_northbond_route_zmq_enabled

`create_local_zmq_client("orch_northbond_route_zmq_enabled", false)` が起動時に
`DEVICE_METADATA|localhost` を `hget` する (routesync.cpp:155)。

### DPU → orchagent_zmq_port

gnmi-native.sh / orchagent.sh が DPU テーブルから ZMQ ポートを読み取る。
YANG: sonic-smart-switch.yang:176-179。

### subtype / switch_type による分岐

orchagent.sh が DEVICE_METADATA subtype/switch_type を参照して ZMQ アドレスと
起動オプションを決定 (orchagent.sh:38-39, 105-118)。

### 設定ファイル生成

orch_zmq_tables.conf.j2 の Jinja2 テンプレートがフラグを参照して
/etc/swss/orch_zmq_tables.conf を生成。orchagent の load_zmq_tables() が読む。
