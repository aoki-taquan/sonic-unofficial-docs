# POLICER フィールド値分析

## enum フィールド

### `METER_TYPE`
実装: policerorch.cpp の meter_type_map
- `PACKETS` → SAI_METER_TYPE_PACKETS
- `BYTES` → SAI_METER_TYPE_BYTES
- storm-control 経由の場合は `BYTES` に自動固定

### `MODE`
実装: policerorch.cpp の policer_mode_map
- `SR_TCM` → SAI_POLICER_MODE_SR_TCM (Single Rate TCM: CIR/CBS/PBS)
- `TR_TCM` → SAI_POLICER_MODE_TR_TCM (Two Rate TCM: CIR/CBS/PIR/PBS)
- `STORM_CONTROL` → SAI_POLICER_MODE_STORM_CONTROL (CIR/CBS のみ)
- storm-control 経由の場合は `STORM_CONTROL` に自動固定

### `COLOR_SOURCE`
実装: policerorch.cpp の color_source_map
- `AWARE` → SAI_POLICER_COLOR_SOURCE_AWARE
- `BLIND` → SAI_POLICER_COLOR_SOURCE_BLIND

### `*_PACKET_ACTION`
実装: policerorch.cpp の packet_action_map
- `FORWARD` → SAI_PACKET_ACTION_FORWARD
- `DROP` → SAI_PACKET_ACTION_DROP
- storm-control 経由の場合 RED_PACKET_ACTION を `DROP` に自動固定

## create-only vs SET 可能フィールド
- create-only: METER_TYPE / MODE / COLOR_SOURCE / *_PACKET_ACTION
- SET 可能: CIR / CBS / PIR / PBS

## モード別有効パラメータ
- SR_TCM: CIR, CBS, PBS
- TR_TCM: CIR, CBS, PIR, PBS
- STORM_CONTROL: CIR, CBS のみ (PIR は無視または SAI エラー)

## ソース
- orchagent/policerorch.cpp (sonic-swss sha 43055961)
- common/schema.h (sonic-swss-common sha 158de8d3)
