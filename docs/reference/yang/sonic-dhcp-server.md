---
title: sonic-dhcp-server YANG
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [DHCP_SERVER]
  cli: []
  yang: []
---

# sonic-dhcp-server YANG

## 概要

- module: `sonic-dhcp-server`
- namespace: `http://github.com/sonic-net/sonic-dhcp-server`
- revision: `2022-09-23`
- import: `ietf-inet-types`
- top container: `sonic-dhcp-server`

DHCP SERVER YANG module for SONiC OS[^1]

## ツリー

```
module: sonic-dhcp-server
  +--rw sonic-dhcp-server
     +--rw DHCP_SERVER
        +--rw DHCP_SERVER_LIST* [ip]
           +--rw ip    inet:ip-address
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-dhcp-server` |  |  |
| `container` | `sonic-dhcp-server/DHCP_SERVER` |  | DHCP server IP addresses used for relay forwarding |
| `list` | `sonic-dhcp-server/DHCP_SERVER/DHCP_SERVER_LIST` | `ip` | List of IPs in DHCP_SERVER Table |

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ip` | `sonic-dhcp-server/DHCP_SERVER/DHCP_SERVER_LIST/ip` | `inet:ip-address` | yes |  |  | IP as DHCP_SERVER |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `DHCP_SERVER`
- CLI: なし

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `DHCP_SERVER`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dhcp-server.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
