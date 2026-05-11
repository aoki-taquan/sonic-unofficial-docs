---
title: sonic-bgp-monitor YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-monitor.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_MONITORS]
  cli: []
  yang: [sonic-bgp-common]
---

# sonic-bgp-monitor YANG

## 概要

- module: `sonic-bgp-monitor`
- namespace: `http://github.com/sonic-net/sonic-bgp-monitor`
- revision: `2022-01-11`
- import: `ietf-inet-types`, `sonic-bgp-common`
- top container: `sonic-bgp-monitor`

`bgpcfgd` が扱う BGP monitor peer 設定。 BMP / monitoring collector 用の擬似ピアを定義する[^1]。

## ツリー

```
module: sonic-bgp-monitor
  +--rw sonic-bgp-monitor
     +--rw BGP_MONITORS
        +--rw BGP_MONITORS_LIST* [addr]
           +--rw addr            inet:ip-address
           +--rw asn?            uint32
           +--rw holdtime?       uint16
           +--rw keepalive?      uint16
           +--rw local_addr?     inet:ip-address
           +--rw name?           string
           +--rw nhopself?       uint8
           +--rw rrclient?       uint8
           +--rw admin_status?   stypes:admin_status
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `addr` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/addr` | `inet:ip-address` | yes |  |  | BGP monitor peer address |
| `asn` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/asn` | `uint32` |  |  | range 0..4294967295 | Peer AS number |
| `holdtime` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/holdtime` | `uint16` |  |  |  | BGP hold time in seconds |
| `keepalive` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/keepalive` | `uint16` |  |  |  | BGP keepalive interval in seconds |
| `local_addr` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/local_addr` | `inet:ip-address` |  |  |  | Local source address for the BGP session |
| `name` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/name` | `string` |  |  |  | Human-readable peer description |
| `nhopself` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/nhopself` | `uint8` |  |  | range 0..1 | Set nexthop to self for routes advertised to this peer |
| `rrclient` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/rrclient` | `uint8` |  |  | range 0..1 | Configure as route reflector client |
| `admin_status` | `sonic-bgp-monitor/BGP_MONITORS/BGP_MONITORS_LIST/admin_status` | `stypes:admin_status` |  |  | up, down | Administrative status of the BGP monitor peer |

## leafref / 依存

- なし（型・grouping は `sonic-bgp-common` から流用）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BGP_MONITORS`
- CLI: なし（`bgpcfgd` が config_db.json から読み取り FRR 設定に反映）

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-monitor.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
