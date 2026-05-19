# extended-monitor Phase E 調査メモ (ハードコード定数)

## 調査ファイル

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-swss-common/common/events_common.h`

## 発見した定数

### eventd.cpp (L24-47)
```
STATS_HEARTBEAT_MIN = 300 (ms)
CAPTURE_SERVICE_POLLING_DURATION = 10 (ms)
CAPTURE_SERVICE_POLLING_INCREMENT = 10 (ms)
CAPTURE_SERVICE_POLLING_MAX_DURATION = 100 (ms)
CAPTURE_SERVICE_POLLING_RETRIES = 100
EVT_SIZE_AVG = 150 (bytes)
MAX_CACHE_SIZE = MB(100) / EVT_SIZE_AVG = 699050
READ_SET_SIZE = 100
CAPTURE_SOCK_TIMEOUT = 800 (ms)
HEARTBEAT_INTERVAL_SECS = 2
EVENTD_PUBLISHER_SOURCE = "sonic-events-eventd"
EVENTD_HEARTBEAT_TAG = "heartbeat"
```

### events_common.h (L45, 54, 470)
```
MAX_PUBLISHERS_COUNT = 1000
LINGER_TIMEOUT = 100 (ms)
CACHE_DRAIN_IN_MILLISECS = 1000 (ms)
```

## 結論

Phase A `<!-- defaults -->` ブロックで既に一部定数 (MAX_CACHE_SIZE, EVT_SIZE_AVG, READ_SET_SIZE, HEARTBEAT_INTERVAL_SECS, STATS_HEARTBEAT_MIN) を記載済みだったが、
Phase E `<!-- constants -->` ブロックで全定数を体系的にカテゴリ分けして整理した。
キャプチャサービス制御定数 (CAPTURE_SERVICE_POLLING_* / CACHE_DRAIN_IN_MILLISECS / CAPTURE_SOCK_TIMEOUT) と ZMQ 定数 (LINGER_TIMEOUT / MAX_PUBLISHERS_COUNT) は Phase A では未記載だった。
