---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 発展トピック

この章の基本経路を押さえた後は、VoQ、BFD、EVPN の順に読むと BGP が他章へどうつながるかが見える。いずれも BGP 単体の話ではなく、シャーシ構成、障害検出、overlay control plane と結びつく。

## VoQ シャーシの BGP

VoQ シャーシでは、iBGP full mesh、addpath、multipath-relax、再帰解決など、単体 ToR より BGP 設定の前提が増える。ECMP 整合性を保つための設定が重要で、minigraph や CONFIG_DB スキーマ拡張も関わる。詳細は [VoQ シャーシでの BGP 構成](../../routing/bgp-setup-for-voq-chassis.md) を参照する。

## BFD for BGP

BFD は BGP の keepalive より速く failure を検出するための補助である。BGP セッション向け BFD hardware offload では、bfdsyncd、local discriminator、remote 情報、IPv6 link-local、scale/default 値が論点になる。BGP PIC の検出契機としても BFD は重要である。詳細は [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md) を参照する。

## EVPN/VXLAN への接続

EVPN/VXLAN では FRR BGP-EVPN が Type-2/Type-5 route を扱い、VTEP、VRF、VXLAN tunnel、symmetric IRB とつながる。underlay の BGP と overlay の BGP-EVPN を混同しないことが重要である。この章で扱った FRR、route-map、VRF、経路反映の考え方は EVPN 章の前提になる。詳細は [EVPN VXLAN](../../routing/evpn-vxlan-hld.md) を参照する。

## 関連ページ

- [VoQ シャーシでの BGP 構成](../../routing/bgp-setup-for-voq-chassis.md)
- [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md)
- [EVPN VXLAN](../../routing/evpn-vxlan-hld.md)
