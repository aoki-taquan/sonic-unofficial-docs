---
title: sonic-dscp-fc-map YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [DSCP_TO_FC_MAP]
  cli: ["config cbf"]
  yang: []
---

# sonic-dscp-fc-map YANG

## 概要

- module: `sonic-dscp-fc-map`
- namespace: `http://github.com/sonic-net/sonic-dscp-fc-map`
- revision: `2021-10-29`
- import: なし
- top container: `sonic-dscp-fc-map`

Class-Based Forwarding (CBF) で使う **DSCP → Forwarding Class (FC) マップ** を定義する SONiC モジュール[^1]。

## ツリー

```
module: sonic-dscp-fc-map
  +--rw sonic-dscp-fc-map
     +--rw DSCP_TO_FC_MAP
        +--rw DSCP_TO_FC_MAP_LIST* [name]
           +--rw name              string
           +--rw DSCP_TO_FC_MAP* [dscp]
              +--rw dscp           string  (pattern "6[0-3]|[1-5][0-9]?|[0-9]?")
              +--rw fc?            string  (pattern "[0-7]?")
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-dscp-fc-map` |  |  |
| `container` | `sonic-dscp-fc-map/DSCP_TO_FC_MAP` |  | DSCP→FC マップ群 |
| `list` | `.../DSCP_TO_FC_MAP_LIST` | `name` | 名前付きマップ |
| `list` | `.../DSCP_TO_FC_MAP_LIST/DSCP_TO_FC_MAP` | `dscp` | DSCP 単位のエントリ |

## leaf 一覧

| leaf | 型 | 必須 | 制約 | 説明 |
|------|----|------|------|------|
| `name` | `string` | yes | length `1..32`, pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | マップ名 |
| `dscp` | `string` | yes | pattern `6[0-3]|[1-5][0-9]?|[0-9]?` (0..63) | DSCP 値 |
| `fc` | `string` |  | pattern `[0-7]?` (0..7) | 対象 Forwarding Class |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `DSCP_TO_FC_MAP`
- CLI: `config cbf dscp-fc-map` (sonic-utilities `cbf` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DSCP_TO_FC_MAP`](../config-db/dscp-to-fc-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang>
