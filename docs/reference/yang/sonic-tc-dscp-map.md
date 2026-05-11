---
title: sonic-tc-dscp-map YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [TC_TO_DSCP_MAP]
  cli: ["config qos"]
  yang: [sonic-types]
---

# sonic-tc-dscp-map YANG

## 概要

- module: `sonic-tc-dscp-map`
- namespace: `http://github.com/sonic-net/sonic-tc-dscp-map`
- revision: `2025-01-10`
- import: `sonic-types`
- top container: `sonic-tc-dscp-map`

egress 側で **Traffic Class (TC) を DSCP に remark** するマップを定義する SONiC モジュール[^1]。

## ツリー

```
module: sonic-tc-dscp-map
  +--rw sonic-tc-dscp-map
     +--rw TC_TO_DSCP_MAP
        +--rw TC_TO_DSCP_MAP_LIST* [name]
           +--rw name             string
           +--rw TC_TO_DSCP_MAP* [tc]
              +--rw tc             stypes:tc_type
              +--rw dscp?          string  (pattern "6[0-3]|[1-5][0-9]?|[0-9]?")
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-tc-dscp-map` |  |  |
| `container` | `sonic-tc-dscp-map/TC_TO_DSCP_MAP` |  | TC→DSCP マップ群 |
| `list` | `.../TC_TO_DSCP_MAP_LIST` | `name` | 名前付きマップ |
| `list` | `.../TC_TO_DSCP_MAP_LIST/TC_TO_DSCP_MAP` | `tc` | TC 単位のエントリ |

## leaf 一覧

| leaf | 型 | 必須 | 制約 | 説明 |
|------|----|------|------|------|
| `name` | `string` | yes | length `1..32`, pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | マップ名 |
| `tc` | `stypes:tc_type` | yes |  | ソース TC |
| `dscp` | `string` |  | pattern `6[0-3]|[1-5][0-9]?|[0-9]?` (0..63) | egress で書き換える DSCP 値 |

## leafref / 依存

- `tc` 型 `stypes:tc_type` は `sonic-types` で定義された TC 値の typedef。

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `TC_TO_DSCP_MAP`
- CLI: `config qos remap` / `config qos clear` 系 (sonic-utilities `qos` グループ)

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`TC_TO_DSCP_MAP`](../config-db/tc-to-dscp-map.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-tc-dscp-map.yang>
