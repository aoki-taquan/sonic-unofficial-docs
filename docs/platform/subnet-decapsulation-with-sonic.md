---
title: VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）
area: platform
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/decap/subnet_decap_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - SUBNET_DECAP
  cli:
    - show tunnel
    - show tunnel decap
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    HLD は 2024 年 3 月版 (Rev 0.1)。`TunnelDecapOrch` の `SUBNET_DECAP` / `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` 取り込み、`MP2MP` 形式の decap term の SAI 実装、`IPINIP_SUBNET` / `IPINIP_V6_SUBNET` 自動生成、warm-reboot 対応 (`swssconfig.sh` 拡張) は未裏取り。

# VLAN Subnet Decap（Netscan 用 IPinIP MP2MP デカプスル）

## 概要

Azure Netscan は **IPinIP プローブ**（outer DIP=デバイス Loopback、inner DIP=Netscan 送信元）でネットワーク経路の blackhole を検知する。従来は host node 上の VLAN subnet IP までは可視化できなかった[^1]。

本 HLD は T0 SONiC に **VLAN subnet 全体**を IPinIP decap 対象にする `IPINIP_SUBNET` / `IPINIP_V6_SUBNET` を自動生成し、Netscan IPinIP probe を T0 が代理で受けて inner を Netscan に戻すことで **VLAN subnet IP の経路 blackhole を検知できる** ようにする。

## 動作仕様

### 自動生成される tunnel / term[^1]

| 属性 | 値 |
|------|-----|
| name | `IPINIP_SUBNET` または `IPINIP_V6_SUBNET` |
| tunnel type | `IPinIP` |
| decap ECN mode | `copy_from_outer` または `standard` |
| decap TTL mode | `pipe` |
| decap DSCP mode | `uniform` |

decap term:

| 属性 | 値 |
|------|-----|
| term_type | `MP2MP`（multi-point to multi-point） |
| dest IP | VLAN subnet |
| dest IP mask | VLAN subnet mask |
| source IP | **Netscan privately-owned subnet**（顧客 IPinIP との誤動作回避） |
| source IP mask | 同上 |

source IP を Netscan の private subnet に絞ることで、顧客の正規 IPinIP traffic と区別する設計。

### CONFIG_DB スキーマ[^1]

```text
SUBNET_DECAP|<config_name>
  status     = enable | disable
  src_ip     = <IPv4 prefix>
  src_ip_v6  = <IPv6 prefix>
  vlan       = カンマ区切り VLAN リスト（空なら全 VLAN）
```

### APPL_DB スキーマ[^1]

```text
TUNNEL_DECAP_TABLE:<tunnel_name>
  tunnel_type    = IPINIP
  dscp_mode      = uniform | pipe
  ecn_mode       = copy_from_outer | standard
  ttl_mode       = uniform | pipe
  encap_ecn_mode = standard

TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip>
  term_type   = P2P | P2MP | MP2MP
  src_ip      = <prefix>           # subnet decap の通常 term は省略
  subnet_type = vlan | vip         # subnet decap term ならこのフィールドあり
```

`STATE_DB` には `TunnelDecapOrch` が実際に作った tunnel / term を反映する[^1]。

### 動作フロー

```mermaid
flowchart TD
  CFG[CONFIG_DB SUBNET_DECAP|...<br>status=enable] --> SC[swssconfig service<br>テンプレート展開]
  SC --> APP[APPL_DB<br>TUNNEL_DECAP_TABLE / _TERM_TABLE]
  APP --> ORCH[TunnelDecapOrch]
  ORCH --> SAI[(SAI tunnel decap term<br>MP2MP)]
  Net[Netscan sender] -->|IPinIP outer DIP=Loopback<br>inner DIP=VLAN subnet IP| T0[T0 SONiC]
  T0 -->|decap + route back| Net
```

`TunnelDecapOrch` は `SUBNET_DECAP` の **src_ip / src_ip_v6 変更** に追従し、対応する decap term の source IP を更新する[^1]。

### Dual-ToR 考慮[^1]

両 ToR は同じ VLAN/decap 設定。T1 → ToR は ECMP なのでどちらの ToR が受けても decap → Netscan へ戻せる。

### Warm-reboot

現状 SONiC は warm-reboot 後に `ipinip.json` を再 load しない。本機能で追加した 2 tunnel (`IPINIP_SUBNET` / `IPINIP_V6_SUBNET`) のみ warm 後に APPL_DB へ書く処理を **`swssconfig.sh` に拡張** する必要がある[^1]。既存 tunnel の重複書込は避ける。

### CLI[^1]

```text
# show tunnel brief
Tunnel Name       Type    Dscp Mode    ECN Mode         TTL Mode
IPINIP_TUNNEL     IPINIP  uniform      copy_from_outer  pipe
IPINIP_V6_TUNNEL  IPINIP  uniform      copy_from_outer  pipe
IPINIP_SUBNET     IPINIP  uniform      copy_from_outer  pipe
IPINIP_V6_SUBNET  IPINIP  uniform      copy_from_outer  pipe

# show tunnel decap
Dst IP         Src IP         Tunnel Name    Decap Term Type
192.168.0.1    N/A            IPINIP_TUNNEL  P2MP
10.10.10.0/24  20.20.20.0/24  IPINIP_SUBNET  MP2MP
```

## 制限事項

- T0 限定。spine では適用しない[^1]
- src IP は Netscan private subnet 限定。顧客 traffic との混線防止
- `vlan` フィールド空 = 全 VLAN 対象
- 現状サポートされる動的更新は **src IP 変更のみ**[^1]

## 干渉する機能

- **既存 IPINIP_TUNNEL / IPINIP_V6_TUNNEL**: 共存。本機能は別の 2 tunnel を追加
- **TunnelDecapOrch**: 既存処理を拡張。`SUBNET_DECAP` テーブル subscribe を追加
- **swssconfig**: warm-reboot 後の選択的書込

## 引用元

[^1]: [sonic-net/SONiC doc/decap/subnet_decap_HLD.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/decap/subnet_decap_HLD.md)
