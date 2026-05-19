# QUEUE_COUNTER_CAPABILITIES — ハードコード定数調査 (Phase E)

調査対象: `sonic-swss/orchagent/portsorch.cpp` @ master

## テーブル名定数

| 定数名 | 値 | 定義箇所 |
|--------|----|---------|
| `STATE_QUEUE_COUNTER_CAPABILITIES_NAME` | `"QUEUE_COUNTER_CAPABILITIES"` | `sonic-swss-common/common/schema.h:528` |

## キー名文字列（コード埋め込み）

`initCounterCapabilities()` 内に 4 つのキー名がリテラル文字列として直接埋め込まれている。YANG やマクロ定義なし。

| キー文字列 | コード行 |
|-----------|---------|
| `"WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER"` | `portsorch.cpp:1872, 1896` |
| `"WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER"` | `portsorch.cpp:1873, 1901` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER"` | `portsorch.cpp:1874, 1906` |
| `"WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER"` | `portsorch.cpp:1875, 1911` |

## フィールド名・値定数

| フィールド | 値候補 | コード行 |
|-----------|--------|---------|
| `"isSupported"` | `"false"` (初期値) | `portsorch.cpp:1868-1869` — `fieldValuesFalse` |
| `"isSupported"` | `"true"` (SAI 確認後) | `portsorch.cpp:1865-1866` — `fieldValuesTrue` |

## SAI 列挙値（マジック定数）

`sai_query_stats_capability()` の戻り値と比較するための SAI enum 値。コード内でマクロ名（`SAI_QUEUE_STAT_*`）を使用。

| SAI マクロ | 対応キー |
|-----------|---------|
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS` | `WRED_ECN_QUEUE_ECN_MARKED_PKT_COUNTER` |
| `SAI_QUEUE_STAT_WRED_ECN_MARKED_BYTES` | `WRED_ECN_QUEUE_ECN_MARKED_BYTE_COUNTER` |
| `SAI_QUEUE_STAT_WRED_DROPPED_PACKETS` | `WRED_ECN_QUEUE_WRED_DROPPED_PKT_COUNTER` |
| `SAI_QUEUE_STAT_WRED_DROPPED_BYTES` | `WRED_ECN_QUEUE_WRED_DROPPED_BYTE_COUNTER` |

## ログメッセージ定数

| マクロ | メッセージ文字列 | コード行 |
|-------|----------------|---------|
| `SWSS_LOG_NOTICE` | `"Queue stat capability get failed: WRED queue stats can not be enabled, rv:%d"` | `portsorch.cpp:1921` |
| `SWSS_LOG_INFO` | `"WRED queue stats is_capable: [ecn-marked-pkts:%d,ecn-marked-bytes:%d,wred-drop-pkts:%d,wred-drop-bytes:%d]"` | `portsorch.cpp:1916-1917` |

## stat_initializer 初期値

`sai_stat_capability_t stat_initializer` は `stat_enum = 0`, `stat_modes = 0` で初期化される (`portsorch.cpp:1859-1860`)。これは `qstat_cap_list.resize()` 時のデフォルト要素として使用される。
