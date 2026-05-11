---
title: sonic-wred-profile YANG
description: "sonic-wred-profile YANG — Weighted Random Early Detection (WRED) プロファイルを名前付きで保持する。色 (green/yellow/red) 毎の min/max 閾値、ドロップ確率、 ECN 有効化、 WRED 有効化を保持する。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-wred-profile.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [WRED_PROFILE]
  cli: ["config qos", "show qos"]
  yang: [sonic-queue, sonic-port-qos-map]
---

# sonic-wred-profile YANG

## 概要

- module: `sonic-wred-profile`
- namespace: `http://github.com/sonic-net/sonic-wred-profile`
- revision: `2021-04-01`
- import: なし
- top container: `sonic-wred-profile`

Weighted Random Early Detection (WRED) プロファイルを名前付きで保持する。色 (green/yellow/red) 毎の min/max 閾値、ドロップ確率、 ECN 有効化、 WRED 有効化を保持する[^1]。

## ツリー

```
module: sonic-wred-profile
  +--rw sonic-wred-profile
     +--rw WRED_PROFILE
        +--rw WRED_PROFILE_LIST* [name]
           +--rw name                       string
           +--rw yellow_min_threshold?      uint64
           +--rw green_min_threshold?       uint64
           +--rw red_min_threshold?         uint64
           +--rw yellow_max_threshold?      uint64
           +--rw green_max_threshold?       uint64
           +--rw red_max_threshold?         uint64
           +--rw ecn?                       enumeration
           +--rw wred_green_enable?         boolean
           +--rw wred_yellow_enable?        boolean
           +--rw wred_red_enable?           boolean
           +--rw yellow_drop_probability?   uint64
           +--rw green_drop_probability?    uint64
           +--rw red_drop_probability?      uint64
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/name` | `string` | yes |  |  | WRED profile name |
| `yellow_min_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/yellow_min_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED begins dropping yellow packets |
| `green_min_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/green_min_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED begins dropping green packets |
| `red_min_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/red_min_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED begins dropping red packets |
| `yellow_max_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/yellow_max_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED drops all yellow packets |
| `green_max_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/green_max_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED drops all green packets |
| `red_max_threshold` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/red_max_threshold` | `uint64` |  |  |  | Queue depth (bytes) at which WRED drops all red packets |
| `ecn` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/ecn` | `enumeration` |  |  | ecn_none, ecn_green, ecn_yellow, ecn_red, ecn_green_yellow, ecn_green_red, ecn_yellow_red, ecn_all | ECN marking mode |
| `wred_green_enable` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/wred_green_enable` | `boolean` |  |  |  | Enable WRED for green traffic |
| `wred_yellow_enable` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/wred_yellow_enable` | `boolean` |  |  |  | Enable WRED for yellow traffic |
| `wred_red_enable` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/wred_red_enable` | `boolean` |  |  |  | Enable WRED for red traffic |
| `yellow_drop_probability` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/yellow_drop_probability` | `uint64` |  |  | range 0..100 | Max drop probability between min/max thresholds (yellow) |
| `green_drop_probability` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/green_drop_probability` | `uint64` |  |  | range 0..100 | Max drop probability between min/max thresholds (green) |
| `red_drop_probability` | `sonic-wred-profile/WRED_PROFILE/WRED_PROFILE_LIST/red_drop_probability` | `uint64` |  |  | range 0..100 | Max drop probability between min/max thresholds (red) |

## leafref / 依存

- なし（`WRED_PROFILE` の名前は `QUEUE` テーブル側の `wred_profile` から leafref で参照される）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `WRED_PROFILE`
- CLI: `config qos`, `show qos`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`WRED_PROFILE`](../config-db/wred-profile.md)
- CLI: [`config qos`](../cli/config-qos.md) / `show qos`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-wred-profile.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
