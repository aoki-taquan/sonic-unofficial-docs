---
title: SRv6 / MPLS / Path Tracing
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/sonic-usid.md
  - docs/routing/srv6-sid-l3adj.md
  - docs/routing/srv6-vpn-hld.md
  - docs/routing/static-configuration-of-srv6-in-sonic-hld.md
  - docs/routing/mpls-for-sonic-high-level-design-document.md
  - docs/routing/mpls-tc-to-tc-map.md
  - docs/routing/path-tracing-midpoint.md
  - docs/routing/router-interface-counters-in-sonic.md
  - docs/routing/evpn-vxlan-hld.md
  - docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md
  - docs/reference/yang/sonic-route-common.md
---

# SRv6 / MPLS / Path Tracing

この章は、SONiC で SRv6（Segment Routing over IPv6）、MPLS、そして経路観測のための Path Tracing をまとめて読むための入口です。SRv6 関連 HLD は base、uSID、static SID、L3 隣接、VPN と段階的に積み上がっているため、ここでは「どの順で読めばよいか」と「BGP / VRF / EVPN 章とどこで接続するか」を最初に整理します。

SRv6 は IPv6 をベースに SID list を運ぶ network programming framework、MPLS は静的 LSP を起点に label switching を SAI/orchagent に拡張した基盤、Path Tracing は転送経路を IPv6 Hop-by-Hop オプションに刻んで観測する仕組みです。三者は別機能ですが、route / RIF / counter / QoS map といった SONiC 内部の共通部品でつながっており、特に SRv6 と Path Tracing は IPv6 forwarding と直接重なります。

## この章で答える質問

- SRv6 base、uSID、static SID、L3 隣接、VPN はどの順で読むか。
- MPLS は SONiC の route / RIF / QoS マップ / CRM とどう接続するか。
- Path Tracing Midpoint は通常 IPv6 forwarding と何が違うか。SRv6 endpoint 処理とどう共存するか。
- SRv6 / MPLS の設定は CLI / CONFIG_DB / YANG の reference にどこまであるか。
- BGP / VRF / EVPN-VXLAN 章とはどこで境界を引くか。

## 読み進め方

1. [概念](concept.md): SRv6 / MPLS / Path Tracing の位置付けと、関連章への前提リンク。
2. [アーキテクチャ](architecture.md): `srv6orch`、locator / SID / VPN / policy、MPLS pipeline、Path Tracing midpoint の object flow。
3. [設定](setup.md): static SID / locator、`SRV6_MY_SID_TABLE`、`LABEL_ROUTE_TABLE`、MPLS TC マップ、PT interface ID の最小構成。
4. [運用](operations.md): RIF counter、MySID counter、Path Tracing と show 系の確認順。
5. [内部実装](internals.md): srv6orch の SAI 呼び出し、`MY_SID_ENTRY`、`uSID` / `L3Adj` の解決、bgpcfgd / frrcfgd の SRv6 manager。
6. [発展トピック](advanced.md): EVPN / BGP との接続、FRR SRv6 制御プレーン、将来 phase（HMAC / sBFD / anycast SID）への分岐。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SONiC の MPLS 基盤](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
