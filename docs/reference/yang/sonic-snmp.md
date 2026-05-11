---
title: sonic-snmp YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-snmp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SNMP, SNMP_COMMUNITY, SNMP_USER, SNMP_AGENT_ADDRESS_CONFIG]
  cli: ["config snmp", "show snmp"]
  yang: []
---

# sonic-snmp YANG

## 概要

- module: `sonic-snmp`
- namespace: `http://github.com/sonic-net/sonic-snmp`
- revision: `2022-05-13`
- import: `ietf-inet-types`
- top container: `sonic-snmp`

SNMP agent global configuration（contact, location）と community, SNMPv3 user, listening agent address を持つ[^1]。

## ツリー

```
module: sonic-snmp
  +--rw sonic-snmp
     +--rw SNMP
     |  +--rw CONTACT
     |  |  +--rw Contact?   string
     |  +--rw LOCATION
     |     +--rw Location?   string
     +--rw SNMP_COMMUNITY
     |  +--rw SNMP_COMMUNITY_LIST* [name]
     |     +--rw name    string
     |     +--rw TYPE?   enumeration
     +--rw SNMP_USER
     |  +--rw SNMP_USER_LIST* [name]
     |     +--rw name                             string
     |     +--rw SNMP_USER_TYPE                   enumeration
     |     +--rw SNMP_USER_PERMISSION             enumeration
     |     +--rw SNMP_USER_AUTH_TYPE?             string
     |     +--rw SNMP_USER_AUTH_PASSWORD?         string
     |     +--rw SNMP_USER_ENCRYPTION_TYPE?       string
     |     +--rw SNMP_USER_ENCRYPTION_PASSWORD    string
     +--rw SNMP_AGENT_ADDRESS_CONFIG
        +--rw SNMP_AGENT_ADDRESS_CONFIG_LIST* [agent_ip port vrf_name]
           +--rw agent_ip    inet:ip-address
           +--rw port        union
           +--rw vrf_name    union
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `Contact` | `sonic-snmp/SNMP/CONTACT/Contact` | `string` |  |  | length 1..255 | SNMP System Contact |
| `Location` | `sonic-snmp/SNMP/LOCATION/Location` | `string` |  |  | length 1..255 | SNMP System Location |
| `name` | `sonic-snmp/SNMP_COMMUNITY/SNMP_COMMUNITY_LIST/name` | `string` | yes |  | length 4..32 | Community string |
| `TYPE` | `sonic-snmp/SNMP_COMMUNITY/SNMP_COMMUNITY_LIST/TYPE` | `enumeration` |  |  | RO, RW | Type of community, read-only or read-write |
| `name` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/name` | `string` | yes |  | length 4..32 | SNMPv3 user name |
| `SNMP_USER_TYPE` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_TYPE` | `enumeration` | yes |  | noAuthNoPriv, AuthNoPriv, Priv | Authentication and encryption method used for the user |
| `SNMP_USER_PERMISSION` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_PERMISSION` | `enumeration` | yes |  | RO, RW | Read-only or read-write user permission |
| `SNMP_USER_AUTH_TYPE` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_AUTH_TYPE` | `string` |  |  | MD5, SHA, HMAC-SHA-2 | Authentication type used for user |
| `SNMP_USER_AUTH_PASSWORD` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_AUTH_PASSWORD` | `string` |  |  | length 0..64 | Authentication password for the user |
| `SNMP_USER_ENCRYPTION_TYPE` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_ENCRYPTION_TYPE` | `string` |  |  | AES, DES | Encryption type for the user |
| `SNMP_USER_ENCRYPTION_PASSWORD` | `sonic-snmp/SNMP_USER/SNMP_USER_LIST/SNMP_USER_ENCRYPTION_PASSWORD` | `string` | yes |  |  | Encryption password for the user |
| `agent_ip` | `sonic-snmp/SNMP_AGENT_ADDRESS_CONFIG/SNMP_AGENT_ADDRESS_CONFIG_LIST/agent_ip` | `inet:ip-address` | yes |  |  | SNMP agent listening IP |
| `port` | `sonic-snmp/SNMP_AGENT_ADDRESS_CONFIG/SNMP_AGENT_ADDRESS_CONFIG_LIST/port` | `union` | yes |  | union(uint16, empty) | SNMP agent listening UDP port |
| `vrf_name` | `sonic-snmp/SNMP_AGENT_ADDRESS_CONFIG/SNMP_AGENT_ADDRESS_CONFIG_LIST/vrf_name` | `union` | yes |  | union(string, empty) | VRF in which the agent listens |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SNMP`, `SNMP_COMMUNITY`, `SNMP_USER`, `SNMP_AGENT_ADDRESS_CONFIG`
- CLI: `config snmp`, `show snmp`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-snmp.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
