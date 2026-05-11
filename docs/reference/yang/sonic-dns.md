---
title: sonic-dns YANG
description: "sonic-dns YANG — Domain Name System (DNS) resolver configuration YANG module for SONiC OS."
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dns.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [DNS_NAMESERVER, DNS_OPTIONS]
  cli: ["config dns"]
  yang: []
---

# sonic-dns YANG

## 概要

- module: `sonic-dns`
- namespace: `http://github.com/sonic-net/sonic-dns`
- revision: `2023-02-14`
- import: `ietf-inet-types`
- top container: `sonic-dns`

Domain Name System (DNS) resolver configuration YANG module for SONiC OS.[^1]

## ツリー

```
module: sonic-dns
  +--rw sonic-dns
     +--rw DNS_NAMESERVER
     |  +--rw DNS_NAMESERVER_LIST* [ip]
     |     +--rw ip    inet:ip-address
     +--rw DNS_OPTIONS
        +--rw search*     inet:host
        +--rw ndots?      uint8
        +--rw timeout?    uint8
        +--rw attempts?   uint8
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-dns` |  |  |
| `container` | `sonic-dns/DNS_NAMESERVER` |  | DNS nameserver addresses for name resolution. |
| `list` | `sonic-dns/DNS_NAMESERVER/DNS_NAMESERVER_LIST` | `ip` | Ordered list of DNS nameserver IP addresses. |
| `container` | `sonic-dns/DNS_OPTIONS` |  | DNS resolver options; requires at least one nameserver to be configured. |

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ip` | `sonic-dns/DNS_NAMESERVER/DNS_NAMESERVER_LIST/ip` | `inet:ip-address` | yes |  |  | IPv4 or IPv6 address of a DNS nameserver. |
| `search[]` | `sonic-dns/DNS_OPTIONS/search` | `inet:host` |  |  |  | Configure the DNS search suffix list |
| `ndots` | `sonic-dns/DNS_OPTIONS/ndots` | `uint8` |  | 1 | range `0..15` | Sets a threshold for the number of dots which must appear in a name given before an initial absolute query will be made |
| `timeout` | `sonic-dns/DNS_OPTIONS/timeout` | `uint8` |  | 5 | range `1..30` | Sets the amount of time in seconds the resolver will wait for a response from a remote name server before retrying the query via a different name server. |
| `attempts` | `sonic-dns/DNS_OPTIONS/attempts` | `uint8` |  | 2 | range `1..5` | Sets the number of times the resolver will send a query to its name servers before giving up and returning an error to the calling application. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `DNS_NAMESERVER`
- CONFIG_DB: `DNS_OPTIONS`
- CLI: `config dns`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `DNS_NAMESERVER` / `DNS_OPTIONS`
- CLI: `config dns`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dns.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
