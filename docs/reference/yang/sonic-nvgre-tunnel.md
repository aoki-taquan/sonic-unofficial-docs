---
title: sonic-nvgre-tunnel YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-nvgre-tunnel.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [NVGRE_TUNNEL, NVGRE_TUNNEL_MAP]
  cli: []
  yang: [sonic-vxlan, sonic-vnet]
---

# sonic-nvgre-tunnel YANG

## 概要

- module: `sonic-nvgre-tunnel`
- namespace: `http://github.com/sonic-net/sonic-nvgre-tunnel`
- revision: `2021-10-31`
- import: `ietf-inet-types`
- top container: `sonic-nvgre-tunnel`

NVGRE トンネルとそれに紐付く VLAN-VSID マッピングを定義する YANG モジュール[^1]。

## ツリー

```
module: sonic-nvgre-tunnel
  +--rw sonic-nvgre-tunnel
     +--rw NVGRE_TUNNEL
     |  +--rw NVGRE_TUNNEL_LIST* [tunnel_name]
     |     +--rw tunnel_name   string
     |     +--rw src_ip        inet:ip-address
     +--rw NVGRE_TUNNEL_MAP
        +--rw NVGRE_TUNNEL_MAP_LIST* [tunnel_name tunnel_map_name]
           +--rw tunnel_name       -> /nvgre:sonic-nvgre-tunnel/NVGRE_TUNNEL/NVGRE_TUNNEL_LIST/tunnel_name
           +--rw tunnel_map_name   string
           +--rw vlan_id           uint16
           +--rw vsid              uint32
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `tunnel_name` | `sonic-nvgre-tunnel/NVGRE_TUNNEL/NVGRE_TUNNEL_LIST/tunnel_name` | `string` | yes |  | length 1..255 | NVGRE トンネル名 |
| `src_ip` | `sonic-nvgre-tunnel/NVGRE_TUNNEL/NVGRE_TUNNEL_LIST/src_ip` | `inet:ip-address` | yes |  |  | トンネル送信元 IP |
| `tunnel_name` | `sonic-nvgre-tunnel/NVGRE_TUNNEL_MAP/NVGRE_TUNNEL_MAP_LIST/tunnel_name` | `leafref` | yes |  | NVGRE_TUNNEL_LIST/tunnel_name | 紐付けるトンネル名 |
| `tunnel_map_name` | `.../tunnel_map_name` | `string` | yes |  | length 1..255 | マップ名 |
| `vlan_id` | `.../vlan_id` | `uint16` | yes |  | range 1..4094 | 対応する VLAN ID |
| `vsid` | `.../vsid` | `uint32` | yes |  | range 0..16777214 | Virtual Subnet Identifier |

## leafref / 依存

- `NVGRE_TUNNEL_MAP_LIST/tunnel_name` → `NVGRE_TUNNEL_LIST/tunnel_name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `NVGRE_TUNNEL`, `NVGRE_TUNNEL_MAP`
- CLI: なし（CONFIG_DB 直接設定）

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`NVGRE_TUNNEL`](../config-db/nvgre-tunnel.md) / `NVGRE_TUNNEL_MAP`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-nvgre-tunnel.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
