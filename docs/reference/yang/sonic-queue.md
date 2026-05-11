---
title: sonic-queue YANG
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-queue.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [QUEUE]
  cli: []
  yang: [sonic-port, sonic-scheduler, sonic-wred-profile]
---

# sonic-queue YANG

## 概要

- module: `sonic-queue`
- namespace: `http://github.com/sonic-net/sonic-queue`
- revision: `2021-04-01`
- import: `sonic-extension`, `sonic-port`, `sonic-scheduler`, `sonic-wred-profile`, `sonic-device_metadata`, `sonic-types`
- top container: `sonic-queue`

QUEUE yang Module for SONiC OS[^1]

## ツリー

```
module: sonic-queue
  +--rw sonic-queue
     +--rw QUEUE
        +--rw QUEUE_LIST* [ifname qindex]
        |  +--rw ifname          union
        |  +--rw qindex          string
        |  +--rw scheduler?      -> /sch:sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name
        |  +--rw wred_profile?   -> /wrd:sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/name
        +--rw VOQ_QUEUE_LIST* [hostname asic_name ifname qindex]
           +--rw hostname        stypes:hostname
           +--rw asic_name       stypes:asic_name
           +--rw ifname          string
           +--rw qindex          string
           +--rw scheduler?      -> /sch:sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name
           +--rw wred_profile?   -> /wrd:sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/name
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ifname` | `sonic-queue/QUEUE/QUEUE_LIST/ifname` | `union` | yes |  | union(leafref, string) | Interface name. |
| `qindex` | `sonic-queue/QUEUE/QUEUE_LIST/qindex` | `string` | yes |  |  | Queue index on the interface. |
| `scheduler` | `sonic-queue/QUEUE/QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | Scheduler for queue. |
| `wred_profile` | `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |
| `hostname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/hostname` | `stypes:hostname` | yes |  |  | VOQ chassis hostname owning this port. |
| `asic_name` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/asic_name` | `stypes:asic_name` | yes |  |  | ASIC instance name within the VOQ chassis. |
| `ifname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/ifname` | `string` | yes |  | length 1..128 | Interface name. |
| `qindex` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/qindex` | `string` | yes |  |  | Queue index on the interface. |
| `scheduler` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | Scheduler for queue. |
| `wred_profile` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |

## leafref / 依存

- `sonic-queue/QUEUE/QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `QUEUE`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`QUEUE`](../config-db/queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-queue.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

