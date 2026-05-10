---
title: VXLAN / EVPN / VNET オーバーレイ
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/overlay/vxlan-sonic.md
  - docs/routing/evpn-vxlan-hld.md
  - docs/overlay/nvgre-tunnel-in-sonic.md
  - docs/platform/subnet-decapsulation-with-sonic.md
  - docs/routing/overlay-ecmp-with-bfd-monitoring.md
  - docs/routing/overlay-ecmp-enhancements.md
  - docs/overlay/dscp-remapping-for-tunnel-traffic.md
---

# VXLAN / EVPN / VNET オーバーレイ

この章は、SONiC の overlay を「VXLAN tunnel を作る」「VNET と VRF/VNI を対応させる」「EVPN やコントローラから経路を入れる」「運用中に ECMP、BFD、QoS を確認する」という読者の順番で読み直す入口です。

既存ページは VXLAN、EVPN、VNET、NVGRE、IPinIP decap、Overlay ECMP などの HLD 単位に分かれています。この章では、それらを 1 つの overlay データプレーンとして見たときの責務境界を先に整理し、詳細なフィールドや実装裏取りは area / reference ページへ誘導します。

## この章で答える質問

- VXLAN、VNET、EVPN は同じ機能なのか、どこで役割が分かれるのか。
- EVPN Type-2 / Type-5、VTEP、VRF、VNI、VNetOrch はどうつながるのか。
- `VXLAN_TUNNEL`、`VXLAN_TUNNEL_MAP`、`VNET`、`VNET_ROUTE_TUNNEL` はどの順に設定するのか。
- Overlay ECMP、BFD monitoring、DSCP remap、inner packet hashing は運用上どこを見るのか。
- NVGRE や subnet decap は VXLAN と同じ章でどう扱えばよいのか。

## 読む順番

1. [概要](concept.md): VXLAN / VNET / EVPN / NVGRE / subnet decap の用語と境界を整理する。
2. [アーキテクチャ](architecture.md): VxlanTunnelOrch、VnetOrch、FRR EVPN、SAI tunnel object の流れを追う。
3. [設定](setup.md): VXLAN tunnel、VNET、EVPN NVO、VNET route、tunnel decap、PBH inner hash の入口を選ぶ。
4. [運用](operations.md): Overlay ECMP、BFD monitoring、DSCP remap、inner hash の確認順を扱う。
5. [発展トピック](advanced.md): EVPN multihoming、DASH / SmartSwitch、NVGRE、subnet decap との境界を確認する。

## 統合した既存ページ

この章は overlay / routing / platform / architecture / reference の既存ページ 22 件を横断しています。各ページの末尾に、深掘り用の関連ページを置いています。
