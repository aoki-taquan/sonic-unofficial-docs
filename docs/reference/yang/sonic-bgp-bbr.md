---
title: sonic-bgp-bbr YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-bbr.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_BBR]
  cli: ["config bgp bbr"]
  yang: [sonic-bgp-global, sonic-bgp-aggregate-address]
---

# sonic-bgp-bbr YANG

## 概要

- module: `sonic-bgp-bbr`
- namespace: `http://github.com/sonic-net/sonic-bgp-bbr`
- revision: `2023-12-25`
- import: `sonic-types`
- top container: `sonic-bgp-bbr`

SONiC の BGP Border Router (BBR) を有効化/無効化する小さなグローバル設定モジュール[^1]。`all` 単一インスタンスのコンテナ配下に `status` リーフを持つ。

## ツリー

```
module: sonic-bgp-bbr
  +--rw sonic-bgp-bbr
     +--rw BGP_BBR
        +--rw all
           +--rw status?   stypes:admin_mode
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `status` | `sonic-bgp-bbr/BGP_BBR/all/status` | `stypes:admin_mode` |  | `enabled` | enabled / disabled | デバイス上で BGP BBR 機能を有効/無効にする |

## leafref / 依存

- なし

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BGP_BBR|all`
- CLI: `config bgp bbr`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `BGP_BBR`
- CLI: `config bgp bbr`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-bbr.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
