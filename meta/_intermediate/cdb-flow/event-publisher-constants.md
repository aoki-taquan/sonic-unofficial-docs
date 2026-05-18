# event-publisher Phase E — ハードコード定数調査メモ

## 調査対象

- `sonic-buildimage/src/sonic-eventd/src/eventd.cpp`
- `sonic-buildimage/src/sonic-eventd/src/eventd.h`
- `sonic-swss-common/common/events_common.h`

## 発見した定数

### eventd.cpp

| 定数 | 値 | 行 |
|------|----|-----|
| `MB(N)` | `(N) * 1024 * 1024` | L30 |
| `EVT_SIZE_AVG` | `150` | L31 |
| `MAX_CACHE_SIZE` | `MB(100)/150 = 699050` | L33 |
| `READ_SET_SIZE` | `100` | L36 |
| `CAPTURE_SOCK_TIMEOUT` | `800` ms | L41 |
| `HEARTBEAT_INTERVAL_SECS` | `2` 秒 | L43 |
| `EVENTD_PUBLISHER_SOURCE` | `"sonic-events-eventd"` | L46 |
| `EVENTD_HEARTBEAT_TAG` | `"heartbeat"` | L47 |

### eventd.h

| 定数 | 値 | 行 |
|------|----|-----|
| `STATS_HEARTBEAT_MIN` | `300` ms | L24 |
| `CAPTURE_SERVICE_POLLING_DURATION` | `10` ms | L25 |
| `CAPTURE_SERVICE_POLLING_INCREMENT` | `10` ms | L26 |
| `CAPTURE_SERVICE_POLLING_MAX_DURATION` | `100` ms | L27 |
| `CAPTURE_SERVICE_POLLING_RETRIES` | `100` 回 | L28 |

### events_common.h

| 定数 | 値 | 行 |
|------|----|-----|
| `MAX_PUBLISHERS_COUNT` | `1000` | L45 |
| `LINGER_TIMEOUT` | `100` ms | L54 |
| `INIT_CFG_PATH` | `"/etc/sonic/init_cfg.json"` | L129 |
| `CFG_EVENTS_KEY` | `"events"` | L130 |
| `CACHE_DRAIN_IN_MILLISECS` | `1000` ms | L470 |

## ハートビート実効値計算

`set_heartbeat_interval(2)` 呼び出し時:
- `interval_count = ceil(2000 / 300) = ceil(6.67) = 7`
- 実効値 = `7 * 300 = 2100 ms`

コード証跡: `eventd.cpp:145` → `(((val * 1000) + STATS_HEARTBEAT_MIN - 1) / STATS_HEARTBEAT_MIN)`
