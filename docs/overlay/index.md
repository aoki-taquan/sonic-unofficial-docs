---
title: オーバーレイ
description: "オーバーレイ — VXLAN / VNet、DASH、Dual ToR、NVGRE など overlay と SmartSwitch 周辺を扱う章。"
area: overlay
verification: meta
last_verified: 2026-05-13
---

# オーバーレイ
[VXLAN](../reference/glossary.md#term-vxlan) / VNet、[DASH](../reference/glossary.md#term-dash)、Dual ToR、NVGRE など overlay と [SmartSwitch](../reference/glossary.md#term-smartswitch) 周辺を扱う章。

## この章の趣旨

物理 underlay の上に仮想ネットワーク（テナント / マルチサイト / [DPU](../reference/glossary.md#term-dpu) offload）を構築するための [SONiC](../reference/glossary.md#term-sonic) 機能群を扱う。具体的には以下:

- **VXLAN / VNet**: VxlanOrch / VnetOrch / [VRF](../reference/glossary.md#term-vrf) mapper を中心とした L2VPN / L3VPN overlay
- **Dual ToR**: y-cable / [linkmgrd](../reference/glossary.md#term-linkmgrd) / [IPinIP](../reference/glossary.md#term-ipinip) tunnel による HA、active-active 構成も含む
- **DASH / SmartSwitch**: [NPU](../reference/glossary.md#term-npu) + DPU 構成での [ENI](../reference/glossary.md#term-eni) / [ACL](../reference/glossary.md#term-acl) / connection offload
- **NVGRE**: nvgreorch + decap mapper の legacy overlay

## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。

## 主要ページ

- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](vxlan-sonic.md)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](sonic-dash-hld.md)
- [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](active-active-dual-tor.md)
- [Active-Standby Dual ToR（y-cable + linkmgrd state machine + IPinIP tunnel）](active-standby-dual-tor.md)
- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](smartswitch-eni-based-forwarding.md)
- [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](vnet-local-endpoint-forwarding.md)
- [NVGRE トンネル（nvgreorch / decap mapper）](nvgre-tunnel-in-sonic.md)
- [DASH SONiC KVM（BMv2 ベース仮想 DPU）](dash-sonic-kvm.md)
- [トンネルトラフィックの DSCP / TC リマップ（Dual-ToR PFC デッドロック回避）](dscp-remapping-for-tunnel-traffic.md)

## 扱わない範囲

- L3 underlay の経路設計そのもの（[BGP](../reference/glossary.md#term-bgp) / [ECMP](../reference/glossary.md#term-ecmp) / VRF route leak は [routing](../routing/index.md) 章）
- SmartSwitch ハードウェア依存層（DPU カード固有の bring-up は [platform](../platform/index.md) 章）
- DASH の上位 API スキーマ詳細（[reference](../reference/index.md) 章の [CONFIG_DB](../reference/glossary.md#term-config_db) / [YANG](../reference/glossary.md#term-yang) リファレンスを参照）
- ベンダー版 SONiC の overlay 実装差分（コミュニティ版 `master` のみ扱う）

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

<!-- glossary-links-injected: 585abfc893ca -->
