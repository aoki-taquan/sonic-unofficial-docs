---
title: sonic-trimming YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-trimming.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SWITCH_TRIMMING]
  cli: ["config switch-trimming"]
  yang: [sonic-buffer-profile, sonic-queue, sonic-dscp-tc-map]
---

# sonic-trimming YANG

## 概要

- module: `sonic-trimming`
- namespace: `http://github.com/sonic-net/sonic-trimming`
- revision: `2024-11-01`
- import: なし
- top container: `sonic-trimming`

パケットトリミング（輻輳テレメトリ用にパケットを縮小して送信）のグローバル設定を保持する YANG モジュール[^1]。

## ツリー

```
module: sonic-trimming
  +--rw sonic-trimming
     +--rw SWITCH_TRIMMING
        +--rw GLOBAL
           +--rw size?          uint32
           +--rw dscp_value?    union(uint8 0..63, "from-tc")
           +--rw tc_value?      uint8
           +--rw queue_index?   union(uint8, "dynamic")
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `size` | `sonic-trimming/SWITCH_TRIMMING/GLOBAL/size` | `uint32` |  |  | bytes | トリミング後のパケットサイズ |
| `dscp_value` | `.../dscp_value` | `union(uint8, string)` |  |  | uint8 0..63 または `from-tc` | トリミング後の DSCP 値。`from-tc` で `tc_value` 経由マッピングを使用 |
| `tc_value` | `.../tc_value` | `uint8` |  |  |  | トリミング後の TC 値 |
| `queue_index` | `.../queue_index` | `union(uint8, string)` |  |  | uint8 または `dynamic` | トリミング後の送信キュー。`dynamic` で `dscp_value` 経由マッピング |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SWITCH_TRIMMING|GLOBAL`
- CLI: `config switch-trimming`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-trimming.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
