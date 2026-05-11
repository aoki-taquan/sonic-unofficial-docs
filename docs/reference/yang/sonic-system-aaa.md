---
title: sonic-system-aaa YANG
description: "sonic-system-aaa YANG — Authentication, Authorization, and Accounting (AAA) YANG module for SONiC OS."
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-system-aaa.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [AAA, TACPLUS, RADIUS]
  cli: ["config aaa"]
  yang: []
---

# sonic-system-aaa YANG

## 概要

- module: `sonic-system-aaa`
- namespace: `http://github.com/sonic-net/sonic-system-aaa`
- revision: `2021-10-12`
- import: `sonic-types`, `sonic-system-tacacs`
- top container: `sonic-system-aaa`

Authentication, Authorization, and Accounting (AAA) YANG module for SONiC OS.[^1]

## ツリー

```
module: sonic-system-aaa
  +--rw sonic-system-aaa
     +--rw AAA
        +--rw AAA_LIST* [type]
           +--rw type           enumeration
           +--rw login?         string
           +--rw failthrough?   stypes:boolean_type
           +--rw fallback?      stypes:boolean_type
           +--rw debug?         stypes:boolean_type
           +--rw trace?         stypes:boolean_type
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `type` | `sonic-system-aaa/AAA/AAA_LIST/type` | `enumeration` | yes |  | authentication, authorization, accounting | AAA function type: authentication, authorization, or accounting. |
| `login` | `sonic-system-aaa/AAA/AAA_LIST/login` | `string` |  | local | pattern `((ldap|tacacs\+|local|radius|default),)*(ldap|tacacs\+|lo...` | Ordered list of authentication methods to attempt (radius, tacacs+, ldap, local, or default). |
| `failthrough` | `sonic-system-aaa/AAA/AAA_LIST/failthrough` | `stypes:boolean_type` |  | False |  | When true, authentication continues to the next method in the list upon failure. |
| `fallback` | `sonic-system-aaa/AAA/AAA_LIST/fallback` | `stypes:boolean_type` |  | False |  | When true, falls back to local authentication if all remote methods fail. |
| `debug` | `sonic-system-aaa/AAA/AAA_LIST/debug` | `stypes:boolean_type` |  | False |  | Enable or disable verbose AAA debug logging. |
| `trace` | `sonic-system-aaa/AAA/AAA_LIST/trace` | `stypes:boolean_type` |  | False |  | Enable or disable AAA protocol packet tracing. |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `AAA`
- CONFIG_DB: `TACPLUS`
- CONFIG_DB: `RADIUS`
- CLI: `config aaa`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`AAA`](../config-db/aaa.md) / `TACPLUS` / [`RADIUS`](../config-db/radius.md)
- CLI: [`config aaa`](../cli/config-aaa.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-system-aaa.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

