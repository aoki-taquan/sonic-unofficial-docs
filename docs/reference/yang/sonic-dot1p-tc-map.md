---
title: sonic-dot1p-tc-map YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [DOT1P_TO_TC_MAP]
  cli: ["config qos"]
  yang: [sonic-types, sonic-port-qos-map]
---

# sonic-dot1p-tc-map YANG

## 概要

- module: `sonic-dot1p-tc-map`
- namespace: `http://github.com/sonic-net/sonic-dot1p-tc-map`
- revision: `2021-04-15`
- import: `sonic-types`
- top container: `sonic-dot1p-tc-map`

802.1p (PCP) ビットからトラフィッククラス (TC) へのマップを名前付きで保持する。ingress 側で `PORT_QOS_MAP` から参照される[^1]。

## ツリー

```
module: sonic-dot1p-tc-map
  +--rw sonic-dot1p-tc-map
     +--rw DOT1P_TO_TC_MAP
        +--rw DOT1P_TO_TC_MAP_LIST* [name]
           +--rw name               string
           +--rw DOT1P_TO_TC_MAP* [dot1p]
              +--rw dot1p    string
              +--rw tc?      stypes:tc_type
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-dot1p-tc-map/DOT1P_TO_TC_MAP/DOT1P_TO_TC_MAP_LIST/name` | `string` | yes |  |  | Map name |
| `dot1p` | `sonic-dot1p-tc-map/DOT1P_TO_TC_MAP/DOT1P_TO_TC_MAP_LIST/DOT1P_TO_TC_MAP/dot1p` | `string` | yes |  | "0".."7" | 802.1p priority value |
| `tc` | `sonic-dot1p-tc-map/DOT1P_TO_TC_MAP/DOT1P_TO_TC_MAP_LIST/DOT1P_TO_TC_MAP/tc` | `stypes:tc_type` |  |  | range 0..7 | Traffic class |

## leafref / 依存

- なし（`PORT_QOS_MAP.dot1p_to_tc_map` から leafref で参照される）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `DOT1P_TO_TC_MAP`
- CLI: `config qos`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DOT1P_TO_TC_MAP`](../config-db/dot1p-to-tc-map.md)
- CLI: [`config qos`](../cli/config-qos.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
