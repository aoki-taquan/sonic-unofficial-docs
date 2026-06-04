---
title: ルーティング
description: "ルーティング — BGP、VRF、ECMP、SRv6、MPLS、DHCP relay など L3 制御面を扱う章。"
area: routing
verification: meta
last_verified: 2026-05-13
---

# ルーティング
[BGP](../reference/glossary.md#term-bgp)、[VRF](../reference/glossary.md#term-vrf)、[ECMP](../reference/glossary.md#term-ecmp)、[SRv6](../reference/glossary.md#term-srv6)、[MPLS](../reference/glossary.md#term-mpls)、DHCP relay など L3 制御面を扱う章。
## この章の読み方
目的の機能名からページを選び、設定名や CLI 名が必要な場合はリファレンス章を併読する。`Discrepancy-found` は [HLD](../reference/glossary.md#term-hld) と現行実装に差分が見つかったページなので、設計値として読む前に本文の注記を確認する。
## 検証状況
- ページ数: 57
- 分布: code-verified: 43 / Discrepancy-found: 14 / HLD-only: 0

## 実装差分があるページ
- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](bgp-route-install-error-handling.md)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](bfd-hw-offload-for-bgp-session.md)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](evpn-vxlan-multihoming.md)
- [EVPN VXLAN Multihoming 概念（ESI / DF election / Split-horizon / Aliasing）](evpn-vxlan-multihoming-concepts.md)
- [EVPN VXLAN Multihoming 実装内部（EvpnMhOrch / L2nhgOrch / ShlOrch / SAI L2 NHG）](evpn-vxlan-multihoming-internals.md)
- [EVPN VXLAN Multihoming 運用（config interface evpn-esi / show vxlan ethernet-segment / 差分）](evpn-vxlan-multihoming-operations.md)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](evpn-vxlan-hld.md)
- [EVPN VXLAN 概念（Route Type 2/3/5 / L2VNI / L3VNI / IRB）](evpn-vxlan-hld-concepts.md)
- [EVPN VXLAN 内部実装（FRR → fpmsyncd → APPL_DB → orchagent → SAI）](evpn-vxlan-hld-internals.md)
- [EVPN VXLAN 設定・運用（vtysh / show evpn / show bgp l2vpn）](evpn-vxlan-hld-operations.md)
- [Local ARS（Adaptive Routing & Switching の local 完結版）](local-ars-hld.md)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](bgp-setup-for-voq-chassis.md)
- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](bgpcfgd-dynamic-peer-modification-support.md)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](fpmsyncd-nexthop-group-enhancement-high-level-design-document.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [BBR 連動の BGP ルート集約（BGP_AGGREGATE_ADDRESS）](bgp-route-aggregation-with-bbr-awareness.md) | code-verified |
| [BFD ハードウェアオフロード（BfdOrch / BFD_SESSION）](bfd-hw-offload.md) | code-verified |
| [BGP Loading Optimization（fpmsyncd flush / orchagent ring buffer / async sairedis）](bgp-loading-optimization-for-sonic.md) | code-verified |
| [BGP PIC（Prefix Independent Convergence / NHG 階層）](bgp-prefix-independent-convergence-architecture-document.md) | code-verified |
| [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](bgp-route-install-error-handling.md) | Discrepancy-found |
| [BGP Suppress FIB Pending（dplane_fpm_nl + RTM_F_OFFLOAD）](bgp-suppress-announcements-of-routes-not-installed-in-hw.md) | code-verified |
| [BGP router-id を明示的に設定する（DEVICE_METADATA.bgp_router_id）](bgp-router-id-explicitly-configured.md) | code-verified |
| [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](bfd-hw-offload-for-bgp-session.md) | Discrepancy-found |
| [BMP（BGP Monitoring Protocol / BMP_STATE_DB）](bmp-for-monitoring-sonic-bgp-info.md) | code-verified |
| [CiscoBgp4MIB の STATE_DB 経由化（bgpmon / NEIGH_STATE_TABLE）](ciscobgp4mib-implementation-changes.md) | code-verified |
| [DHCP Relay per-interface counter（dhcpmon マルチスレッド + COUNTERS_DB 永続化）](dhcp-relay-per-interface-counter.md) | code-verified |
| [DHCPv6 リレー（dhcp-relay docker 内の dhcrelay -6 プロセス）](dhcp-relay-for-ipv6-hld.md) | code-verified |
| [ECMP inner packet hashing テストプラン（PBH 経由の VxLAN/NVGRE 内側 5-tuple ハッシュ）](test-plan-for-inner-packet-hashing-in-ecmp.md) | code-verified |
| [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](evpn-vxlan-multihoming.md) | Discrepancy-found |
| [EVPN VXLAN Multihoming 概念（ESI / DF election / Split-horizon / Aliasing）](evpn-vxlan-multihoming-concepts.md) | Discrepancy-found |
| [EVPN VXLAN Multihoming 実装内部（EvpnMhOrch / L2nhgOrch / ShlOrch / SAI L2 NHG）](evpn-vxlan-multihoming-internals.md) | Discrepancy-found |
| [EVPN VXLAN Multihoming 運用（config interface evpn-esi / show vxlan ethernet-segment / 差分）](evpn-vxlan-multihoming-operations.md) | Discrepancy-found |
| [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](evpn-vxlan-hld.md) | Discrepancy-found |
| [EVPN VXLAN 概念（Route Type 2/3/5 / L2VNI / L3VNI / IRB）](evpn-vxlan-hld-concepts.md) | Discrepancy-found |
| [EVPN VXLAN 内部実装（FRR → fpmsyncd → APPL_DB → orchagent → SAI）](evpn-vxlan-hld-internals.md) | Discrepancy-found |
| [EVPN VXLAN 設定・運用（vtysh / show evpn / show bgp l2vpn）](evpn-vxlan-hld-operations.md) | Discrepancy-found |
| [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](sonic-frr-bgp-extended-unified-configuration-management-framework.md) | code-verified |
| [Fine Grained ECMP（FG_NHG / fgnhgorch）](sonic-fine-grained-ecmp.md) | code-verified |
| [IPv6 Link-Local アドレス管理（自動生成と use-link-local-only）](ipv6-link-local-enhancements.md) | code-verified |
| [Local ARS（Adaptive Routing & Switching の local 完結版）](local-ars-hld.md) | Discrepancy-found |
| [MPLS TC → TC map（MPLS パケットの QoS classification）](mpls-tc-to-tc-map.md) | code-verified |
| [Management VRF 設計（201911 release / l3mdev + cgroups）](sonic-management-vrf-design-document-201911-release.md) | code-verified |
| [NEXT_HOP_GROUP_TABLE による APP_DB ルートとネクストホップ分離](routing-and-next-hop-table-enhancement.md) | code-verified |
| [Ordered ECMP（IP ソート順で nexthop に sequence_id を付け同一フローを同 ToR/Appliance に固定）](high-level-design-document.md) | code-verified |
| [Overlay ECMP with BFD monitoring（VxLAN VNet ルートと BFD 連動）](overlay-ecmp-with-bfd-monitoring.md) | code-verified |
| [Overlay ECMP の Primary/Secondary・カスタム監視・BFD タイマ拡張](overlay-ecmp-enhancements.md) | code-verified |
| [Path Tracing Midpoint（IPv6 HbH-PT に MCD を追記）](path-tracing-midpoint.md) | code-verified |
| [Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期）](reliable-tsa.md) | code-verified |
| [Route Flow Counter（ROUTE_MATCH / Route Pattern Orch）](sonic-route-flow-counter-design.md) | code-verified |
| [SONiC における FRR upgrade の手順とパッチ管理](detailed-steps-to-upgrade-frr-in-sonic.md) | code-verified |
| [SONiC の MPLS 基盤（per-RIF MPLS / LABEL_ROUTE_TABLE / 静的 LSP）](mpls-for-sonic-high-level-design-document.md) | code-verified |
| [SRv6 SID の L3 隣接（uA / End.X / uDX4 / uDX6 / End.DX4 / End.DX6）](srv6-sid-l3adj.md) | code-verified |
| [SRv6 Static SID/Locator 設定（CONFIG_DB → bgpcfgd → FRR）](static-configuration-of-srv6-in-sonic-hld.md) | code-verified |
| [SRv6 VPN（L3VPN over SRv6 と SRv6 Policy）](srv6-vpn-hld.md) | code-verified |
| [SRv6 uSID（srv6orch の uN/uA/uDT/uDX 拡張）](sonic-usid.md) | code-verified |
| [SRv6（Segment Routing over IPv6 / END.DT46 / H.Encaps.Red）](segment-routing-over-ipv6-srv6-hld.md) | code-verified |
| [Static IP Route 設定（STATIC_ROUTE → frrcfgd → FRR）](static-ip-route-configuration.md) | code-verified |
| [VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）](vrf-feature-ansible-test-plan-omit-in-toc.md) | code-verified |
| [VRF VS テストプラン（vrfmgrd / intfmgrd / Orchagent → APP_DB / ASIC_DB / kernel）](vrf-vs-test-plan.md) | code-verified |
| [VRF サポート（vrfmgrd / vrforch / FRR vrf-aware）](sonic-vrf-support-design-spec-draft.md) | code-verified |
| [VRRP（FRR vrrpd 連携 / VRRPv2/v3 / uplink tracking）](virtual-router-redundancy-protocol-adaptation-hld.md) | code-verified |
| [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](bgp-setup-for-voq-chassis.md) | Discrepancy-found |
| [Weighted ECMP（WCMP / BGP link-bandwidth ext community）](sonic-weighted-ecmp.md) | code-verified |
| [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](bgpcfgd-dynamic-peer-modification-support.md) | Discrepancy-found |
| [dual-tor mux 跨ぎの multi-nexthop route ループ回避（MuxOrch::updateRoute）](multiple-nexthop-route-hld.md) | code-verified |
| [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](fpmsyncd-nexthop-group-enhancement-high-level-design-document.md) | Discrepancy-found |
| [gNMI Subscription for YANG Data（ON_CHANGE / SAMPLE / TARGET_DEFINED）](gnmi-subscription-for-yang-data.md) | code-verified |
| [linkmgrd のデフォルトルート連動（DualToR mux 制御）](default-route.md) | code-verified |
| [クラスベース転送 (CBF) — DSCP/EXP→FC マップと CLASS_BASED_NEXT_HOP_GROUP](class-based-forwarding-enhancement.md) | code-verified |
| [プレフィックスルート方式の Mux ネイバ（Dual-ToR の状態遷移最適化）](prefix-based-mux-neighbors.md) | code-verified |
| [ルータインタフェース (RIF) カウンタ](router-interface-counters-in-sonic.md) | code-verified |
| [新 FRR-SONiC 通信チャネル（dplane_fpm_sonic モジュール）](new-frr-sonic-communication-channel.md) | code-verified |

<!-- glossary-links-injected: 6bc31d3f0d0b -->
