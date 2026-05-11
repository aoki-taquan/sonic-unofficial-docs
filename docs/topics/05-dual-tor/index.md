---
title: Dual-ToR と Mux 制御
description: "Dual-ToR と Mux 制御 — この章は、SONiC の Dual-ToR 構成で「2 台の ToR と 1 台のサーバ NIC の間にある mux を、どの状態情報で、どのように切り替えるのか」を読み解くための入口です。"
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
  - docs/categories/dual-tor.md
  - docs/overlay/active-active-dual-tor.md
  - docs/overlay/active-standby-dual-tor.md
  - docs/management/design-doc.md
  - docs/routing/default-route.md
  - docs/routing/prefix-based-mux-neighbors.md
  - docs/routing/multiple-nexthop-route-hld.md
  - docs/reference/cli/config-muxcable.md
  - docs/reference/cli/show-muxcable.md
  - docs/reference/config-db/mux-cable.md
  - docs/reference/config-db/peer-switch.md
  - docs/platform/icmp-hardware-offload.md
  - docs/routing/bfd-hw-offload.md
  - docs/routing/bfd-hw-offload-for-bgp-session.md
  - docs/overlay/dscp-remapping-for-tunnel-traffic.md
  - docs/architecture/dhcpv6-relay-agent.md
keywords:
  - Dual-ToR
  - Mux
  - active-standby
  - active-active
  - ToR
  - linkmgrd
  - orchagent
  - 冗長化
  - 切替
---

# Dual-ToR と Mux 制御

この章は、SONiC の Dual-ToR 構成で「2 台の ToR と 1 台のサーバ NIC の間にある mux を、どの状態情報で、どのように切り替えるのか」を読み解くための入口です。

既存ページは [HLD](../../reference/glossary.md#term-hld) 単位で分かれているため、ここでは運用者や設計者が実際に持つ質問の順に並べ直します。Active-Standby と Active-Active の選び方、`linkmgrd` / `MuxOrch` / `ycabled` / gRPC client の責務、`MUX_CABLE` の最小設定、障害時に見るべき CLI、そして [QoS](../../reference/glossary.md#term-qos) / DHCPv6 など周辺機能との境界を扱います。

## この章で答える質問

- Active-Active と Active-Standby Dual-ToR は何が違い、どちらを選ぶのか。
- `linkmgrd`、`MuxOrch`、`ycabled`、gRPC client はそれぞれ何を管理するのか。
- mux state、prefix-based neighbor、default route 連動はどの障害を避けるのか。
- ICMP hardware offload、[BFD](../../reference/glossary.md#term-bfd)、DSCP remap、DHCPv6 loopback は Dual-ToR でどこに関係するのか。

## 読み進め方

1. [概念](concept.md): Dual-ToR の問題設定と Active-Standby / Active-Active の違い。
2. [内部構造](internals.md): mux state machine、`linkmgrd`、`MuxOrch`、gRPC、経路連動の関係。
3. [設定](setup.md): `MUX_CABLE`、`PEER_SWITCH`、`config muxcable`、最小設定例。
4. [運用](operations.md): 状態確認、フェイルオーバー確認、ループ回避、プローブの見方。
5. [発展トピック](advanced.md): DSCP remap、DHCPv6 loopback、QoS / DHCP 章との境界。

## 関連ページ

- [Dual-ToR 関連](../../categories/dual-tor.md)
- [Active-Standby Dual ToR](../../overlay/active-standby-dual-tor.md)
- [Active-Active Dual ToR](../../overlay/active-active-dual-tor.md)
- [MUX_CABLE テーブル](../../reference/config-db/mux-cable.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)

<!-- glossary-links-injected: 8b515830f775 -->
