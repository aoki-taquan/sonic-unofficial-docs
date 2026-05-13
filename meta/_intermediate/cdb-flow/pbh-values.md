# PBH_TABLE / PBH_RULE フィールド値分析

## enum フィールド

### `packet_action` (PBH_RULE)
- `SET_ECMP_HASH` (デフォルト): ECMP hash profile を適用
- `SET_LAG_HASH`: LAG hash profile を適用
- YANG typedef `packet-action`

### `flow_counter` (PBH_RULE)
- `DISABLED` (デフォルト): カウンタ無効
- `ENABLED`: ACL packet/byte カウンタ有効化
- YANG typedef `flow-counter`

### `hash_field` (PBH_HASH_FIELD)
- `INNER_IP_PROTOCOL`
- `INNER_L4_DST_PORT`
- `INNER_L4_SRC_PORT`
- `INNER_DST_IPV4`
- `INNER_SRC_IPV4`
- `INNER_DST_IPV6`
- `INNER_SRC_IPV6`
- YANG typedef `hash-field` (sonic-types:hash-field を絞り込んで定義)

## 条件付きフィールド

### `ip_mask` (PBH_HASH_FIELD)
- `when`: IPv4/IPv6 アドレスフィールド (`INNER_*_IPV4/IPV6`) のみ有効
- `must`: IPv4 フィールドの場合 `.` を含む、IPv6 の場合 `:` を含むアドレスのみ受理

## min-elements 制約
- `PBH_HASH.hash_field_list`: min-elements 1
- `PBH_TABLE.interface_list`: min-elements 1

## ソース
- sonic-pbh.yang (sonic-buildimage sha 9ea932ec)
- orchagent/pbhorch.cpp (sonic-swss)
