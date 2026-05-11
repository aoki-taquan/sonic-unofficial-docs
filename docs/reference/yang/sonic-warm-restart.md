---
title: sonic-warm-restart YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-warm-restart.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [WARM_RESTART]
  cli: ["config warm_restart"]
  yang: []
---

# sonic-warm-restart YANG

## 概要

- module: `sonic-warm-restart`
- namespace: `http://github.com/sonic-net/sonic-warm-restart`
- revision: `2021-05-24`
- import: なし
- top container: `sonic-warm-restart`

Warm restart configuration per module for hitless software upgrades[^1]。BGP EOIU 信号と各 syncd 系のタイマーをモジュール別に保持する。

## ツリー

```
module: sonic-warm-restart
  +--rw sonic-warm-restart
     +--rw WARM_RESTART
        +--rw WARM_RESTART_LIST* [module]
           +--rw module              module-name
           +--rw bgp_eoiu?           boolean
           +--rw bgp_timer?          uint16
           +--rw teamsyncd_timer?    uint16
           +--rw neighsyncd_timer?   uint16
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `module` | `sonic-warm-restart/WARM_RESTART/WARM_RESTART_LIST/module` | `module-name` | yes |  | system, bgp, teamd, swss, syncd, natsyncd, etc. | Name of the module |
| `bgp_eoiu` | `sonic-warm-restart/WARM_RESTART/WARM_RESTART_LIST/bgp_eoiu` | `boolean` |  | false |  | BGP End-of-Initial Update (EOIU) signal enable/disable |
| `bgp_timer` | `sonic-warm-restart/WARM_RESTART/WARM_RESTART_LIST/bgp_timer` | `uint16` |  |  | range 1..3600 | BGP graceful restart timer (seconds) |
| `teamsyncd_timer` | `sonic-warm-restart/WARM_RESTART/WARM_RESTART_LIST/teamsyncd_timer` | `uint16` |  |  | range 1..3600 | teamsyncd warm restart timer (seconds) |
| `neighsyncd_timer` | `sonic-warm-restart/WARM_RESTART/WARM_RESTART_LIST/neighsyncd_timer` | `uint16` |  |  | range 1..9999 | neighsyncd warm restart timer (seconds) |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `WARM_RESTART`
- CLI: `config warm_restart`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-warm-restart.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
