# pbh 例外条件エビデンス

## 調査ソース

- `sonic-swss/orchagent/pbhorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-pbh.yang`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `PBH_HASH_FIELD.hash_field` は mandatory。`sequence_id` も mandatory。
- `ip_mask` は `when` 条件付き: IPv4 フィールドに `:` を含む address、または IPv6 フィールドに `.` を含む address は `must` 違反で reject。
- `PBH_HASH.hash_field_list` は `min-elements 1` → 空リストは reject。
- `PBH_TABLE.interface_list` は `min-elements 1`、かつ leafref で PORT または PORTCHANNEL 参照必須。
- `PBH_RULE.hash` は leafref → `PBH_HASH` 参照必須 (mandatory)。
- `PBH_RULE.table_name` は leafref → `PBH_TABLE` 参照必須。

### consumer (orchagent) 例外動作
- 重複 SET (SAI object already exists): `Failed to create PBH table(%s) in SAI: object already exists` → `return false` (pbhorch.cpp:237)
- type / stage / ports / validate 失敗: 各 `SWSS_LOG_ERROR` + `return false` (pbhorch.cpp:256-295)
- 能力チェック失敗 (ADD/UPDATE/REMOVE field 不対応): `unsupported capabilities` → `return false` (pbhorch.cpp:327-340)
- DEL で存在しない table: `object doesn't exist` → `return false` (pbhorch.cpp:384)
- `packet_action` default: `SET_ECMP_HASH`、`flow_counter` default: `DISABLED`
