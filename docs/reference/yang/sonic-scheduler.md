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

### 関連 HLD

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
| `type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/type` | `enumeration` |  | [WRR](../../reference/glossary.md#term-wrr) | [DWRR](../../reference/glossary.md#term-dwrr), [WRR](../../reference/glossary.md#term-wrr), STRICT | Scheduling algorithm type |
| `weight` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/weight` | `uint8` |  | 1 | range 1..100 | Scheduling algorithm weight |
| `priority` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/priority` | `uint8` |  |  | range 0..9 | [Scheduler](../../reference/glossary.md#term-scheduler) priority |
| `meter_type` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/meter_type` | `enumeration` |  | bytes | packets, bytes | Metering unit for shaping rates (packets or bytes). |
| `cir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cir` | `uint64` |  |  |  | Committed information rate for the dual-rate token bucket policer. Tokens are added to the primary bucket at this rate. 単位は `meter_type=bytes` のとき Bps (bytes per second)、`packets` のとき pps (packets per second)。 |
| `pir` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pir` | `uint64` |  |  |  | Peak information rate for the dual-rate token bucket policer. Tokens are added to the secondary bucket at this rate. 単位は `meter_type=bytes` のとき Bps、`packets` のとき pps。`must` により `cir > 0` かつ `pir >= cir` が要求される[^1]。 |
| `cbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/cbs` | `uint32` |  |  |  | Committed burst size (primary token bucket の深さ)。単位は `meter_type=bytes` のとき bytes、`packets` のとき packets。`must` により `cir > 0` が要求される[^1]。 |
| `pbs` | `sonic-scheduler/SCHEDULER/SCHEDULER_LIST/pbs` | `uint32` |  |  |  | Excess (peak) burst size (secondary token bucket の深さ)。単位は `meter_type=bytes` のとき bytes、`packets` のとき packets。`must` により `pir > 0` かつ `pbs >= cbs` (cbs 設定時) が要求される[^1]。 |

## leafref / must 制約

`leafref` は無し（このモジュール内で直接 leafref を持つ leaf はない）。一方、`SCHEDULER_LIST` 配下の shaping パラメータには [YANG](../../reference/glossary.md#term-yang) `must` 式によるクロスフィールド検証が定義されている[^1]:

| 対象 leaf | `must` 式 (要約) | エラー文言 |
|-----------|------------------|------------|
| `pir` | `cir` が設定済みで `cir > 0` | `pir can't be configured without cir.` |
| `pir` | `pir >= cir` | `pir must be greater than or equal to cir` |
| `cbs` | `cir` が設定済みで `cir > 0` | `cbs can't be configured without cir.` |
| `pbs` | `pir` が設定済みで `pir > 0` | `pbs can't be configured without pir.` |
| `pbs` | `cbs` 未設定 もしくは `pbs >= cbs` | `pbs must be greater than or equal to cbs` |

これらの制約は [CONFIG_DB](../../reference/glossary.md#term-config_db) への書き込み時に `sonic-yang-models` で検証される。

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

<!-- glossary-links-injected: 9dae6d74c08e -->
