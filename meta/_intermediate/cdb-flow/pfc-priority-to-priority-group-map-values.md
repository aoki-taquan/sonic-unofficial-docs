# PFC_PRIORITY_TO_PRIORITY_GROUP_MAP フィールド値分析

## enum フィールド

なし — pfc_priority / pg は string pattern `[0-7]?` (0..7 の 1 桁数字または空文字)。

## 数値範囲 / pattern フィールド

### `pfc_priority` / `pg`
- `0`..`7` (文字列): SAI QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP への key/value として登録
- 空文字: YANG pattern では許容するが QosOrch での数値変換が失敗してエラー
- 実質有効: `0`..`7` のみ

### `name`
- 1..32 文字、英数字始まり、英数字 / `-` / `_` 使用可能

## SAI マッピング
- SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP として create

## ソース
- sonic-pfc-priority-priority-group-map.yang (sonic-buildimage sha 9ea932ec)
- orchagent/qosorch.cpp (sonic-swss)
