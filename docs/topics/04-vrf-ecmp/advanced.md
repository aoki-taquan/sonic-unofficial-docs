---
title: 発展トピックへの橋渡し
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/virtual-router-redundancy-protocol-adaptation-hld.md
  - docs/architecture/sag-high-level-design-for-sonic.md
  - docs/routing/reliable-tsa.md
---

# 発展トピックへの橋渡し

VRF / RIF / route / NHG の読み方を押さえると、周辺機能の設計意図が追いやすくなります。このページでは、章 04 から次に読む候補を整理します。

## VRRP は interface と VRF の冗長化

VRRP は、複数ルータが 1 つの仮想 router address を共有し、Master 障害時に Backup が引き継ぐ L3 冗長プロトコルです。SONiC では Ethernet、VLAN、sub-interface、PortChannel、non-default VRF が関係します。

この章の前提で見るなら、VRRP は「どの L3 interface / VRF 上で VIP と VMAC を扱うか」「FRR vrrpd と CONFIG_DB がどう連携するか」の機能です。詳細は [VRRP](../../routing/virtual-router-redundancy-protocol-adaptation-hld.md) を参照してください。

## SAG は VLAN RIF の gateway MAC を揃える

Static Anycast Gateway は、EVPN/VXLAN fabric などで複数 leaf が同じ default gateway IP / MAC を提供するための仕組みです。L3 interface と RIF の MAC、IPv6 link-local の me-route 更新が関係します。

現行ページでは community master への取り込み状況に discrepancy があるため、利用前提ではなく設計理解として読みます。詳細は [SAG for SONiC](../../architecture/sag-high-level-design-for-sonic.md) を参照してください。

## TSA は経路広告を止めて traffic を逃がす

TSA は Traffic-Shift Away のための運用機能で、BGP に route policy を適用して対象装置へ traffic が来ないようにします。FIB pipeline そのものではなく、RIB に入る前の制御プレーン運用に近い機能です。

VoQ Chassis では Supervisor と Line Card の TSA 状態同期が課題になります。詳細は [Reliable TSA](../../routing/reliable-tsa.md) を参照してください。

## 他章との境界

| 読みたいこと | 次に読む章 |
|--------------|------------|
| BGP が route を選ぶまで | BGP と FRR 制御プレーン |
| EVPN / VNET / Overlay ECMP | VXLAN / EVPN / VNET |
| SRv6 / MPLS | Segment Routing / MPLS |
| counter や telemetry の全体 | Observability / Telemetry 系の章 |
| test plan や VS test | テスト計画の章 |

## 関連ページ

- [VRRP](../../routing/virtual-router-redundancy-protocol-adaptation-hld.md)
- [SAG for SONiC](../../architecture/sag-high-level-design-for-sonic.md)
- [Reliable TSA](../../routing/reliable-tsa.md)
