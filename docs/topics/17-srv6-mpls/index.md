---
title: SRv6 / MPLS / Path Tracing
description: SRv6 / MPLS / Path Tracing — この章は、SONiC で SRv6（Segment Routing over IPv6）、MPLS、そして経路観測のための Path Tracing をまとめて読むための入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- SRv6
- MPLS
- Path Tracing
- segment routing
- label switching
- SID
- uSID
- transit
- underlay
related:
  cli:
  - config bgp
  - config qos
  - config vrf
  - show bgp
  - config vxlan
  - clear counters
  - config interface
  config_db:
  - CRM
  - PORT_QOS_MAP
  - VRF
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP_AF
  - INTERFACE
  yang:
  - sonic-srv6
  - sonic-crm
  - sonic-bgp-bbr
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peerrange
  - sonic-interface
---

# SRv6 / MPLS / Path Tracing

この章は、[SONiC](../../reference/glossary.md#term-sonic) で [SRv6](../../reference/glossary.md#term-srv6)（Segment Routing over IPv6）、[MPLS](../../reference/glossary.md#term-mpls)、そして経路観測のための Path Tracing をまとめて読むための入口です。SRv6 関連 [HLD](../../reference/glossary.md#term-hld) は base、uSID、static SID、L3 隣接、VPN と段階的に積み上がっているため、ここでは「どの順で読めばよいか」と「[BGP](../../reference/glossary.md#term-bgp) / [VRF](../../reference/glossary.md#term-vrf) / [EVPN](../../reference/glossary.md#term-evpn) 章とどこで接続するか」を最初に整理します。

SRv6 は IPv6 をベースに SID list を運ぶ network programming framework、MPLS は静的 LSP を起点に label switching を [SAI](../../reference/glossary.md#term-sai)/[orchagent](../../reference/glossary.md#term-orchagent) に拡張した基盤、Path Tracing は転送経路を IPv6 Hop-by-Hop オプションに刻んで観測する仕組みです。三者は別機能ですが、route / [RIF](../../reference/glossary.md#term-rif) / counter / [QoS](../../reference/glossary.md#term-qos) map といった SONiC 内部の共通部品でつながっており、特に SRv6 と Path Tracing は IPv6 forwarding と直接重なります。

## この章で答える質問

- SRv6 base、uSID、static SID、L3 隣接、VPN はどの順で読むか。
- MPLS は SONiC の route / RIF / QoS マップ / [CRM](../../reference/glossary.md#term-crm) とどう接続するか。
- Path Tracing Midpoint は通常 IPv6 forwarding と何が違うか。SRv6 endpoint 処理とどう共存するか。
- SRv6 / MPLS の設定は CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) の reference にどこまであるか。
- BGP / VRF / EVPN-[VXLAN](../../reference/glossary.md#term-vxlan) 章とはどこで境界を引くか。

## 読み進め方

1. [概念](concept.md): SRv6 / MPLS / Path Tracing の位置付けと、関連章への前提リンク。
2. [アーキテクチャ](architecture.md): `srv6orch`、locator / SID / VPN / policy、MPLS pipeline、Path Tracing midpoint の object flow。
3. [設定](setup.md): static SID / locator、`SRV6_MY_SID_TABLE`、`LABEL_ROUTE_TABLE`、MPLS TC マップ、PT interface ID の最小構成。
4. [運用](operations.md): RIF counter、MySID counter、Path Tracing と show 系の確認順。
5. [内部実装](internals.md): srv6orch の SAI 呼び出し、`MY_SID_ENTRY`、`uSID` / `L3Adj` の解決、[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) / frrcfgd の SRv6 manager。
6. [発展トピック](advanced.md): EVPN / BGP との接続、[FRR](../../reference/glossary.md#term-frr) SRv6 制御プレーン、将来 phase（HMAC / sBFD / anycast SID）への分岐。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SONiC の MPLS 基盤](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| advanced | 120 | ✅ 完成 | meta | 発展トピック |
| architecture | 80 | ⚠️ プレースホルダ | code-verified | アーキテクチャ・データフロー |
| concept | 227 | ✅ 完成 | code-verified | 概念・位置付け |
| internals | 129 | ✅ 完成 | meta | 内部実装 |
| operations | 254 | ✅ 完成 | code-verified | 運用・デバッグ |
| setup | 246 | ✅ 完成 | meta | セットアップ手順 |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: 概念](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [SRv6 VPN（L3VPN over SRv6 と SRv6 Policy）](../../routing/srv6-vpn-hld.md)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../../routing/bgp-setup-for-voq-chassis.md)
- [Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期）](../../routing/reliable-tsa.md)
- [NEXT_HOP_GROUP_TABLE による APP_DB ルートとネクストホップ分離](../../routing/routing-and-next-hop-table-enhancement.md)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../../routing/bfd-hw-offload-for-bgp-session.md)
- [BGP Loading Optimization（fpmsyncd flush / orchagent ring buffer / async sairedis）](../../routing/bgp-loading-optimization-for-sonic.md)
- [BGP PIC（Prefix Independent Convergence / NHG 階層）](../../routing/bgp-prefix-independent-convergence-architecture-document.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [PFC で帯域が出ない / Buffer overflow](../../reference/runbooks/pfc-bandwidth.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [BGP と FRR 制御プレーン](../02-bgp/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
