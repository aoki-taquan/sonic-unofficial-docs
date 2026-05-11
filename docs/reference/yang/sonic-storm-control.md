---
title: sonic-storm-control YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-storm-control.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [PORT_STORM_CONTROL]
  cli: ["config interface storm-control", "show storm-control"]
  yang: [sonic-port]
---

# sonic-storm-control YANG

## 概要

- module: `sonic-storm-control`
- namespace: `http://github.com/sonic-net/sonic-storm-control`
- revision: `2021-12-13`
- import: `sonic-port`
- top container: `sonic-storm-control`

ポート単位の BUM (Broadcast / Unknown unicast / Multicast) ストーム制御レート上限を保持する[^1]。

## ツリー

```
module: sonic-storm-control
  +--rw sonic-storm-control
     +--rw PORT_STORM_CONTROL
        +--rw PORT_STORM_CONTROL_LIST* [ifname storm_type]
           +--rw ifname        -> /prt:sonic-port/PORT/PORT_LIST/name
           +--rw storm_type    enumeration
           +--rw kbps?         uint64
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `ifname` | `sonic-storm-control/PORT_STORM_CONTROL/PORT_STORM_CONTROL_LIST/ifname` | `leafref` | yes |  | /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name | Physical port on which storm control is applied |
| `storm_type` | `sonic-storm-control/PORT_STORM_CONTROL/PORT_STORM_CONTROL_LIST/storm_type` | `enumeration` | yes |  | broadcast, unknown-unicast, unknown-multicast | Type of BUM traffic to rate-limit |
| `kbps` | `sonic-storm-control/PORT_STORM_CONTROL/PORT_STORM_CONTROL_LIST/kbps` | `uint64` |  |  |  | Rate limit in kilobits per second |

## leafref / 依存

- `sonic-storm-control/PORT_STORM_CONTROL/PORT_STORM_CONTROL_LIST/ifname` → `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `PORT_STORM_CONTROL`
- CLI: `config interface storm-control`, `show storm-control`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PORT_STORM_CONTROL`](../config-db/port-storm-control.md)
- CLI: [`config interface storm-control`](../cli/config-interface.md) / [`show storm-control`](../cli/show-storm-control.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-storm-control.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
