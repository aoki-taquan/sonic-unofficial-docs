---
title: sonic-versions YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-versions.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [VERSIONS]
  cli: []
  yang: []
---

# sonic-versions YANG

## 概要

- module: `sonic-versions`
- namespace: `http://github.com/sonic-net/sonic-versions`
- revision: `2020-04-10`
- import: なし
- top container: `sonic-versions`

VERSIONS YANG Module for SONiC OS. CONFIG_DB のスキーマバージョンを記録し、`db_migrator.py` がマイグレーションの判定に使う。[^1]

## ツリー

```
module: sonic-versions
  +--rw sonic-versions
     +--rw VERSIONS
        +--rw DATABASE
           +--rw VERSION?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `VERSION` | `sonic-versions/VERSIONS/DATABASE/VERSION` | `string` |  |  | length 1..255; pattern `version_(...)` (例: `version_4_0_5`) | Database schema version string. |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `VERSIONS|DATABASE` キーで `VERSION` フィールドを保持

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-versions.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
