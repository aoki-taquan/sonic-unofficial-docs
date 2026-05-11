---
title: sonic-sflow YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-sflow.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [SFLOW, SFLOW_COLLECTOR, SFLOW_SESSION]
  cli: ["config sflow", "show sflow"]
  yang: [sonic-port, sonic-portchannel, sonic-vlan, sonic-mgmt_port, sonic-mgmt_vrf]
---

# sonic-sflow YANG

## 概要

- module: `sonic-sflow`
- namespace: `http://github.com/sonic-net/sonic-sflow`
- revision: `2023-04-11`
- import: `ietf-inet-types`, `sonic-types`, `sonic-port`, `sonic-vlan`, `sonic-portchannel`, `sonic-mgmt_port`, `sonic-mgmt_vrf`
- top container: `sonic-sflow`

SFLOW yang Module for SONiC OS。コレクタ宛て・ポート別セッション・グローバル設定を含む[^1]。

## ツリー

```
module: sonic-sflow
  +--rw sonic-sflow
     +--rw SFLOW_COLLECTOR
     |  +--rw SFLOW_COLLECTOR_LIST* [name]
     |     +--rw name              string
     |     +--rw collector_ip      inet:ip-address
     |     +--rw collector_port?   inet:port-number
     |     +--rw collector_vrf?    string
     +--rw SFLOW_SESSION
     |  +--rw SFLOW_SESSION_LIST* [port]
     |     +--rw port                union
     |     +--rw admin_state?        stypes:admin_status
     |     +--rw sample_rate?        uint32
     |     +--rw sample_direction?   sample_direction
     +--rw SFLOW
        +--rw global
           +--rw admin_state?        stypes:admin_status
           +--rw polling_interval?   uint16
           +--rw agent_id?           union
           +--rw sample_direction?   sample_direction
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `name` | `sonic-sflow/SFLOW_COLLECTOR/SFLOW_COLLECTOR_LIST/name` | `string` | yes |  | length 1..16 | Name of the Sflow collector |
| `collector_ip` | `sonic-sflow/SFLOW_COLLECTOR/SFLOW_COLLECTOR_LIST/collector_ip` | `inet:ip-address` | yes |  |  | IPv4/IPv6 address of the Sflow collector |
| `collector_port` | `sonic-sflow/SFLOW_COLLECTOR/SFLOW_COLLECTOR_LIST/collector_port` | `inet:port-number` |  | 6343 |  | Destination L4 port of the Sflow collector |
| `collector_vrf` | `sonic-sflow/SFLOW_COLLECTOR/SFLOW_COLLECTOR_LIST/collector_vrf` | `string` |  |  | default or mgmt | Collector VRF (default or management) |
| `port` | `sonic-sflow/SFLOW_SESSION/SFLOW_SESSION_LIST/port` | `union` | yes |  | union(leafref to PORT, "all") | Port reference or "all" |
| `admin_state` | `sonic-sflow/SFLOW_SESSION/SFLOW_SESSION_LIST/admin_state` | `stypes:admin_status` |  | up |  | Per-port sflow admin state |
| `sample_rate` | `sonic-sflow/SFLOW_SESSION/SFLOW_SESSION_LIST/sample_rate` | `uint32` |  |  | range 256..8388608 | Per-port sample rate (1 in N) |
| `sample_direction` | `sonic-sflow/SFLOW_SESSION/SFLOW_SESSION_LIST/sample_direction` | `sample_direction` |  | rx | rx, tx, both | Sflow sample direction |
| `admin_state` | `sonic-sflow/SFLOW/global/admin_state` | `stypes:admin_status` |  | down |  | Global sflow admin state |
| `polling_interval` | `sonic-sflow/SFLOW/global/polling_interval` | `uint16` |  | 20 | range 0, 5..300 | Counter polling interval in seconds |
| `agent_id` | `sonic-sflow/SFLOW/global/agent_id` | `union` |  |  | union(port-leafref, vlan, portchannel, mgmt_port) | Interface from which the agent IP is derived |
| `sample_direction` | `sonic-sflow/SFLOW/global/sample_direction` | `sample_direction` |  | rx |  | Default sample direction for sessions |

## leafref / 依存

- `sonic-sflow/SFLOW_SESSION/SFLOW_SESSION_LIST/port` → `/prt:sonic-port/PORT/PORT_LIST/name` または `"all"`
- `sonic-sflow/SFLOW/global/agent_id` → 各種 interface leafref

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `SFLOW`, `SFLOW_COLLECTOR`, `SFLOW_SESSION`
- CLI: `config sflow`, `show sflow`

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-sflow.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
