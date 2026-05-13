# PORT_STORM_CONTROL フィールド値分析

## enum フィールド (key として使用)

### `storm_type` (key の一部)
- `broadcast` → SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID
- `unknown-unicast` → SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID
- `unknown-multicast` → SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID
- その他: `Unknown storm_type %s` → SWSS_LOG_ERROR

## 数値フィールド

### `kbps` (uint64, 0..100000000)
- SAI policer CIR として設定 (METER_TYPE=BYTES, MODE=STORM_CONTROL 固定)
- 0: SAI が無制限として扱うかはプラットフォーム依存
- 上限: HW 実際の上限による更なる制約あり

## interface 制約

### `ifname` (key: PORT.name leafref)
- 物理ポート: 正常
- LAG / VLAN など: `Unsupported / Invalid interface %s` → SWSS_LOG_ERROR
- 存在しないポート: `Failed to apply storm-control %s to port %s. Port not found` → SWSS_LOG_ERROR

## 内部 policer 生成 (自動)
policerorch が storm-control パスで:
- METER_TYPE=BYTES (固定)
- MODE=STORM_CONTROL (固定)
- RED_PACKET_ACTION=DROP (固定)

## ソース
- sonic-storm-control.yang (sonic-buildimage sha 9ea932ec)
- orchagent/policerorch.cpp (sonic-swss sha 43055961)
