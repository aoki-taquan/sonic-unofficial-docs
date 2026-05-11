---
title: sonic-bgp-peerrange YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-peerrange.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_PEER_RANGE]
  cli: []
  yang: [sonic-bgp-global, sonic-vrf, sonic-vnet]
---

# sonic-bgp-peerrange YANG

## 概要

- module: `sonic-bgp-peerrange`
- namespace: `http://github.com/sonic-net/sonic-bgp-peerrange`
- revision: `2022-02-24`
- import: `ietf-inet-types`, `sonic-types`, `sonic-vrf`, `sonic-vnet`
- top container: `sonic-bgp-peerrange`

SONIC BGP Peer Range YANG。 BGP dynamic neighbor (listen range) 設定を VRF/VNET 別、 およびテンプレートとして保持する[^1]。

## ツリー

```
module: sonic-bgp-peerrange
  +--rw sonic-bgp-peerrange
     +--rw BGP_PEER_RANGE
        +--rw BGP_PEER_RANGE_LIST* [vrf_name peer_range_name]
        |  +--rw vrf_name           union
        |  +--rw peer_range_name    string
        |  +--rw name?              string
        |  +--rw src_address?       inet:ip-address
        |  +--rw peer_asn?          uint32
        |  +--rw ip_range*          stypes:sonic-ip-prefix
        +--rw BGP_PEER_RANGE_TEMPLATE_LIST* [peer_range_name]
           +--rw peer_range_name    string
           +--rw name?              string
           +--rw src_address?       inet:ip-address
           +--rw peer_asn?          uint32
           +--rw ip_range*          stypes:sonic-ip-prefix
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `vrf_name` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/vrf_name` | `union` | yes |  | VRF または VNET leafref | VRF or VNET name for this peer range |
| `peer_range_name` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/peer_range_name` | `string` | yes |  |  | Peer range name |
| `name` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/name` | `string` |  |  |  | Peer range display name; must match the key |
| `src_address` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/src_address` | `inet:ip-address` |  |  |  | Source address for the connection |
| `peer_asn` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/peer_asn` | `uint32` |  |  | range 1..4294967295 | Peer AS number |
| `ip_range` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_LIST/ip_range` | `leaf-list stypes:sonic-ip-prefix` |  |  | ordered-by user | A range of addresses (listen subnet) |
| `peer_range_name` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_TEMPLATE_LIST/peer_range_name` | `string` | yes |  |  | Template peer range name |
| `name` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_TEMPLATE_LIST/name` | `string` |  |  |  | Template display name; must match the key |
| `src_address` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_TEMPLATE_LIST/src_address` | `inet:ip-address` |  |  |  | Source address for the connection |
| `peer_asn` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_TEMPLATE_LIST/peer_asn` | `uint32` |  |  |  | Peer AS number |
| `ip_range` | `sonic-bgp-peerrange/BGP_PEER_RANGE/BGP_PEER_RANGE_TEMPLATE_LIST/ip_range` | `leaf-list stypes:sonic-ip-prefix` |  |  |  | A range of addresses (listen subnet) |

## leafref / 依存

- `BGP_PEER_RANGE_LIST/vrf_name` → VRF または VNET 名

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BGP_PEER_RANGE`
- CLI: なし（`bgpcfgd` が config_db.json から読み取り FRR `bgp listen range` に反映）

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BGP_PEER_RANGE`](../config-db/bgp-peer-range.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-peerrange.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
