# SWITCH_HASH ハードコード定数調査 (Phase E)

調査対象: `sonic-swss/orchagent/switch/switch_schema.h` L1-37
調査日: 2026-05-19

## フィールドキー定数 (switch_schema.h)

`switch_schema.h` が全ての文字列定数を集中管理。`switch_helper.cpp` の lookup map がこれらを使用。

### テーブルフィールド名 (CONFIG_DB キー)

| マクロ名 | 値 |
|---|---|
| `SWITCH_HASH_ECMP_HASH` | `"ecmp_hash"` |
| `SWITCH_HASH_LAG_HASH` | `"lag_hash"` |
| `SWITCH_HASH_ECMP_HASH_ALGORITHM` | `"ecmp_hash_algorithm"` |
| `SWITCH_HASH_LAG_HASH_ALGORITHM` | `"lag_hash_algorithm"` |

### hash-field 有効値定数 (switch_schema.h:5-23)

`swHashHashFieldMap` (`switch_helper.cpp:22-43`) にてこれらを SAI native hash field enum にマッピング:

| マクロ名 | 値 |
|---|---|
| `SWITCH_HASH_FIELD_IN_PORT` | `"IN_PORT"` |
| `SWITCH_HASH_FIELD_DST_MAC` | `"DST_MAC"` |
| `SWITCH_HASH_FIELD_SRC_MAC` | `"SRC_MAC"` |
| `SWITCH_HASH_FIELD_ETHERTYPE` | `"ETHERTYPE"` |
| `SWITCH_HASH_FIELD_VLAN_ID` | `"VLAN_ID"` |
| `SWITCH_HASH_FIELD_IP_PROTOCOL` | `"IP_PROTOCOL"` |
| `SWITCH_HASH_FIELD_DST_IP` | `"DST_IP"` |
| `SWITCH_HASH_FIELD_SRC_IP` | `"SRC_IP"` |
| `SWITCH_HASH_FIELD_L4_DST_PORT` | `"L4_DST_PORT"` |
| `SWITCH_HASH_FIELD_L4_SRC_PORT` | `"L4_SRC_PORT"` |
| `SWITCH_HASH_FIELD_INNER_DST_MAC` | `"INNER_DST_MAC"` |
| `SWITCH_HASH_FIELD_INNER_SRC_MAC` | `"INNER_SRC_MAC"` |
| `SWITCH_HASH_FIELD_INNER_ETHERTYPE` | `"INNER_ETHERTYPE"` |
| `SWITCH_HASH_FIELD_INNER_IP_PROTOCOL` | `"INNER_IP_PROTOCOL"` |
| `SWITCH_HASH_FIELD_INNER_DST_IP` | `"INNER_DST_IP"` |
| `SWITCH_HASH_FIELD_INNER_SRC_IP` | `"INNER_SRC_IP"` |
| `SWITCH_HASH_FIELD_INNER_L4_DST_PORT` | `"INNER_L4_DST_PORT"` |
| `SWITCH_HASH_FIELD_INNER_L4_SRC_PORT` | `"INNER_L4_SRC_PORT"` |
| `SWITCH_HASH_FIELD_IPV6_FLOW_LABEL` | `"IPV6_FLOW_LABEL"` |

19 フィールドのみ有効。これ以外の文字列は `swHashHashFieldMap` のルックアップ失敗 → `LOG_ERROR` + erase。

### hash-algorithm 有効値定数 (switch_schema.h:28-34)

`swHashAlgorithmMap` (`switch_helper.cpp:45-53`) にてこれらを SAI hash algorithm enum にマッピング:

| マクロ名 | 値 | SAI enum |
|---|---|---|
| `SWITCH_HASH_ALGORITHM_CRC` | `"CRC"` | `SAI_HASH_ALGORITHM_CRC` |
| `SWITCH_HASH_ALGORITHM_XOR` | `"XOR"` | `SAI_HASH_ALGORITHM_XOR` |
| `SWITCH_HASH_ALGORITHM_RANDOM` | `"RANDOM"` | `SAI_HASH_ALGORITHM_RANDOM` |
| `SWITCH_HASH_ALGORITHM_CRC_32LO` | `"CRC_32LO"` | `SAI_HASH_ALGORITHM_CRC_32LO` |
| `SWITCH_HASH_ALGORITHM_CRC_32HI` | `"CRC_32HI"` | `SAI_HASH_ALGORITHM_CRC_32HI` |
| `SWITCH_HASH_ALGORITHM_CRC_CCITT` | `"CRC_CCITT"` | `SAI_HASH_ALGORITHM_CRC_CCITT` |
| `SWITCH_HASH_ALGORITHM_CRC_XOR` | `"CRC_XOR"` | `SAI_HASH_ALGORITHM_CRC_XOR` |

7 アルゴリズムのみ有効。YANG の `hash-algorithm` typedef (`sonic-types.yang`) と完全一致。

## エラーログ文字列定数

| ログ文字列 | 発生箇所 |
|---|---|
| `"Failed to parse switch hash key: empty string"` | `switchorch.cpp` doCfgSwitchHashTableTask |
| `"Failed to validate switch ECMP/LAG hash: capability is not supported"` | `switchorch.cpp` setSwitchHash |
| `"Failed to set switch ECMP/LAG hash in SAI"` | `switchorch.cpp` setSwitchHashFieldListSai |
| `"Failed to set switch hash: ASIC and CONFIG DB are diverged"` | `switchorch.cpp` setSwitchHash |
| `"Switch ECMP hash configuration is not supported: skipping ..."` | `switchorch.cpp` setSwitchHash |
| `"Failed to remove switch ECMP/LAG hash configuration: operation is not supported"` | `switchorch.cpp` doSwitchHashTableDeleteTask |
