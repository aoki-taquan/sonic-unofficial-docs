# PORT_QOS_MAP フィールド値分析

## enum フィールド

なし — 全フィールドは string pattern か leafref。

## 特殊フィールド

### `ifname`
- `global`: グローバルデフォルトとして全ポートに適用
- `PORT.name` (leafref): 指定ポートのみに binding
- 存在しない PORT 名: YANG leafref 違反 → reject

### `pfc_enable` / `pfcwd_sw_enable` (string pattern `([0-7](,[0-7])*)?`)
- `3,4`: PFC priority 3, 4 を有効化 (RoCEv2 lossless 定番)
- 空文字: 全無効
- `0,1,2,...,7`: 全有効化

### map 系フィールド (leafref)
各フィールドは対応 QoS map テーブルへの leafref:
- dscp_to_tc_map → DSCP_TO_TC_MAP.name
- tc_to_queue_map → TC_TO_QUEUE_MAP.name
- tc_to_pg_map → TC_TO_PRIORITY_GROUP_MAP.name
- pfc_to_queue_map → MAP_PFC_PRIORITY_TO_QUEUE.name
- pfc_to_pg_map → PFC_PRIORITY_TO_PRIORITY_GROUP_MAP.name
- tc_to_dscp_map → TC_TO_DSCP_MAP.name
- dot1p_to_tc_map → DOT1P_TO_TC_MAP.name
- scheduler → SCHEDULER.name
- 存在しない名前: `Object with name:%s not found.` → SWSS_LOG_ERROR、適用中断

## YANG 制約
- mandatory / must 制約なし。全フィールドが optional。

## ソース
- sonic-port-qos-map.yang (sonic-buildimage sha 9ea932ec)
- orchagent/qosorch.cpp (sonic-swss)
