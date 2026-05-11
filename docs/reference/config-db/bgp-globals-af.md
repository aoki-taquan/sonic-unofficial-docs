---
title: BGP_GLOBALS_AF テーブル
description: "BGP_GLOBALS_AF テーブル — BGP_GLOBALS_AF は BGP_GLOBALS の VRF ごとに、address-family / subsequent address-family 単位の BGP 設定を保持する CONFIG_DB テーブル。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - BGP_GLOBALS_AF
    - BGP_GLOBALS_AF_AGGREGATE_ADDR
    - BGP_GLOBALS_AF_NETWORK
  cli:
    - config bgp
  yang:
    - sonic-bgp-global
---

# BGP_GLOBALS_AF テーブル

## 概要

`BGP_GLOBALS_AF` は `BGP_GLOBALS` の VRF ごとに、address-family / subsequent address-family 単位の BGP 設定を保持する CONFIG_DB テーブル。multipath、VRF import、route download filter、distance、route flap dampening、EVPN/VXLAN 関連フラグを扱う[^1]。派生テーブルとして、aggregate-address を定義する `BGP_GLOBALS_AF_AGGREGATE_ADDR` と、network statement を定義する `BGP_GLOBALS_AF_NETWORK` がある。実装側のテーブル名定数は `schema.h` も参照する[^2]。

## key 構造

```text
BGP_GLOBALS_AF|<vrf_name>|<afi_safi>
BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf_name>|<afi_safi>|<ip_prefix>
BGP_GLOBALS_AF_NETWORK|<vrf_name>|<afi_safi>|<ip_prefix>
```

`<vrf_name>` は `BGP_GLOBALS.vrf_name` への leafref。`<afi_safi>` は address family 名文字列。

## 主要フィールド

### BGP_GLOBALS_AF

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `max_ebgp_paths` | uint16 1..256 | `1` | eBGP multipath 最大数 |
| `max_ibgp_paths` | uint16 1..256 | `1` | iBGP multipath 最大数 |
| `import_vrf` | `default` or leafref `BGP_GLOBALS.vrf_name` | - | route import 元 VRF |
| `import_vrf_route_map` | leafref `ROUTE_MAP_SET.name` | - | VRF import 時の route filter |
| `route_download_filter` | leafref `ROUTE_MAP_SET.name` | - | FIB download を絞る table-map |
| `ebgp_route_distance` | uint8 1..255 | - | eBGP route distance |
| `ibgp_route_distance` | uint8 1..255 | - | iBGP route distance |
| `local_route_distance` | uint8 1..255 | - | local route distance |
| `ibgp_equal_cluster_length` | boolean | - | iBGP multipath 比較で cluster-list length を揃える |
| `route_flap_dampen` | boolean | - | route flap dampening 有効化 |
| `route_flap_dampen_half_life` | uint8 1..45 | - | dampening half-life |
| `route_flap_dampen_reuse_threshold` | uint16 1..20000 | - | reuse threshold |
| `route_flap_dampen_suppress_threshold` | uint16 1..20000 | - | suppress threshold |
| `route_flap_dampen_max_suppress` | uint8 1..255 | - | max suppress duration |
| `autort` | enum `rfc8365-compatible` | - | RFC8365 互換 route-target 自動生成 |
| `advertise-all-vni` | boolean | - | L2VPN で全 VNI を advertise |
| `advertise-svi-ip` | boolean | - | local SVI IP を remote VTEP へ advertise |

### BGP_GLOBALS_AF_AGGREGATE_ADDR

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ip_prefix` | ip-prefix | aggregate address |
| `as_set` | boolean | AS set path 情報を生成 |
| `summary_only` | boolean | more specific route の update を抑制 |
| `policy` | leafref `ROUTE_MAP_SET.name` | aggregate network に適用する route-map |

### BGP_GLOBALS_AF_NETWORK

| フィールド | 型 | 説明 |
|-----------|----|------|
| `ip_prefix` | ip-prefix | network statement の prefix |
| `policy` | leafref `ROUTE_MAP_SET.name` | attribute 変更用 route-map |
| `backdoor` | boolean | backdoor route 指定 |

## 制約

- `vrf_name` は `BGP_GLOBALS` への leafref。
- `import_vrf` は自分自身の `vrf_name` と同じ値を禁止する `must` を持つ。
- `route_flap_dampen*` は `afi_safi = 'ipv4_unicast'` の場合のみ許可される。
- `policy` / route-map 系 field は `ROUTE_MAP_SET` への leafref。

## 購読者

- `bgpcfgd`: CONFIG_DB の BGP global AF 設定を FRR address-family 設定へ変換する。
- `frr-mgmt-framework`: `DEVICE_METADATA.frr_mgmt_framework_config = true` のときに generic BGP model として処理する。
- `bgpd` (FRR): vtysh / mgmt framework 経由で最終的な AF 設定を保持する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BGP_GLOBALS`、`BGP_NEIGHBOR_AF`、`BGP_PEER_GROUP_AF`、`ROUTE_MAP_SET`、`VRF`
- 関連 CLI: `config bgp`
- 関連 YANG: `sonic-bgp-global`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-bgp-global`](../yang/sonic-bgp-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-global.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-global.yang>
[^2]: テーブル名定数参照: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>
