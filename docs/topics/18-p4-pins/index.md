---
title: P4 / PINS / Programmable Pipeline
description: 'P4 / PINS / Programmable Pipeline — この章は、SONiC を P4Runtime ベースの SDN コントローラから直接プログラムする ための仕組み（PINS: P4 Integrated Network Stack）をまとめて読むための入口です。'
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/management/pins-hld.md
- docs/management/p4rt-application-hld.md
- docs/management/p4rt-read-cache-hld.md
- docs/internals/p4-orchagent.md
- docs/management/packetio.md
- docs/management/send-to-ingress-hld.md
- docs/management/sonic-management-framework.md
- docs/management/gnmi-usage.md
keywords:
- P4
- PINS
- P4Runtime
- programmable pipeline
- PINS Infra
- p4rt
- SDN
- match-action
related:
  cli:
  - config acl
  - show acl
  - show platform
  - config bgp
  - config route
  - config vrf
  - show bgp
  config_db:
  - CRM
  - ACL_RULE
  - ACL_TABLE
  - COPP_GROUP
  - COPP_TRAP
  - DEVICE_METADATA
  - P4RT_TABLE
  yang:
  - sonic-crm
  - sonic-copp
  - sonic-bgp-bbr
  - sonic-bgp-device-global
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-neighbor
---

# P4 / PINS / Programmable Pipeline

この章は、SONiC を **P4Runtime ベースの SDN コントローラから直接プログラムする** ための仕組み（[PINS](../../reference/glossary.md#term-pins): P4 Integrated Network Stack）をまとめて読むための入口です。PINS は SONiC の従来パス（[BGP](../../reference/glossary.md#term-bgp) / [FRR](../../reference/glossary.md#term-frr) / [orchagent](../../reference/glossary.md#term-orchagent) 群）を残したまま、opt-in の外部チャネルで forwarding を書き換える設計のため、関連コンポーネントが管理面、orchagent、CPU パケット注入と複数章にまたがります。ここでは読み手の質問順に並べ直し、既存ページへリンクで誘導します。

PINS の中心は 4 点です。コントローラと話す **P4RT App**（gRPC port 9559）、それを [SAI](../../reference/glossary.md#term-sai) に翻訳する **P4Orch**（orchagent 内の同期 manager 群）、Read を高速化する **table_entry_cache_（entity_cache_）**、CPU と ASIC の間でパケットを流す **PacketIO + send_to_ingress**。これらは [APPL_DB](../../reference/glossary.md#term-appl_db) / APPL_STATE_DB / SAI hostif / generic netlink といった既存の SONiC 部品の上に乗っています。

## この章で答える質問

- PINS、P4Runtime App、P4Orch、PacketIO はどの関係か。
- P4Runtime の Read cache は何を最適化しているか。
- Send to Ingress と PacketIO は CPU packet injection としてどう違うか。
- P4 系ページは [gNMI / SDN 管理章](../../management/sonic-management-framework.md) とどう接続するか。

## 読み進め方

1. [概念](concept.md): PINS が何を opt-in で足すのか、SAI pipeline を P4 で表す意味。
2. [アーキテクチャ](architecture.md): P4RT App、P4Orch、APPL_DB / APPL_STATE_DB の流れ。
3. [設定](setup.md): P4RT サービス、controller 接続、`SEND_TO_INGRESS_PORT` の最小構成。
4. [運用](operations.md): PacketIO 経路の確認、Read cache の挙動、Send to Ingress の使い分け。
5. [内部実装](internals.md): P4Orch の Manager 群、`P4OidMapper`、同期書き込みと APPL_STATE_DB。
6. [発展トピック](advanced.md): [gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig との接続、HashOrch [HLD](../../reference/glossary.md#term-hld) と実装の乖離。

## 関連ページ

- [PINS（P4 Integrated Network Stack / SDN 制御 SONiC）](../../management/pins-hld.md)
- [P4RT アプリケーション（gRPC port 9559）](../../management/p4rt-application-hld.md)
- [P4Orch（PINS の P4Runtime 用 orchagent / 同期書き込み）](../../internals/p4-orchagent.md)
- [P4RT App の Read キャッシュ](../../management/p4rt-read-cache-hld.md)
- [P4Runtime PacketIO（generic netlink + send_to_ingress）](../../management/packetio.md)
- [Send to Ingress（CPU から ingress pipeline へパケット注入する hostif）](../../management/send-to-ingress-hld.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)
- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)

**派生で読むべき章**

- [DASH と SmartSwitch](../13-dash-smartswitch/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [SRv6 / MPLS / Path Tracing](../17-srv6-mpls/index.md)
- [Build / Packaging / Application Extension](../19-build-packaging/index.md)

<!-- glossary-links-injected: 9d7f47a8f2d1 -->
