---
title: VXLAN / EVPN / VNET オーバーレイ
description: VXLAN / EVPN / VNET オーバーレイ — この章は、SONiC の overlay を「VXLAN tunnel を作る」「VNET と VRF/VNI を対応させる」「EVPN やコントローラから経路を入れる」「運用中に ECMP、BFD、QoS を確認する」という読者の順番で読み直す入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- VXLAN
- EVPN
- VNET
- オーバーレイ
- VNI
- type-2
- type-5
- VTEP
- tunnel
- overlay
related:
  cli:
  - config vnet
  - config bgp
  - config vlan
  - show bfd
  - show bgp
  - config vxlan
  - show arp
  config_db:
  - VLAN
  - VNET
  - VXLAN_TUNNEL_MAP
  - VRF
  - VXLAN_TUNNEL
  - TUNNEL_DECAP_TABLE
  - VXLAN_EVPN_NVO
  yang:
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-vnet
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# VXLAN / EVPN / VNET オーバーレイ

この章は、[SONiC](../../reference/glossary.md#term-sonic) の overlay を「[VXLAN](../../reference/glossary.md#term-vxlan) tunnel を作る」「[VNET](../../reference/glossary.md#term-vnet) と [VRF](../../reference/glossary.md#term-vrf)/VNI を対応させる」「[EVPN](../../reference/glossary.md#term-evpn) やコントローラから経路を入れる」「運用中に [ECMP](../../reference/glossary.md#term-ecmp)、[BFD](../../reference/glossary.md#term-bfd)、[QoS](../../reference/glossary.md#term-qos) を確認する」という読者の順番で読み直す入口です。

既存ページは VXLAN、EVPN、VNET、NVGRE、[IPinIP](../../reference/glossary.md#term-ipinip) decap、Overlay ECMP などの [HLD](../../reference/glossary.md#term-hld) 単位に分かれています。この章では、それらを 1 つの overlay データプレーンとして見たときの責務境界を先に整理し、詳細なフィールドや実装裏取りは area / reference ページへ誘導します。

## この章で答える質問

- VXLAN、VNET、EVPN は同じ機能なのか、どこで役割が分かれるのか。
- EVPN Type-2 / Type-5、[VTEP](../../reference/glossary.md#term-vtep)、VRF、VNI、VNetOrch はどうつながるのか。
- `VXLAN_TUNNEL`、`VXLAN_TUNNEL_MAP`、`VNET`、`VNET_ROUTE_TUNNEL` はどの順に設定するのか。
- Overlay ECMP、BFD monitoring、[DSCP](../../reference/glossary.md#term-dscp) remap、inner packet hashing は運用上どこを見るのか。
- NVGRE や subnet decap は VXLAN と同じ章でどう扱えばよいのか。

## 読む順番

1. [概要](concept.md): VXLAN / VNET / EVPN / NVGRE / subnet decap の用語と境界を整理する。
2. [アーキテクチャ](architecture.md): VxlanTunnelOrch、VnetOrch、[FRR](../../reference/glossary.md#term-frr) EVPN、[SAI](../../reference/glossary.md#term-sai) tunnel object の流れを追う。
3. [設定](setup.md): VXLAN tunnel、VNET、EVPN NVO、VNET route、tunnel decap、PBH inner hash の入口を選ぶ。
4. [運用](operations.md): Overlay ECMP、BFD monitoring、DSCP remap、inner hash の確認順を扱う。
5. [発展トピック](advanced.md): EVPN multihoming、[DASH](../../reference/glossary.md#term-dash) / [SmartSwitch](../../reference/glossary.md#term-smartswitch)、NVGRE、subnet decap との境界を確認する。
6. [内部実装](internals.md): VxlanTunnelOrch / VnetOrch のオブジェクト整合と、FRR EVPN との状態同期を実装側から見る。

## 統合した既存ページ

この章は overlay / routing / platform / architecture / reference の既存ページ 22 件を横断しています。各ページの末尾に、深掘り用の関連ページを置いています。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 173 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 79 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| setup | 240 | ✅ 完成 | meta | セットアップ手順 |
| operations | 167 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 130 | ✅ 完成 | meta | 内部実装 |
| advanced | 100 | ✅ 完成 | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: VXLAN / VNET / EVPN の概要](concept.md)
- [アーキテクチャ: Overlay アーキテクチャ](architecture.md)
- [設定: Overlay 設定](setup.md)
- [運用: Overlay 運用](operations.md)
- [内部実装](internals.md)
- [発展トピック: Overlay 発展トピック](advanced.md)

**関連する HLD 7 件**

- [VXLAN / VNet 概念（VTEP + VNet + L2/L3 トンネル）](../../overlay/vxlan-sonic-concepts.md)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../../overlay/vxlan-sonic.md)
- [VXLAN / VNet 内部実装（VxlanTunnelOrch / VnetOrch / SAI 属性）](../../overlay/vxlan-sonic-internals.md)
- [VXLAN / VNet 制限事項と既知の課題](../../overlay/vxlan-sonic-limitations.md)
- [VXLAN / VNet 設定と運用（CONFIG_DB / APP_DB / CLI）](../../overlay/vxlan-sonic-operations.md)
- [Active-Active Dual ToR（gRPC ベース cable control + prefix-based neighbor）](../../overlay/active-active-dual-tor.md)
- [Active-Standby Dual ToR 制限事項と既知の課題](../../overlay/active-standby-dual-tor-limitations.md)

**関連トラブルシュート 5 件**

- [EVPN Type-2 route が広告されない](../../reference/runbooks/evpn-type2-not-advertised.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [BGP と FRR 制御プレーン](../02-bgp/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [DASH と SmartSwitch](../13-dash-smartswitch/index.md)
- [Dual-ToR と Mux 制御](../05-dual-tor/index.md)

**補完的に読む章**

- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

<!-- glossary-links-injected: c5c8b661ae7e -->
