---
title: sonic-fips YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-fips.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [FIPS]
  cli: ["config fips"]
  yang: []
---

# sonic-fips YANG

## 概要

- module: `sonic-fips`
- namespace: `http://github.com/sonic-net/sonic-fips`
- revision: `2023-06-20`
- import: `sonic-types`
- top container: `sonic-fips`

Federal Information Processing Standards (FIPS) 140-3 compliance YANG module for SONiC OS.[^1]

## ツリー

```
module: sonic-fips
  +--rw sonic-fips
     +--rw FIPS
        +--rw global
           +--rw enable?    stypes:boolean_type
           +--rw enforce?   stypes:boolean_type
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `enable` | `sonic-fips/FIPS/global/enable` | `stypes:boolean_type` |  | `false` |  | Enable or disable FIPS-validated cryptographic modules. |
| `enforce` | `sonic-fips/FIPS/global/enforce` | `stypes:boolean_type` |  | `false` |  | When true, enforce FIPS compliance and reject non-compliant operations. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `FIPS|global`
- CLI: `config fips`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-fips.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
