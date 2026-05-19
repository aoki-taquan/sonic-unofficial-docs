# SWITCH_TRIMMING 暗黙参照テーブル調査 (Phase C)

調査日: 2026-05-19
ソース: `sonic-swss/orchagent/switchorch.cpp`, `orchagent/switch/trimming/capabilities.cpp`

## 概要

`SwitchOrch::doCfgSwitchTrimmingTableTask()` は他の Orch への依存が極めて少ない。
CONFIG_DB の SWITCH_TRIMMING エントリを SAI へ直接マッピングするシンプルなフロー。
ただし capability クエリ結果を STATE_DB に書き出す副次書き込みが存在する。

## 参照テーブル

### 1. STATE_DB: SWITCH_CAPABILITY|switch (書き込み)

`SwitchTrimmingCapabilities::writeCapabilitiesToDb()` (capabilities.cpp L724) が
SAI capability クエリ結果を STATE_DB に書き込む。

- テーブル名: `STATE_SWITCH_CAPABILITY_TABLE_NAME = "SWITCH_CAPABILITY"` (sonic-swss-common/common/schema.h:417)
- キー: `CAPABILITY_KEY = "switch"` (capabilities.cpp:39)
- 書き込みタイミング: `SwitchOrch` コンストラクタ内の `queryCapabilities()` → `writeCapabilitiesToDb()` (capabilities.cpp L145)

書き込みフィールド:

| フィールド名 | 定数 | 値の例 |
|---|---|---|
| `SWITCH_TRIMMING_CAPABLE` | `CAPABILITY_SWITCH_TRIMMING_CAPABLE_FIELD` | `"true"` / `"false"` |
| `SWITCH\|PACKET_TRIMMING_DSCP_RESOLUTION_MODE` | `CAPABILITY_SWITCH_DSCP_RESOLUTION_MODE_FIELD` | `"DSCP_VALUE,FROM_TC"` / `"N/A"` |
| `SWITCH\|PACKET_TRIMMING_QUEUE_RESOLUTION_MODE` | `CAPABILITY_SWITCH_QUEUE_RESOLUTION_MODE_FIELD` | `"STATIC,DYNAMIC"` / `"N/A"` |
| `SWITCH\|NUMBER_OF_TRAFFIC_CLASSES` | `CAPABILITY_SWITCH_NUMBER_OF_TRAFFIC_CLASSES_FIELD` | 数値 / `"N/A"` |
| `SWITCH\|NUMBER_OF_UNICAST_QUEUES` | `CAPABILITY_SWITCH_NUMBER_OF_UNICAST_QUEUES_FIELD` | 数値 / `"N/A"` |

(定数定義: capabilities.cpp:32–37)

### 2. SAI sai_switch_api (必須)

`setSwitchTrimming()` から呼ばれる各 SAI set 関数が `sai_switch_api->set_switch_attribute(gSwitchId, ...)` を使用する (switchorch.cpp L1000–1065)。失敗時は `SWSS_LOG_ERROR` + `return false`。他 Orch への依存はなく SAI のみ。

### 3. 他 Orch 依存なし

`doCfgSwitchTrimmingTableTask()` は `gPortsOrch`, `gNeighOrch`, `gRouteOrch` 等の他の global Orch を参照しない。orchdaemon.cpp L200–213 で `SwitchOrch` が `conf_switch_trim` を直接受け取る構造。
