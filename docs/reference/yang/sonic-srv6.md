---
title: sonic-srv6 YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-srv6.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SRV6_MY_LOCATORS, SRV6_MY_SIDS]
  cli: []
  yang: [sonic-vrf]
---

# sonic-srv6 YANG

## 概要

- module: `sonic-srv6`
- namespace: `http://github.com/sonic-net/sonic-srv6`
- revision: `2024-12-05`
- import: `ietf-inet-types`, `sonic-vrf`
- top container: `sonic-srv6`

Segment Routing over IPv6 (SRv6) configuration for SONiC.[^1]

## ツリー

```
module: sonic-srv6
  +--rw sonic-srv6
     +--rw SRV6_MY_LOCATORS
     |  +--rw SRV6_MY_LOCATORS_LIST* [locator_name]
     |     +--rw locator_name    string
     |     +--rw prefix          inet:ipv6-address
     |     +--rw block_len?      uint8
     |     +--rw node_len?       uint8
     |     +--rw func_len?       uint8
     |     +--rw arg_len?        uint8
     |     +--rw vrf?            union
     +--rw SRV6_MY_SIDS
        +--rw SRV6_MY_SIDS_LIST* [locator ip_prefix]
           +--rw ip_prefix         inet:ipv6-prefix
           +--rw locator           -> /srv6:sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/locator_name
           +--rw action?           enumeration
           +--rw decap_vrf?        union
           +--rw decap_dscp_mode?  enumeration
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `locator_name` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/locator_name` | `string` | yes |  |  | SRv6 locator name. |
| `prefix` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/prefix` | `inet:ipv6-address` | yes |  |  | IPv6 address prefix for this locator. |
| `block_len` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/block_len` | `uint8` |  | `32` | range 1..128 | Length in bits of the SRv6 locator block portion. |
| `node_len` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/node_len` | `uint8` |  | `16` | range 1..128 | Length in bits of the SRv6 locator node portion. |
| `func_len` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/func_len` | `uint8` |  | `16` | range 0..128 | Length in bits of the SRv6 SID function portion. |
| `arg_len` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/arg_len` | `uint8` |  | `0` | range 0..128 | Length in bits of the SRv6 SID argument portion. |
| `vrf` | `sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/vrf` | `union` |  | `default` | leafref(VRF) or `default` | VRF name. |
| `ip_prefix` | `sonic-srv6/SRV6_MY_SIDS/SRV6_MY_SIDS_LIST/ip_prefix` | `inet:ipv6-prefix` | yes |  |  | IPv6 prefix representing this SID. |
| `locator` | `sonic-srv6/SRV6_MY_SIDS/SRV6_MY_SIDS_LIST/locator` | `leafref` | yes |  | /srv6:sonic-srv6/srv6:SRV6_MY_LOCATORS/srv6:SRV6_MY_LOCATORS_LIST/srv6:locator_name | Reference to the parent SRv6 locator. |
| `action` | `sonic-srv6/SRV6_MY_SIDS/SRV6_MY_SIDS_LIST/action` | `enumeration` |  |  | `uN`, `uDT46` | SRv6 endpoint behavior (uN for prefix SID, uDT46 for decap with VRF lookup). |
| `decap_vrf` | `sonic-srv6/SRV6_MY_SIDS/SRV6_MY_SIDS_LIST/decap_vrf` | `union` |  | `default` | leafref(VRF) or `default` | VRF name used for decapsulation. |
| `decap_dscp_mode` | `sonic-srv6/SRV6_MY_SIDS/SRV6_MY_SIDS_LIST/decap_dscp_mode` | `enumeration` |  |  | `uniform`, `pipe` | DSCP handling mode for decapsulated packets. |

## must 制約

- `SRV6_MY_LOCATORS_LIST`: `block_len + node_len + func_len + arg_len <= 128`

## leafref / 依存

- `SRV6_MY_LOCATORS_LIST/vrf` → `/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name`
- `SRV6_MY_SIDS_LIST/locator` → `/srv6:sonic-srv6/srv6:SRV6_MY_LOCATORS/srv6:SRV6_MY_LOCATORS_LIST/srv6:locator_name`
- `SRV6_MY_SIDS_LIST/decap_vrf` → `/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SRV6_MY_LOCATORS`, `SRV6_MY_SIDS`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-srv6.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
