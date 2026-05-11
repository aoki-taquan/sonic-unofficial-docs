---
title: sonic-breakout_cfg YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BREAKOUT_CFG]
  cli: ["config interface breakout"]
  yang: []
---

# sonic-breakout_cfg YANG

## 概要

- module: `sonic-breakout_cfg`
- namespace: `http://github.com/sonic-net/sonic-breakout_cfg`
- revision: `2020-04-10`
- import: なし
- top container: `sonic-breakout_cfg`

BREAKOUT_CFG YANG Module for SONiC OS。動的ポート分割 (port breakout) 設定を親ポート単位で保持する[^1]。

## ツリー

```
module: sonic-breakout_cfg
  +--rw sonic-breakout_cfg
     +--rw BREAKOUT_CFG
        +--rw BREAKOUT_CFG_LIST* [port]
           +--rw port           string
           +--rw brkout_mode?   string
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `port` | `sonic-breakout_cfg/BREAKOUT_CFG/BREAKOUT_CFG_LIST/port` | `string` | yes |  |  | Parent port name for breakout configuration |
| `brkout_mode` | `sonic-breakout_cfg/BREAKOUT_CFG/BREAKOUT_CFG_LIST/brkout_mode` | `string` |  |  | platform.json で検証 (例: `1x100G`, `4x25G`, `2x50G`) | Breakout mode for the port; validated against `platform.json` |

## leafref / 依存

- なし（`port` キーは `platform.json` 側で検証）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BREAKOUT_CFG`
- CLI: `config interface breakout`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BREAKOUT_CFG`](../config-db/breakout-cfg.md)
- CLI: `config interface breakout`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
