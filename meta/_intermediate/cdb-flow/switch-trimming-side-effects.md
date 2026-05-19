# SWITCH_TRIMMING 副次 DB 書込 (Phase F)

対象: `sonic-swss/orchagent/switchorch.cpp`, `sonic-swss/orchagent/switch/trimming/capabilities.cpp`
調査日: 2026-05-19

## CONFIG_DB SWITCH_TRIMMING SET 操作時の副次書込

`doCfgSwitchTrimmingTableTask()` → `setSwitchTrimming()` の処理経路は:

1. `setSwitchTrimmingSizeSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_SIZE)`
2. `setSwitchTrimmingDscpModeSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_RESOLUTION_MODE)`
3. `setSwitchTrimmingDscpSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_DSCP_VALUE)`
4. `setSwitchTrimmingTcSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_TC_VALUE)`
5. `setSwitchTrimmingQueueModeSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_RESOLUTION_MODE)`
6. `setSwitchTrimmingQueueIndexSai()` → `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_PACKET_TRIM_QUEUE_INDEX)`

いずれも SAI API 呼び出しのみ。Redis への副次書込は発生しない。

`trimHlpr.setConfig(cfg)` は orchagent プロセス内メモリ (`SwitchTrimmingHelper::cfg`) への書込のみで、DB 操作なし。

## 起動時 capability 書込（副次 DB 書込あり）

`SwitchTrimmingCapabilities` コンストラクタは `writeCapabilitiesToDb()` を呼び、orchagent 起動時に一度だけ STATE_DB へ書き込む。CONFIG_DB SET 操作のたびには実行されない。

- **書込先**: `STATE_DB:SWITCH_CAPABILITY|switch`
- **書込者**: `SwitchTrimmingCapabilities::writeCapabilitiesToDb()` (`capabilities.cpp:724-745`)
- **書込フィールド**:

| フィールド | 値例 | 意味 |
|---|---|---|
| `SWITCH_TRIMMING_CAPABLE` | `"true"` / `"false"` | ハードウェアがパケットトリミングをサポートするか |
| `SWITCH\|PACKET_TRIMMING_DSCP_RESOLUTION_MODE` | `"DSCP_VALUE,FROM_TC"` | 対応 DSCP 解決モード一覧 |
| `SWITCH\|PACKET_TRIMMING_QUEUE_RESOLUTION_MODE` | `"STATIC,DYNAMIC"` | 対応キュー解決モード一覧 |
| `SWITCH\|NUMBER_OF_TRAFFIC_CLASSES` | `"8"` | トラフィッククラス数 |
| `SWITCH\|NUMBER_OF_UNICAST_QUEUES` | `"8"` | ユニキャストキュー数 |

## まとめ

| DB | CONFIG_DB SET 時副次書込 | 備考 |
|---|---|---|
| APPL_DB | **なし** | `ProducerStateTable` を使用しない |
| STATE_DB | **なし** (起動時のみ有り) | `writeCapabilitiesToDb()` は起動時一回のみ |
| COUNTERS_DB | **なし** | — |
| FLEX_COUNTER_DB | **なし** | — |
| ASIC_DB (間接) | **あり** (syncd 経由) | SAI API 呼び出し → syncd が非同期に ASIC_DB へ反映 |
