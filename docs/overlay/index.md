---
title: オーバーレイ
description: "オーバーレイ — VXLAN / VNet、DASH、Dual ToR、NVGRE など overlay と SmartSwitch 周辺を扱う章。"
verification: stub
---

# オーバーレイ
[VXLAN](../reference/glossary.md#term-vxlan) / VNet、[DASH](../reference/glossary.md#term-dash)、Dual ToR、NVGRE など overlay と [SmartSwitch](../reference/glossary.md#term-smartswitch) 周辺を扱う章。
## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。
## 検証状況
- ページ数: 9
- 分布: Code-verified: 8 / Discrepancy-found: 1

## 実装差分があるページ
- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](dscp-remapping-for-tunnel-traffic.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](active-active-dual-tor.md) | Code-verified |
| [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](active-standby-dual-tor.md) | Code-verified |
| [DASH SONiC KVM（BMv2 ベース仮想 DPU）](dash-sonic-kvm.md) | Code-verified |
| [NVGRE トンネル（nvgreorch / decap mapper）](nvgre-tunnel-in-sonic.md) | Code-verified |
| [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](sonic-dash-hld.md) | Code-verified |
| [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](smartswitch-eni-based-forwarding.md) | Code-verified |
| [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](vnet-local-endpoint-forwarding.md) | Code-verified |
| [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](vxlan-sonic.md) | Code-verified |
| [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](dscp-remapping-for-tunnel-traffic.md) | Discrepancy-found |

<!-- glossary-links-injected: 9751825192ec -->
