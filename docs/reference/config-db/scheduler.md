---
title: SCHEDULER テーブル
description: "SCHEDULER テーブル — キュー / ポートに適用するスケジューラ（DWRR / WRR / STRICT）と dual-rate token bucket policer (CIR / PIR / CBS / PBS) のプロファイルを保持する。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-scheduler.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - SCHEDULER
    - QUEUE
    - PORT_QOS_MAP
  cli: []
  yang:
    - sonic-scheduler
---

# SCHEDULER テーブル

## 概要

キュー / ポートに適用するスケジューラ（DWRR / WRR / STRICT）と dual-rate token bucket policer (CIR / PIR / CBS / PBS) のプロファイルを保持する[^1]。`qosorch` が SAI scheduler を生成、`QUEUE.scheduler` から leafref で参照される。

## key 構造

```
SCHEDULER|<name>
```

## フィールド一覧

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|----|------|-----------|------|
| `name` (key) | string | ✅ | - | スケジューラ名 |
| `type` | enum `DWRR`/`WRR`/`STRICT` | - | `WRR` | スケジューリングアルゴリズム |
| `weight` | uint8 (1..100) | - | `1` | 重み（DWRR/WRR で使用） |
| `priority` | uint8 (0..9) | - | - | 優先度 |
| `meter_type` | enum `packets`/`bytes` | - | `bytes` | meter 単位 |
| `cir` | uint64 | - | - | committed information rate（Bps or Pps） |
| `pir` | uint64 | - | - | peak information rate。`cir > 0` 必須、`pir >= cir` |
| `cbs` | uint32 | - | - | committed burst size。`cir > 0` 必須 |
| `pbs` | uint32 | - | - | excess/peak burst size。`pir > 0` 必須、`pbs >= cbs` |

## 制約 (must)

- `pir` 単独設定禁止（`cir` 必須・`cir > 0`）
- `pir >= cir`
- `cbs` 単独設定禁止（`cir` 必須）
- `pbs` 単独設定禁止（`pir` 必須）、`pbs >= cbs`

## 購読者

- `qosorch`: SAI scheduler を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `QUEUE`、`PORT_QOS_MAP`
- 関連 CLI: なし
- 関連 YANG: `sonic-scheduler`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-scheduler`](../yang/sonic-scheduler.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-scheduler.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-scheduler.yang>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
