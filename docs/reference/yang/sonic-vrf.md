---
title: sonic-vrf YANG
description: "sonic-vrf YANG — Virtual Routing and Forwarding (VRF) instance configuration for L3 traffic isolation"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vrf.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [VRF]
  cli: ["config vrf"]
  yang: []
---

# sonic-vrf YANG

## 概要

- module: `sonic-vrf`
- namespace: `http://github.com/sonic-net/sonic-vrf`
- revision: `2021-03-30`
- import: `sonic-types`
- top container: `sonic-vrf`

Virtual Routing and Forwarding (VRF) instance configuration for L3 traffic isolation[^1]

## ツリー

```
module: sonic-vrf
  +--rw sonic-vrf
     +--rw VRF
        +--rw VRF_LIST* [name]
           +--rw name        stypes:interface_name
           +--rw fallback?   boolean
           +--rw vni?        uint32
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-vrf/VRF/VRF_LIST/name` | `stypes:interface_name` | yes |  | pattern `Vrf[a-zA-Z0-9_-]+` | VRF instance name (e.g. Vrf_blue) |
| `fallback` | `sonic-vrf/VRF/VRF_LIST/fallback` | `boolean` |  | false |  | Enable/disable fallback feature which is useful for specified VRF user to access internet through global/main route. |
| `vni` | `sonic-vrf/VRF/VRF_LIST/vni` | `uint32` |  | 0 | range 0..16777215 | VNI mapped to VRF |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `VRF`
- CLI: `config vrf`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`VRF`](../config-db/vrf.md)
- CLI: [`config vrf`](../cli/config-vrf.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-vrf.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

