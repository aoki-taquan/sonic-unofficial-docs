# SWITCH_TRIMMING ハードコード定数調査 (Phase E)

調査対象:
- `sonic-swss/orchagent/switch/trimming/schema.h` (全行)
- `sonic-swss/orchagent/switch/trimming/helper.cpp` L25-26
- `sonic-swss/orchagent/switch/trimming/capabilities.cpp` L32-41
調査日: 2026-05-19

## フィールドキー定数 (schema.h)

`schema.h` が CONFIG_DB フィールド名文字列と `dscp_value` / `queue_index` の特殊値文字列を集中管理する。

### テーブルフィールド名

| マクロ名 | 値 | 用途 |
|---|---|---|
| `SWITCH_TRIMMING_SIZE` | `"size"` | パケットトリミング後サイズ [bytes] |
| `SWITCH_TRIMMING_DSCP_VALUE` | `"dscp_value"` | DSCP 値または `"from-tc"` |
| `SWITCH_TRIMMING_TC_VALUE` | `"tc_value"` | Traffic Class 値 |
| `SWITCH_TRIMMING_QUEUE_INDEX` | `"queue_index"` | 送信キューインデックスまたは `"dynamic"` |

### `dscp_value` 特殊値定数

| マクロ名 | 値 | SAI 意味 |
|---|---|---|
| `SWITCH_TRIMMING_DSCP_VALUE_FROM_TC` | `"from-tc"` | TC から DSCP を逆引きする (`SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_FROM_TC`) |

### DSCP 解決モード文字列 (STATE_DB capabilities 用)

| マクロ名 | 値 | SAI enum |
|---|---|---|
| `SWITCH_TRIMMING_DSCP_MODE_DSCP_VALUE` | `"DSCP_VALUE"` | `SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_DSCP_VALUE` |
| `SWITCH_TRIMMING_DSCP_MODE_FROM_TC` | `"FROM_TC"` | `SAI_PACKET_TRIM_DSCP_RESOLUTION_MODE_FROM_TC` |

### キュー解決モード文字列 (STATE_DB capabilities 用)

| マクロ名 | 値 | SAI enum |
|---|---|---|
| `SWITCH_TRIMMING_QUEUE_INDEX_DYNAMIC` | `"dynamic"` | `SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_DYNAMIC` |
| `SWITCH_TRIMMING_QUEUE_MODE_STATIC` | `"STATIC"` | `SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_STATIC` |
| `SWITCH_TRIMMING_QUEUE_MODE_DYNAMIC` | `"DYNAMIC"` | `SAI_PACKET_TRIM_QUEUE_RESOLUTION_MODE_DYNAMIC` |

## 数値範囲定数 (helper.cpp)

| 定数名 | 値 | 用途 |
|---|---|---|
| `minDscp` | `0` | `dscp_value` の最小値 (helper.cpp L25) |
| `maxDscp` | `63` | `dscp_value` の最大値 (helper.cpp L26) |

範囲外の `dscp_value` は `helper.cpp` 内でバリデーション失敗 → `LOG_ERROR` + エントリ破棄。

## STATE_DB キー・フィールド定数 (capabilities.cpp)

`SwitchTrimmingCapabilities::writeCapabilitiesToDb()` が `STATE_DB:SWITCH_CAPABILITY|switch` に書き込む際に使用する定数。

| マクロ名 | 値 | 用途 |
|---|---|---|
| `CAPABILITY_SWITCH_TRIMMING_CAPABLE_FIELD` | `"SWITCH_TRIMMING_CAPABLE"` | ASIC が packet trimming をサポートするか (`"true"` / `"false"`) |
| `CAPABILITY_SWITCH_DSCP_RESOLUTION_MODE_FIELD` | `"SWITCH\|PACKET_TRIMMING_DSCP_RESOLUTION_MODE"` | サポートされる DSCP resolution mode 一覧 |
| `CAPABILITY_SWITCH_QUEUE_RESOLUTION_MODE_FIELD` | `"SWITCH\|PACKET_TRIMMING_QUEUE_RESOLUTION_MODE"` | サポートされる queue resolution mode 一覧 |
| `CAPABILITY_SWITCH_NUMBER_OF_TRAFFIC_CLASSES_FIELD` | `"SWITCH\|NUMBER_OF_TRAFFIC_CLASSES"` | ASIC がサポートするトラフィッククラス数 |
| `CAPABILITY_SWITCH_NUMBER_OF_UNICAST_QUEUES_FIELD` | `"SWITCH\|NUMBER_OF_UNICAST_QUEUES"` | ASIC がサポートするユニキャストキュー数 |
| `CAPABILITY_KEY` | `"switch"` | STATE_DB の行キー (固定) |
| `SWITCH_STATE_DB_NAME` | `"STATE_DB"` | 接続先 DB 名 |
| `SWITCH_STATE_DB_TIMEOUT` | `0` | DB 接続タイムアウト (ブロッキングなし) |
