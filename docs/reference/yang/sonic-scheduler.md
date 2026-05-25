---
title: sonic-scheduler YANG
description: "sonic-scheduler YANG — SCHEDULER yang Module for SONiC OS"
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
  _no_related_cli: true
  _no_related_yang: true
---

# sonic-scheduler YANG

## 概要

- module: `sonic-scheduler`
- namespace: `http://github.com/sonic-net/sonic-scheduler`
- revision: `2021-04-01`
- top container: `sonic-scheduler`

SCHEDULER yang Module for [SONiC](../../reference/glossary.md#term-sonic) OS[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-scheduler"]
  C1[("CONFIG_DB<br/>SCHEDULER")]
  Y --> C1
  D1["QosOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`SCHEDULER`](../config-db/scheduler.md)

### 対応 CONFIG_DB (追加)

- [POLICER テーブル](../../reference/config-db/policer.md)

<!-- /yang-xref -->

## ツリー

```text
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
| `name` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/name` | `string` | yes |  |  | [Scheduler](../../reference/glossary.md#term-scheduler) name |
| `type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/type` | `enumeration` |  | WRR | [DWRR](../../reference/glossary.md#term-dwrr), WRR, STRICT | Scheduling algorithm type |
| `weight` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/weight` | `uint8` |  | 1 | range 1..100 | Scheduling algorithm weight |
| `priority` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/priority` | `uint8` |  |  | range 0..9 | [Scheduler](../../reference/glossary.md#term-scheduler) priority |
| `meter_type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/meter_type` | `enumeration` |  | bytes | packets, bytes | Metering unit for shaping rates (packets or bytes). |
| `cir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cir` | `uint64` |  |  |  | Committed information rate for the dual-rate token bucket policer. This value represents the rate at which tokens are added to the primary bucket. Unit is Bps(Bytes per second) for meter type bytes else packets. |
| `pir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pir` | `uint64` |  |  |  | Peak information rate for the dual-rate token bucket policer.This value represents the rate at which tokens are added to the secondary bucket.Unit is Bps(Bytes per second) for meter type bytes else... |
| `cbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cbs` | `uint32` |  |  |  | Committed burst size for the dual-rate token bucket policer.This value represents the depth of the token bucket.Unit is bytes for meter type bytes else packets for meter type is packets |
| `pbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pbs` | `uint32` |  |  |  | Excess burst size for the dual-rate token bucket policer. This value represents the depth of the secondary bucket. Unit is bytes for meter type bytes else packets for meter type is packets |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `SCHEDULER`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
- [`sonic-buffer-profile`](sonic-buffer-profile.md)
- [`sonic-buffer-queue`](sonic-buffer-queue.md)
- [`sonic-dot1p-tc-map`](sonic-dot1p-tc-map.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`SCHEDULER`](../config-db/scheduler.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-scheduler.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
