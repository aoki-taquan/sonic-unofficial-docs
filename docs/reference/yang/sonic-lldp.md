---
title: sonic-lldp YANG
description: "sonic-lldp YANG — : sonic-net/sonic-buildimage src/sonic-yang-models/yang-models/sonic-lldp.yang @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-lldp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [LLDP, LLDP_PORT]
  cli: ["show lldp"]
  yang: [sonic-port]
---

# sonic-lldp YANG

## 概要

- module: `sonic-lldp`
- namespace: `http://github.com/sonic-net/sonic-lldp`
- revision: `2021-07-08`
- import: `sonic-port`
- top container: `sonic-lldp`

SONiC LLDP yang model[^1]

## ツリー

```
module: sonic-lldp
  +--rw sonic-lldp
     +--rw LLDP
     |  +--rw GLOBAL
     |     +--rw hello_time?                     uint8
     |     +--rw multiplier?                     uint8
     |     +--rw system_name?                    string
     |     +--rw system_description?             string
     |     +--rw supp_mgmt_address_tlv?          boolean
     |     +--rw supp_system_capabilities_tlv?   boolean
     |     +--rw enabled?                        boolean
     |     +--rw mode?                           enumeration
     +--rw LLDP_PORT
        +--rw LLDP_PORT_LIST* [ifname]
           +--rw ifname     -> /prt:sonic-port/PORT/PORT_LIST/name
           +--rw enabled?   boolean
           +--rw mode?      enumeration
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-lldp` |  |  |
| `container` | `sonic-lldp/LLDP` |  |  |
| `container` | `sonic-lldp/LLDP/GLOBAL` |  |  |
| `container` | `sonic-lldp/LLDP_PORT` |  |  |
| `list` | `sonic-lldp/LLDP_PORT/LLDP_PORT_LIST` | `ifname` |  |

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `hello_time` | `sonic-lldp/LLDP/GLOBAL/hello_time` | `uint8` |  | 30 | range `5..254` | It is the time interval at which periodic hellos are exchanged. Default is 30 seconds |
| `multiplier` | `sonic-lldp/LLDP/GLOBAL/multiplier` | `uint8` |  | 4 | range `1..10` | This multiplier value is used to determine the timeout interval (i.e. hello-time x multiplier value) after which LLDP neighbor entry is deleted. |
| `system_name` | `sonic-lldp/LLDP/GLOBAL/system_name` | `string` |  |  |  | System administratively assigned name |
| `system_description` | `sonic-lldp/LLDP/GLOBAL/system_description` | `string` |  |  |  | System description |
| `supp_mgmt_address_tlv` | `sonic-lldp/LLDP/GLOBAL/supp_mgmt_address_tlv` | `boolean` |  | false |  | Suppress sending of Management Address TLV in LLDP frames |
| `supp_system_capabilities_tlv` | `sonic-lldp/LLDP/GLOBAL/supp_system_capabilities_tlv` | `boolean` |  | false |  | Suppress sending of System Capabilities TLV in LLDP frames |
| `ifname` | `sonic-lldp/LLDP_PORT/LLDP_PORT_LIST/ifname` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Reference of port on which LLDP to be configured. |

## leafref / 依存

- `sonic-lldp/LLDP_PORT/LLDP_PORT_LIST/ifname` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `LLDP`
- CONFIG_DB: `LLDP_PORT`
- CLI: `show lldp`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`LLDP`](../config-db/lldp.md) / [`LLDP_PORT`](../config-db/lldp-port.md)
- CLI: [`show lldp`](../cli/show-lldp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-lldp.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
