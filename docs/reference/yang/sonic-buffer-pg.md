---
title: sonic-buffer-pg YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-buffer-pg.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BUFFER_PG]
  cli: []
  yang: [sonic-port, sonic-buffer-profile]
---

# sonic-buffer-pg YANG

## 概要

- module: `sonic-buffer-pg`
- namespace: `http://github.com/sonic-net/sonic-buffer-pg`
- revision: `2021-07-01`
- import: `sonic-port`, `sonic-buffer-profile`
- top container: `sonic-buffer-pg`

Ingress buffer priority group configuration for SONiC ports.[^1]

## ツリー

```
module: sonic-buffer-pg
  +--rw sonic-buffer-pg
     +--rw BUFFER_PG
        +--rw BUFFER_PG_LIST* [port pg_num]
           +--rw port       -> /prt:sonic-port/PORT/PORT_LIST/name
           +--rw pg_num     string
           +--rw profile?   union
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `port` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/port` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Port on which the buffer priority group is configured. |
| `pg_num` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/pg_num` | `string` | yes |  | pattern `[0-7]((-)[0-7])?` | Priority Group number |
| `profile` | `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/profile` | `union` |  | 0 | union(leafref, string) | Buffer Profile associated with Priority Group number for a port |

## leafref / 依存

- `sonic-buffer-pg/BUFFER_PG/BUFFER_PG_LIST/port` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BUFFER_PG`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-buffer-pg.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

