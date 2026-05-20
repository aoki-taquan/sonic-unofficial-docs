---
title: sonic-queue YANG
description: "sonic-queue YANG — QUEUE yang Module for SONiC OS"
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

QUEUE yang Module for [SONiC](../../reference/glossary.md#term-sonic) OS[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-queue"]
  C1[("CONFIG_DB<br/>QUEUE")]
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

- [`QUEUE`](../config-db/queue.md)

<!-- /yang-xref -->

## ツリー

```text
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
| `scheduler` | `sonic-queue/QUEUE/QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | [Scheduler](../../reference/glossary.md#term-scheduler) for queue. |
| `wred_profile` | `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |
| `hostname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/hostname` | `stypes:hostname` | yes |  |  | [VOQ](../../reference/glossary.md#term-voq) chassis hostname owning this port. |
| `asic_name` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/asic_name` | `stypes:asic_name` | yes |  |  | [ASIC](../../reference/glossary.md#term-asic) instance name within the [VOQ](../../reference/glossary.md#term-voq) chassis. |
| `ifname` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/ifname` | `string` | yes |  | length 1..128 | Interface name. |
| `qindex` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/qindex` | `string` | yes |  |  | Queue index on the interface. |
| `scheduler` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` | `leafref` |  |  | /sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name | [Scheduler](../../reference/glossary.md#term-scheduler) for queue. |
| `wred_profile` | `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` | `leafref` |  |  | /wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name | Wred profile for queue. |

## leafref / 依存

- `sonic-queue/QUEUE/QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/scheduler` → `/sch:sonic-scheduler/sch:SCHEDULER/sch:SCHEDULER_LIST/sch:name`
- `sonic-queue/QUEUE/VOQ_QUEUE_LIST/wred_profile` → `/wrd:sonic-wred-profile/wrd:WRED_PROFILE/wrd:WRED_PROFILE_LIST/wrd:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `QUEUE`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-port`](sonic-port.md)
- [`sonic-scheduler`](sonic-scheduler.md)
- [`sonic-wred-profile`](sonic-wred-profile.md)
- [`sonic-buffer-pg`](sonic-buffer-pg.md)
- [`sonic-buffer-pool`](sonic-buffer-pool.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`QUEUE`](../config-db/queue.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- queue ごとの scheduler / wred 紐付け。`QUEUE|<port>|<index>` を qosorch が処理。

### よくある落とし穴

- `scheduler` / `wred_profile` leafref を持つため、SCHEDULER / WRED_PROFILE を先に作る必要がある。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'QUEUE|*'
show queue counters
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-queue.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
