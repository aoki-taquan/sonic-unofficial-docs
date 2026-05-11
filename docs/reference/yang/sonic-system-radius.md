---
title: sonic-system-radius YANG
description: "sonic-system-radius YANG — Remote Authentication Dial-In User Service (RADIUS) YANG module for SONiC OS."
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-radius.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [RADIUS, RADIUS_SERVER]
  cli: ["config radius"]
  yang: [sonic-port, sonic-portchannel, sonic-loopback-interface, sonic-mgmt_port, sonic-system-aaa]
---

# sonic-system-radius YANG

## 概要

- module: `sonic-system-radius`
- namespace: `http://github.com/sonic-net/sonic-system-radius`
- revision: `2022-11-11`
- import: `ietf-inet-types`, `sonic-port`, `sonic-portchannel`, `sonic-loopback-interface`, `sonic-mgmt_port`
- top container: `sonic-system-radius`

Remote Authentication Dial-In User Service (RADIUS) YANG module for SONiC OS.[^1]

## typedef

- `auth_type_enumeration`: `pap`, `chap`, `mschapv2`

## ツリー

```
module: sonic-system-radius
  +--rw sonic-system-radius
     +--rw RADIUS
     |  +--rw global
     |     +--rw passkey?      string
     |     +--rw auth_type?    auth_type_enumeration
     |     +--rw src_ip?       inet:ip-address
     |     +--rw nas_ip?       inet:ip-address
     |     +--rw statistics?   boolean
     |     +--rw timeout?      uint16
     |     +--rw retransmit?   uint8
     +--rw RADIUS_SERVER
        +--rw RADIUS_SERVER_LIST* [ipaddress]   (max-elements 8)
           +--rw ipaddress     inet:host
           +--rw auth_port?    inet:port-number
           +--rw passkey?      string
           +--rw auth_type?    auth_type_enumeration
           +--rw priority?     uint8
           +--rw timeout?      uint16
           +--rw retransmit?   uint8
           +--rw vrf?          string
           +--rw src_intf?     union
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `passkey` | `sonic-system-radius/RADIUS/global/passkey` | `string` |  |  | length 1..65, pattern `[^ #,]*` | Default shared secret for authenticating RADIUS server communication. |
| `auth_type` | `sonic-system-radius/RADIUS/global/auth_type` | `auth_type_enumeration` |  | `pap` | `pap`, `chap`, `mschapv2` | Default authentication protocol for RADIUS communication. |
| `src_ip` | `sonic-system-radius/RADIUS/global/src_ip` | `inet:ip-address` |  |  |  | Source IP address used for outgoing RADIUS packets. |
| `nas_ip` | `sonic-system-radius/RADIUS/global/nas_ip` | `inet:ip-address` |  |  |  | NAS-IP-Address attribute sent in outgoing RADIUS packets. |
| `statistics` | `sonic-system-radius/RADIUS/global/statistics` | `boolean` |  |  |  | Enable or disable RADIUS server statistics collection. |
| `timeout` | `sonic-system-radius/RADIUS/global/timeout` | `uint16` |  | `5` | range 1..60 | Default timeout in seconds for RADIUS server responses. |
| `retransmit` | `sonic-system-radius/RADIUS/global/retransmit` | `uint8` |  | `3` | range 0..10 | Default number of times to retransmit a RADIUS request. |
| `ipaddress` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/ipaddress` | `inet:host` | yes |  |  | RADIUS server's Domain name or IP address (IPv4 or IPv6). |
| `auth_port` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/auth_port` | `inet:port-number` |  | `1812` |  | RADIUS authentication port number. |
| `passkey` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/passkey` | `string` |  |  | length 1..65, pattern `[^ #,]*` | Per-server shared secret overriding the global passkey. |
| `auth_type` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/auth_type` | `auth_type_enumeration` |  | `pap` | `pap`, `chap`, `mschapv2` | Per-server authentication protocol. |
| `priority` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/priority` | `uint8` |  |  | range 1..64 | Server selection priority; higher values are tried first. |
| `timeout` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/timeout` | `uint16` |  | `5` | range 1..60 | Per-server response timeout in seconds. |
| `retransmit` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/retransmit` | `uint8` |  | `3` | range 0..10 | Per-server number of retransmit attempts before failing over. |
| `vrf` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/vrf` | `string` |  |  | pattern `mgmt\|default` | VRF used to reach this RADIUS server. |
| `src_intf` | `sonic-system-radius/RADIUS_SERVER/RADIUS_SERVER_LIST/src_intf` | `union` |  |  | leafref(PORT, PORTCHANNEL, LOOPBACK_INTERFACE, MGMT_PORT) or `Vlan<id>` | Source interface to use for RADIUS server communication. |

## leafref / 依存

- `RADIUS_SERVER_LIST/src_intf` → `sonic-port`, `sonic-portchannel`, `sonic-loopback-interface`, `sonic-mgmt_port` 各 LIST/name
- `RADIUS_SERVER_LIST` は最大 8 要素

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `RADIUS|global`, `RADIUS_SERVER|<ipaddress>`
- CLI: `config radius`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`RADIUS`](../config-db/radius.md) / [`RADIUS_SERVER`](../config-db/radius.md)
- CLI: `config radius`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-system-radius.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
