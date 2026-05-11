---
title: sonic-mux-cable YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-mux-cable.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [MUX_CABLE]
  cli: ["config mux", "show mux"]
  yang: [sonic-port, sonic-tunnel, sonic-peer-switch]
---

# sonic-mux-cable YANG

## 概要

- module: `sonic-mux-cable`
- namespace: `http://github.com/sonic-net/sonic-mux-cable`
- revision: `2022-08-19`
- import: `ietf-inet-types`, `sonic-port`
- top container: `sonic-mux-cable`

DualToR 構成における MUX cable のポート別状態（cable type, prober, neighbor, server/SoC IP, MUX state）を保持する[^1]。

## ツリー

```
module: sonic-mux-cable
  +--rw sonic-mux-cable
     +--rw MUX_CABLE
        +--rw MUX_CABLE_LIST* [ifname]
           +--rw ifname           -> /prt:sonic-port/PORT/PORT_LIST/name
           +--rw cable_type?      enumeration
           +--rw prober_type?     enumeration
           +--rw neighbor_mode?   enumeration
           +--rw server_ipv4?     inet:ipv4-prefix
           +--rw server_ipv6?     inet:ipv6-prefix
           +--rw soc_ipv4?        inet:ipv4-prefix
           +--rw soc_ipv6?        inet:ipv6-prefix
           +--rw state?           enumeration
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ifname` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/ifname` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Port on which MUX cable is configured |
| `cable_type` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/cable_type` | `enumeration` |  |  | active-active, active-standby | SONiC DualToR interface cable type |
| `prober_type` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/prober_type` | `enumeration` |  |  | active, passive | DualToR LinkMgrd ICMP prober mode |
| `neighbor_mode` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/neighbor_mode` | `enumeration` |  |  |  | DualToR MUX neighbor mode |
| `server_ipv4` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/server_ipv4` | `inet:ipv4-prefix` |  |  |  | Server IPv4 address |
| `server_ipv6` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/server_ipv6` | `inet:ipv6-prefix` |  |  |  | Server IPv6 address |
| `soc_ipv4` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/soc_ipv4` | `inet:ipv4-prefix` |  |  |  | SoC IPv4 address (active-active only) |
| `soc_ipv6` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/soc_ipv6` | `inet:ipv6-prefix` |  |  |  | SoC IPv6 address (active-active only) |
| `state` | `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/state` | `enumeration` |  |  | active, standby, auto, manual | MUX mode determining if auto failover is enabled |

## leafref / 依存

- `sonic-mux-cable/MUX_CABLE/MUX_CABLE_LIST/ifname` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `MUX_CABLE`
- CLI: `config mux`, `show mux`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-mux-cable.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
