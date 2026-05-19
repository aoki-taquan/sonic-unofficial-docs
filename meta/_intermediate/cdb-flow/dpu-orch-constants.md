# dpu-orch — Phase E ハードコード定数調査

対象: `DpuOrchDaemon` / `orchagent.sh` / `orch_zmq_config` に存在する CONFIG_DB / YANG 管理外の固定値

## orchagent.sh DPU 固有引数

```bash
# orchagent.sh:27-39
elif [[ x"$LOCALHOST_SWITCHTYPE" == x"dpu" ]]; then
    # To handle high volume of objects in DPU
    ORCHAGENT_ARGS+="-b 65536 "
...
if [ "$LOCALHOST_SWITCHTYPE" == "dpu" ]; then
    ORCHAGENT_ARGS+="-z zmq_sync -k 65536 "
```

- `-b 65536`: pop batch size。通常 NPU は 1024、chassis-packet は 128
- `-z zmq_sync`: ZMQ 同期モード強制。`synchronous_mode` フィールドに依存しない
- `-k 65536`: ZMQ バルク送信上限。デフォルト (`DEFAULT_MAX_BULK_SIZE`) は 1000

## orch_zmq_config 固定値

```cpp
// orch_zmq_config.h:16
#define ZMQ_LOCAL_ADDRESS "tcp://localhost"

// orch_zmq_config.h:21
#define ORCH_NORTHBOND_DASH_ZMQ_ENABLED "orch_northbond_dash_zmq_enabled"

// orch_zmq_config.h:26
#define ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED "orch_northbond_route_zmq_enabled"

// orch_zmq_config.cpp:10
#define ZMQ_TABLE_CONFIGFILE "/etc/swss/orch_zmq_tables.conf"
```

## ZMQ ポート番号

```cpp
// sonic-swss-common/common/zmqserver.h:16
static const int ORCH_ZMQ_PORT = 8100;
```

`get_zmq_port()` (orch_zmq_config.cpp:35-53):
- `NAMESPACE_ID` 環境変数が空: `8100`
- `NAMESPACE_ID` が `n` (0-based): `8100 + n + 1`

## orchdaemon.h — P4Orch エンドポイント

```cpp
// orchdaemon.h:121
const std::string m_p4OrchZmqServerEp = "ipc:///zmq_swss/p4orch_zmq_swss_ep";
```

DPU モードでは P4Orch を使用しないため、`DpuOrchDaemon::init()` では使われない。

## DEFAULT_MAX_BULK_SIZE

```cpp
// orchdaemon.cpp:81
#define DEFAULT_MAX_BULK_SIZE 1000
```

`-k 65536` が DPU モードで上書きするデフォルト値。通常 NPU では 1000 が適用される。

## まとめ

上書き不可の固定値:
- pop batch size: 65536 (orchagent.sh:29)
- ZMQ mode: zmq_sync (orchagent.sh:39)
- ZMQ bulk limit: 65536 (orchagent.sh:39)
- ZMQ base port: 8100 (zmqserver.h:16)
- ZMQ local address: tcp://localhost (orch_zmq_config.h:16)
- ZMQ config file path: /etc/swss/orch_zmq_tables.conf (orch_zmq_config.cpp:10)
