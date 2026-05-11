---
title: sonic-scheduler YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-scheduler.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SCHEDULER]
  cli: []
  yang: []
---

# sonic-scheduler YANG

## 概要

- module: `sonic-scheduler`
- namespace: `http://github.com/sonic-net/sonic-scheduler`
- revision: `2021-04-01`
- top container: `sonic-scheduler`

SCHEDULER yang Module for SONiC OS[^1]

## ツリー

```
module: sonic-scheduler
  +--rw sonic-scheduler
     +--rw SCHEDULER
        +--rw SCHEDULER_LIST* [name]
           +--rw name          string
           +--rw type?         enumeration
           +--rw weight?       uint8
           +--rw priority?     uint8
           +--rw meter_type?   enumeration
           +--rw cir?          uint64
           +--rw pir?          uint64
           +--rw cbs?          uint32
           +--rw pbs?          uint32
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name` | `string` | yes |  |  | Scheduler name |
| `type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/type` | `enumeration` |  | WRR | DWRR, WRR, STRICT | Scheduling algorithm type |
| `weight` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/weight` | `uint8` |  | 1 | range 1..100 | Scheduling algorithm weight |
| `priority` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/priority` | `uint8` |  |  | range 0..9 | Scheduler priority |
| `meter_type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/meter_type` | `enumeration` |  | bytes | packets, bytes | Metering unit for shaping rates (packets or bytes). |
| `cir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cir` | `uint64` |  |  |  | Committed information rate for the dual-rate token bucket policer.This value represents the rate at which tokens are added to the primary bucket.nt Units is Bps(Bytes per second) for meter type is ... |
| `pir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pir` | `uint64` |  |  |  | Peak information rate for the dual-rate token bucket policer.This value represents the rate at which tokens are added to the secondary bucket.Unit is Bps(Bytes per second) for meter type bytes else... |
| `cbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cbs` | `uint32` |  |  |  | Committed burst size for the dual-rate token bucket policer.This value represents the depth of the token bucket.Unit is bytes for meter type bytes else packets for meter type is packets |
| `pbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pbs` | `uint32` |  |  |  | Excess burst size for the dual-rate token bucket policer. This value represents the depth of the secondary bucket. Unit is bytes for meter type bytes else packets for meter type is packets |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SCHEDULER`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`SCHEDULER`](../config-db/scheduler.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-scheduler.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

