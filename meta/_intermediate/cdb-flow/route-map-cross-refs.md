# ROUTE_MAP 暗黙参照テーブル抽出 (Phase C)

## ソース

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-map.yang`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## YANG leafref 一覧 (直接参照)

`sonic-route-map.yang` の leafref を全行スキャンして抽出した参照先テーブル:

| フィールド | leafref パス | 参照先テーブル |
|-----------|-------------|--------------|
| `match_interface` (union 1) | `/port:sonic-port/port:PORT/...` | `PORT` |
| `match_interface` (union 2) | `/lag:sonic-portchannel/lag:PORTCHANNEL/...` | `PORTCHANNEL` |
| `match_interface` (union 3) | `/loopback:sonic-loopback-interface/loopback:LOOPBACK_INTERFACE/...` | `LOOPBACK_INTERFACE` |
| `match_prefix_set` | `/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/name` | `PREFIX_SET` |
| `match_ipv6_prefix_set` | `/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/name` | `PREFIX_SET` (YANG leafref あり、frrcfgd 未処理) |
| `match_next_hop_set` | `/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/name` | `PREFIX_SET` |
| `match_src_vrf` (union) | `/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/name` | `VRF` |
| `match_neighbor` (union 1) | `/port:sonic-port/port:PORT/...` | `PORT` |
| `match_neighbor` (union 2) | `/lag:sonic-portchannel/lag:PORTCHANNEL/...` | `PORTCHANNEL` |
| `match_community` | `/rpolsets:COMMUNITY_SET/rpolsets:COMMUNITY_SET_LIST/name` | `COMMUNITY_SET` |
| `match_ext_community` | `/rpolsets:EXTENDED_COMMUNITY_SET/rpolsets:EXTENDED_COMMUNITY_SET_LIST/name` | `EXTENDED_COMMUNITY_SET` |
| `match_as_path` | `/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/name` | `AS_PATH_SET` |
| `call_route_map` | `../../../ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name` | `ROUTE_MAP_SET` |
| `set_community_ref` | `/rpolsets:COMMUNITY_SET/rpolsets:COMMUNITY_SET_LIST/name` | `COMMUNITY_SET` |
| `set_ext_community_ref` | `/rpolsets:EXTENDED_COMMUNITY_SET/rpolsets:EXTENDED_COMMUNITY_SET_LIST/name` | `EXTENDED_COMMUNITY_SET` |

## frrcfgd 逆参照 (ROUTE_MAP から参照される)

`frrcfgd.py` L2671, L1928–1955, L2298–2315 スキャン結果:

- `PREFIX_SET.mode` を動的参照 (IPv4/IPv6 AF 判定) — `match_prefix_set` / `match_next_hop_set` 処理時
- `COMMUNITY_SET` テーブルを `get_table()` で全件読み取り — `match_community` / `set_community_ref` 処理時
- `EXTENDED_COMMUNITY_SET` テーブルを `get_table()` で全件読み取り — `match_ext_community` / `set_ext_community_ref` 処理時
- `AS_PATH_SET` テーブルを `get_table()` で全件読み取り — `match_as_path` 処理時

## ROUTE_MAP を参照する逆方向テーブル

`BGP_NEIGHBOR_AF` / `BGP_PEER_GROUP_AF` の `route_map_in` / `route_map_out` フィールドが `ROUTE_MAP_SET.name` を leafref で参照する。
frrcfgd.py L1903–1904, L90–91 で処理登録を確認。

## 生成メモ

- `match_ipv6_prefix_set`: YANG leafref あり (PREFIX_SET) だが `frrcfgd.route_map_key_map` に対応エントリなし → dead field
- `match_interface` の VLAN: YANG でコメントアウト済み (`//type leafref vlan...`) → 参照不可
- `match_neighbor` の VLAN: 同上コメントアウト
- `set_tag`: `route_map_key_map` に対応エントリなし → dead field
