---
title: sonic-pfc-priority-queue-map YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pfc-priority-queue-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [MAP_PFC_PRIORITY_TO_QUEUE]
  cli: []
  yang: [sonic-port-qos-map, sonic-queue]
---

# sonic-pfc-priority-queue-map YANG

## 概要

- module: `sonic-pfc-priority-queue-map`
- namespace: `http://github.com/sonic-net/sonic-pfc-priority-queue-map`
- revision: `2021-04-15`
- import: なし
- top container: `sonic-pfc-priority-queue-map`

PFC_PRIORITY_TO_QUEUE_MAP yang Module for SONiC OS. PFC 優先度 (0-7) を egress queue index にマッピングする。[^1]

## ツリー

```
module: sonic-pfc-priority-queue-map
  +--rw sonic-pfc-priority-queue-map
     +--rw MAP_PFC_PRIORITY_TO_QUEUE
        +--rw MAP_PFC_PRIORITY_TO_QUEUE_LIST* [name]
           +--rw name    string
           +--rw MAP_PFC_PRIORITY_TO_QUEUE* [pfc_priority]
              +--rw pfc_priority    string
              +--rw qindex?         string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-pfc-priority-queue-map/MAP_PFC_PRIORITY_TO_QUEUE/MAP_PFC_PRIORITY_TO_QUEUE_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32 | Name of the PFC priority to queue map. |
| `pfc_priority` | `.../MAP_PFC_PRIORITY_TO_QUEUE/pfc_priority` | `string` | yes |  | pattern `[0-7]?` | PFC priority value (0-7). |
| `qindex` | `.../MAP_PFC_PRIORITY_TO_QUEUE/qindex` | `string` |  |  | pattern `[0-7]?` | Target egress queue index (0-7). |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `MAP_PFC_PRIORITY_TO_QUEUE|<name>` でマップ本体、`PORT_QOS_MAP|<port>/pfc_to_queue_map` から参照
- CLI: マップ名は `config qos reload` / minigraph 経由で投入

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`MAP_PFC_PRIORITY_TO_QUEUE`](../config-db/map-pfc-priority-to-queue.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-pfc-priority-queue-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
