# ZMQ ハードコード定数 (Phase E) — 調査メモ

slug: zmq
phase: constants (Phase E)
date: 2026-05-19

## 調査対象ファイル

- `sonic-swss-common/common/zmqserver.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-swss/lib/orch_zmq_config.h` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/lib/orch_zmq_config.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/zmqserver.cpp` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-swss-common/common/zmqclient.cpp` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## 発見された定数

### zmqserver.h (define / static const)

```
#define MQ_RESPONSE_MAX_COUNT (16*1024*1024)  // 16 MiB — max message size
#define MQ_SIZE 100                            // queue initial size
#define MQ_MAX_RETRY 10                        // max send retries
#define MQ_POLL_TIMEOUT (1000)                 // poll timeout ms
#define MQ_WATERMARK 10000                     // HWM for ZMQ sockets
static const int ORCH_ZMQ_PORT = 8100;        // base ZMQ port
static constexpr int DEFAULT_POP_BATCH_SIZE = 128;  // pops() batch size
```

### orch_zmq_config.h (define)

```
#define ZMQ_LOCAL_ADDRESS  "tcp://localhost"
#define ORCH_NORTHBOND_DASH_ZMQ_ENABLED  "orch_northbond_dash_zmq_enabled"
#define ORCH_NORTHBOND_ROUTE_ZMQ_ENABLED "orch_northbond_route_zmq_enabled"
```

### orch_zmq_config.cpp (const char*)

```
ZMQ_TABLE_CONFIGFILE = "/etc/swss/orch_zmq_tables.conf"
```

### zmqclient.cpp (inline literals)

```
retry_delay = 10  // initial backoff ms (line 182)
retry_delay *= 2  // exponential backoff (line 199)
```

### TCP Keepalive (zmqserver.cpp + zmqclient.cpp — both use same values)

```
ZMQ_TCP_KEEPALIVE      = 1
ZMQ_TCP_KEEPALIVE_IDLE = 5   seconds
ZMQ_TCP_KEEPALIVE_INTVL= 1   second
ZMQ_TCP_KEEPALIVE_CNT  = 5   probes
```
