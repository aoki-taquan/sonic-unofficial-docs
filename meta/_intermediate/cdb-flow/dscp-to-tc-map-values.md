# DSCP_TO_TC_MAP フィールド値分析

## マップ値フィールド

### `dscp` (key: string 0..63)
- `0`..`63` → DSCP 値。qosorch が SAI_QOS_MAP_TYPE_DSCP_TO_TC エントリを生成
- 範囲外 → YANG 違反で reject

### `tc` (tc_type: 0..7)
- `0`..`7` → Traffic Class。qosorch が SAI QoS map オブジェクトに設定
- 8 以上 → ASIC が拒否（SAI エラー）

## cross-cutting
- PORT_QOS_MAP.dscp_to_tc_map から参照されない限り、定義しても SAI に反映されない
- 典型設定: DSCP EF(46)→TC6, CS6(48)→TC7, AF11-AF23→TC1-TC2 等
- enum なし。全 64 DSCP 値を列挙するか、使用する DSCP のみをスパース定義する（未定義 DSCP はデフォルト TC=0 が一般的）
