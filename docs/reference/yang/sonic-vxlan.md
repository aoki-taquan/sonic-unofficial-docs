---
title: sonic-vxlan YANG
description: "sonic-vxlan YANG — VXLAN tunnel and EVPN NVO configuration for SONiC."
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vxlan.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [VXLAN_TUNNEL, VXLAN_TUNNEL_MAP, VXLAN_EVPN_NVO]
  cli: ["config vxlan"]
  yang: [sonic-vlan, sonic-vrf]
---

# sonic-vxlan YANG

## 概要

- module: `sonic-vxlan`
- namespace: `http://github.com/sonic-net/sonic-vxlan`
- revision: `2021-04-12`
- import: `ietf-inet-types`, `sonic-types`
- top container: `sonic-vxlan`

VXLAN tunnel and EVPN NVO configuration for SONiC.[^1]

## ツリー

```
module: sonic-vxlan
  +--rw sonic-vxlan
     +--rw VXLAN_TUNNEL
     |  +--rw VXLAN_TUNNEL_LIST* [name]
     |     +--rw name        string
     |     +--rw src_ip?     inet:ip-address
     |     +--rw dst_ip?     inet:ip-address
     |     +--rw ttl_mode?   string
     +--rw VXLAN_TUNNEL_MAP
     |  +--rw VXLAN_TUNNEL_MAP_LIST* [name mapname]
     |     +--rw name       -> /sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/name
     |     +--rw mapname    string
     |     +--rw vlan       string
     |     +--rw vni        stypes:vnid_type
     +--rw VXLAN_EVPN_NVO
        +--rw VXLAN_EVPN_NVO_LIST* [name]
           +--rw name           string
           +--rw source_vtep    -> /sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/name
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/name` | `string` | yes |  |  | VXLAN tunnel name. |
| `src_ip` | `sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/src_ip` | `inet:ip-address` |  |  |  | Source VTEP IP address for tunnel origination. |
| `dst_ip` | `sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/dst_ip` | `inet:ip-address` |  |  |  | Destination VTEP IP address for point-to-point tunnels. |
| `ttl_mode` | `sonic-vxlan/VXLAN_TUNNEL/VXLAN_TUNNEL_LIST/ttl_mode` | `string` |  |  | pattern `uniform|pipe` | Decap TTL mode |
| `name` | `sonic-vxlan/VXLAN_TUNNEL_MAP/VXLAN_TUNNEL_MAP_LIST/name` | `leafref` | yes |  | /svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name | Reference to the parent VXLAN tunnel. |
| `mapname` | `sonic-vxlan/VXLAN_TUNNEL_MAP/VXLAN_TUNNEL_MAP_LIST/mapname` | `string` | yes |  |  | Name of the VLAN-to-VNI mapping entry. |
| `vlan` | `sonic-vxlan/VXLAN_TUNNEL_MAP/VXLAN_TUNNEL_MAP_LIST/vlan` | `string` | yes |  | pattern `Vlan([0-9]{1,3}|[1-3][0-9]{3}|[4][0][0-8][0-9]|[4][0][9][...` | VLAN associated with this mapping. |
| `vni` | `sonic-vxlan/VXLAN_TUNNEL_MAP/VXLAN_TUNNEL_MAP_LIST/vni` | `stypes:vnid_type` | yes |  |  | VXLAN Network Identifier mapped to the VLAN. |
| `name` | `sonic-vxlan/VXLAN_EVPN_NVO/VXLAN_EVPN_NVO_LIST/name` | `string` | yes |  |  | EVPN NVO instance name. |
| `source_vtep` | `sonic-vxlan/VXLAN_EVPN_NVO/VXLAN_EVPN_NVO_LIST/source_vtep` | `leafref` | yes |  | /svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name | Reference to the VXLAN tunnel used as the source VTEP. |

## leafref / 依存

- `sonic-vxlan/VXLAN_TUNNEL_MAP/VXLAN_TUNNEL_MAP_LIST/name` → `/svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name`
- `sonic-vxlan/VXLAN_EVPN_NVO/VXLAN_EVPN_NVO_LIST/source_vtep` → `/svxlan:sonic-vxlan/svxlan:VXLAN_TUNNEL/svxlan:VXLAN_TUNNEL_LIST/svxlan:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `VXLAN_TUNNEL`
- CONFIG_DB: `VXLAN_TUNNEL_MAP`
- CONFIG_DB: `VXLAN_EVPN_NVO`
- CLI: `config vxlan`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`VXLAN_TUNNEL`](../config-db/vxlan-tunnel.md) / [`VXLAN_TUNNEL_MAP`](../config-db/vxlan-tunnel-map.md) / [`VXLAN_EVPN_NVO`](../config-db/vxlan-evpn-nvo.md)
- CLI: [`config vxlan`](../cli/config-vxlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-vxlan.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

