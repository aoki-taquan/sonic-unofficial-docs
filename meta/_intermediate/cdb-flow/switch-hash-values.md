# SWITCH_HASH — 値依存挙動調査メモ

## ソース

- `sonic-hash.yang` (sonic-buildimage@9ea932ec)
- `sonic-types.yang.j2` (hash-algorithm typedef)
- `orchagent/switchorch.cpp` (SwitchOrch, Generic Hash)

## hash-field enum 全値

`IN_PORT` / `DST_MAC` / `SRC_MAC` / `ETHERTYPE` / `VLAN_ID` / `IP_PROTOCOL` /
`DST_IP` / `SRC_IP` / `L4_DST_PORT` / `L4_SRC_PORT` /
`INNER_DST_MAC` / `INNER_SRC_MAC` / `INNER_ETHERTYPE` / `INNER_IP_PROTOCOL` /
`INNER_DST_IP` / `INNER_SRC_IP` / `INNER_L4_DST_PORT` / `INNER_L4_SRC_PORT` /
`IPV6_FLOW_LABEL`

## hash-algorithm enum 全値

`CRC` / `XOR` / `RANDOM` / `CRC_32LO` / `CRC_32HI` / `CRC_CCITT` / `CRC_XOR`

## 値依存挙動

| フィールド | 値 | SAI 挙動 | 備考 |
|-----------|----|---------|----|
| `ecmp_hash` / `lag_hash` | ASICがサポートしないフィールドを含む | SET 拒否 (`capability is not supported`) | capability は SAI から起動時取得 |
| `ecmp_hash_algorithm` / `lag_hash_algorithm` | ASICがサポートしないアルゴリズム | SET 拒否 (同上) | |
| 任意 | DEL | 拒否 (`operation is not supported`) | 削除不可 |

## enum なし明示

- `ecmp_hash` / `lag_hash`: 上記 19 値の leaf-list。YANG `ordered-by user`。
- `ecmp_hash_algorithm` / `lag_hash_algorithm`: 上記 7 値の enum。
