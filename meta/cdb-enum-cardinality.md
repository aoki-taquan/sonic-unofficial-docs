# CDB enum cardinality report

本ファイルは `meta/scripts/scan_cdb_enum_cardinality.py` の出力。
高カーディナリティ enum を持つ CDB ページは値別深掘りで dilution されるので、
値別解析バッチを以下のサイズに分けると過学習なく汎用に深さを揃えられる。

| tier | 閾値 | 推奨 batch サイズ |
|---|---|---|
| high | enum 値 ≥ 15 | 1 page / agent |
| mid | 6 ≤ values < 15 | 3 pages / agent |
| low | values < 6 | 12 pages / agent |

## high tier (1)

- `device-metadata` — max=35 — fields: `default_bgp_status`=2, `docker_routing_config_mode`=4, `default_pfcwd_status`=2, `type`=35, `buffer_model`=2, `synchronous_mode`=2, `subtype`=5, `switch_type`=6, `suppress-fib-pending`=2, `async_swss_rec`=2, `nexthop_group`=2, `zebra_nexthop`=2

## mid tier (3)

- `acl-rule` — max=7 — fields: `stage`=2, `type`=4, `PACKET_ACTION`=3, `IP_TYPE`=7, `ETHER_TYPE`=7
- `acl-table` — max=7 — fields: `stage`=2, `type`=4, `PACKET_ACTION`=3, `IP_TYPE`=7, `ETHER_TYPE`=7
- `wred-profile` — max=8 — fields: `ecn`=8

## low tier (117)

low tier は通常の 12 ページ/agent で十分。詳細は JSON 参照。
