---
title: sonic-route-common YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-route-common.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: []
  cli: []
  yang: []
---

# sonic-route-common YANG

## 概要

- module: `sonic-route-common`
- namespace: `http://github.com/sonic-net/sonic-route-common`
- revision: `2021-02-26`
- import: `sonic-vrf`, `sonic-route-map`
- top container: `sonic-route-common`

SONIC ROUTE common YANG[^1]

## ツリー

```
module: sonic-route-common
  +--rw sonic-route-common
     +--rw ROUTE_REDISTRIBUTE
        +--rw ROUTE_REDISTRIBUTE_LIST* [vrf_name src_protocol dst_protocol addr_family]
           +--rw vrf_name        union
           +--rw src_protocol    string
           +--rw dst_protocol    string
           +--rw addr_family     string
           +--rw route_map*      -> /rmap:sonic-route-map/ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name
           +--rw metric?         uint32
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `vrf_name` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/vrf_name` | `union` | yes |  | union(string, leafref) | VRF name |
| `src_protocol` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/src_protocol` | `string` | yes |  |  | IP protocols such as connected, ospf and static |
| `dst_protocol` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/dst_protocol` | `string` | yes |  |  | IP protocol such as bgp |
| `addr_family` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/addr_family` | `string` | yes |  |  | Address family ipv4/ipv6 |
| `route_map` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/route_map` | `leafref` |  |  | /rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name | Router filter to apply while redistributing the routes from another protocol. |
| `metric` | `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/metric` | `uint32` |  |  |  | Metric for redistributed routes |

## leafref / 依存

- `sonic-route-common/ROUTE_REDISTRIBUTE/ROUTE_REDISTRIBUTE_LIST/route_map` → `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- 関連 CLI / CONFIG_DB は本ページからは未リンク（CONFIG_DB のテーブル名は本モジュールの top-level container と一致するのが通例）

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-route-common.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

