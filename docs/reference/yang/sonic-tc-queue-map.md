---
title: sonic-tc-queue-map YANG
description: "sonic-tc-queue-map YANG — TC_TO_QUEUE_MAP yang Module for SONiC OS"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tc-queue-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [TC_TO_QUEUE_MAP]
  cli: []
  yang: []
---

# sonic-tc-queue-map YANG

## 概要

- module: `sonic-tc-queue-map`
- namespace: `http://github.com/sonic-net/sonic-tc-queue-map`
- revision: `2021-04-15`
- import: `sonic-types`
- top container: `sonic-tc-queue-map`

TC_TO_QUEUE_MAP yang Module for SONiC OS[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-tc-queue-map"]
  C1[("CONFIG_DB<br/>TC_TO_QUEUE_MAP")]
  Y --> C1
  D1["QosOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## ツリー

```
module: sonic-tc-queue-map
  +--rw sonic-tc-queue-map
     +--rw TC_TO_QUEUE_MAP
        +--rw TC_TO_QUEUE_MAP_LIST* [name]
           +--rw name               string
           +--rw TC_TO_QUEUE_MAP* [tc]
              +--rw tc        stypes:tc_type
              +--rw qindex?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-tc-queue-map/TC_TO_QUEUE_MAP/TC_TO_QUEUE_MAP_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | Name of the TC to queue map. |
| `tc` | `sonic-tc-queue-map/TC_TO_QUEUE_MAP/TC_TO_QUEUE_MAP_LIST/TC_TO_QUEUE_MAP/tc` | `stypes:tc_type` | yes |  |  | Source traffic class. |
| `qindex` | `sonic-tc-queue-map/TC_TO_QUEUE_MAP/TC_TO_QUEUE_MAP_LIST/TC_TO_QUEUE_MAP/qindex` | `string` |  |  | pattern `[0-9]?` | Target egress queue index (0-9). |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `TC_TO_QUEUE_MAP`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`TC_TO_QUEUE_MAP`](../config-db/tc-to-queue-map.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- TC → output queue マッピング。`TC_TO_QUEUE_MAP|<name>` を qosorch が SAI qos map に反映。

### よくある落とし穴

- key は TC 番号 (0-7) string。範囲外を入れると orchagent が map を skip するためサイレント不適用になる。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'TC_TO_QUEUE_MAP|*'
show qos map tc-queue
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-tc-queue-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`


<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
