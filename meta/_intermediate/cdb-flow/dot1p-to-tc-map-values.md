# DOT1P_TO_TC_MAP フィールド値分析

## マップ値フィールド

### `dot1p` (string pattern [0-7])
- `0`..`7` → 802.1p PCP 値。qosorch が SAI_QOS_MAP_TYPE_DOT1P_TO_TC エントリを生成
- 範囲外（8 以上等）→ YANG pattern 違反で reject

### `tc` (tc_type, 0..7)
- `0`..`7` → Traffic Class 番号。SAI QoS map オブジェクトの tc 値
- 8 以上 → ASIC が拒否（SAI エラー）

## cross-cutting
- PORT_QOS_MAP.dot1p_to_tc_map から参照されない限り、定義しても SAI に反映されない（有効化されない）
- マップ名変更（削除 + 再作成）は qosorch が DELETE / SET を連続で受け取るため、一時的な SAI オブジェクト削除が発生する
- enum なし。キー→値は任意の 0-7 のペアで構成でき、8 エントリが全 PCP 値をカバーする典型パターン
