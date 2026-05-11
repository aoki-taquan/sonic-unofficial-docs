---
title: sonic-pfc-priority-priority-group-map YANG
description: "sonic-pfc-priority-priority-group-map YANG — PFC_PRIORITY_TO_PRIORITY_GROUP_MAP yang Module for SONiC OS. PFC 優先度 (0-7) を ingress priority group にマップしロスレス転送を制御…"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP]
  cli: []
  yang: [sonic-port-qos-map, sonic-buffer-pg]
---

# sonic-pfc-priority-priority-group-map YANG

## 概要

- module: `sonic-pfc-priority-priority-group-map`
- namespace: `http://github.com/sonic-net/sonic-pfc-priority-priority-group-map`
- revision: `2021-04-15`
- import: なし
- top container: `sonic-pfc-priority-priority-group-map`

PFC_PRIORITY_TO_PRIORITY_GROUP_MAP yang Module for SONiC OS. PFC 優先度 (0-7) を ingress priority group にマップしロスレス転送を制御する。[^1]

## ツリー

```
module: sonic-pfc-priority-priority-group-map
  +--rw sonic-pfc-priority-priority-group-map
     +--rw PFC_PRIORITY_TO_PRIORITY_GROUP_MAP
        +--rw PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_LIST* [name]
           +--rw name    string
           +--rw PFC_PRIORITY_TO_PRIORITY_GROUP_MAP* [pfc_priority]
              +--rw pfc_priority    string
              +--rw pg?             string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-pfc-priority-priority-group-map/PFC_PRIORITY_TO_PRIORITY_GROUP_MAP/PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_LIST/name` | `string` | yes |  | pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`, length 1..32 | Name of the PFC priority to priority group map. |
| `pfc_priority` | `.../PFC_PRIORITY_TO_PRIORITY_GROUP_MAP/pfc_priority` | `string` | yes |  | pattern `[0-7]?` | PFC priority value (0-7). |
| `pg` | `.../PFC_PRIORITY_TO_PRIORITY_GROUP_MAP/pg` | `string` |  |  | pattern `[0-7]?` | Target ingress priority group (0-7). |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP|<name>`、`PORT_QOS_MAP|<port>/pfc_to_pg_map` から参照

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`](../config-db/pfc-priority-to-priority-group-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-pfc-priority-priority-group-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
