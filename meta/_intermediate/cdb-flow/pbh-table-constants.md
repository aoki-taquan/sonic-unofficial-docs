# PBH_TABLE ハードコード定数 (Phase E)

ソース:
- `sonic-net/sonic-swss` `orchagent/pbhorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-net/sonic-utilities` `config/plugins/pbh.py` @ (latest)
- `sonic-net/sonic-swss` `tests/dvslib/dvs_pbh.py` @ (latest)

## CONFIG_DB テーブル名定数

| 定数名 | 値 | 用途 |
|--------|----|------|
| `PBH_TABLE_CDB` (pbh.py:47) | `"PBH_TABLE"` | CLI プラグインが CONFIG_DB 上で PBH テーブルを操作する際のテーブル名 |
| `PBH_RULE_CDB` (pbh.py:48) | `"PBH_RULE"` | PBH ルールテーブル名 |
| `PBH_HASH_CDB` (pbh.py:49) | `"PBH_HASH"` | PBH ハッシュテーブル名 |
| `PBH_HASH_FIELD_CDB` (pbh.py:50) | `"PBH_HASH_FIELD"` | PBH ハッシュフィールドテーブル名 |

## フィールド名定数 (pbh.py:52-70)

| 定数名 | 値 | 対象テーブル |
|--------|----|------------|
| `PBH_TABLE_INTERFACE_LIST` | `"interface_list"` | PBH_TABLE |
| `PBH_TABLE_DESCRIPTION` | `"description"` | PBH_TABLE |
| `PBH_RULE_PRIORITY` | `"priority"` | PBH_RULE |
| `PBH_RULE_GRE_KEY` | `"gre_key"` | PBH_RULE |
| `PBH_RULE_ETHER_TYPE` | `"ether_type"` | PBH_RULE |
| `PBH_RULE_IP_PROTOCOL` | `"ip_protocol"` | PBH_RULE |
| `PBH_RULE_IPV6_NEXT_HEADER` | `"ipv6_next_header"` | PBH_RULE |
| `PBH_RULE_L4_DST_PORT` | `"l4_dst_port"` | PBH_RULE |
| `PBH_RULE_INNER_ETHER_TYPE` | `"inner_ether_type"` | PBH_RULE |
| `PBH_RULE_HASH` | `"hash"` | PBH_RULE |
| `PBH_RULE_PACKET_ACTION` | `"packet_action"` | PBH_RULE |
| `PBH_RULE_FLOW_COUNTER` | `"flow_counter"` | PBH_RULE |
| `PBH_HASH_HASH_FIELD_LIST` | `"hash_field_list"` | PBH_HASH |
| `PBH_HASH_FIELD_HASH_FIELD` | `"hash_field"` | PBH_HASH_FIELD |
| `PBH_HASH_FIELD_IP_MASK` | `"ip_mask"` | PBH_HASH_FIELD |
| `PBH_HASH_FIELD_SEQUENCE_ID` | `"sequence_id"` | PBH_HASH_FIELD |

## SAI ACL バインドポイント定数 (pbhorch.cpp:244-245)

`PbhOrch::createPbhTable()` 内で静的に定義される ACL テーブル型。CONFIG_DB では表現されずバイナリにハードコードされる。

| 定数名 | 値 | 意味 |
|--------|----|------|
| `SAI_ACL_BIND_POINT_TYPE_PORT` | SAI enum | PBH ACL テーブルを物理ポートにバインド可能 |
| `SAI_ACL_BIND_POINT_TYPE_LAG` | SAI enum | PBH ACL テーブルを LAG にバインド可能 |

## SAI ACL マッチフィールド定数 (pbhorch.cpp:246-251)

PBH ACL テーブル型に固定的に追加されるマッチフィールド群。`interface_list` 経由で SAI に展開される前提フィールドセット。

| 定数名 | 意味 |
|--------|------|
| `SAI_ACL_TABLE_ATTR_FIELD_GRE_KEY` | GRE キーマッチ |
| `SAI_ACL_TABLE_ATTR_FIELD_ETHER_TYPE` | イーサタイプマッチ |
| `SAI_ACL_TABLE_ATTR_FIELD_IP_PROTOCOL` | IP プロトコルマッチ |
| `SAI_ACL_TABLE_ATTR_FIELD_IPV6_NEXT_HEADER` | IPv6 Next Header マッチ |
| `SAI_ACL_TABLE_ATTR_FIELD_L4_DST_PORT` | L4 dst port マッチ |
| `SAI_ACL_TABLE_ATTR_FIELD_INNER_ETHER_TYPE` | inner ether type マッチ |

## ACL ステージ定数 (pbhorch.cpp:260)

| 定数名 | 値 | 意味 |
|--------|----|------|
| `ACL_STAGE_INGRESS` | enum | PBH テーブルは常に ingress ステージで適用。CONFIG_DB にステージフィールドは存在しない（固定値） |
