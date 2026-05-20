---
title: L2 / VLAN / LAG / MC-LAG
description: L2 / VLAN / LAG / MC-LAG — この章は、SONiC を L2 switch として読むときに最初に迷う「VLAN、VLAN interface、switchport、sub-port、LAG、MC-LAG はどの順番で理解すればよいか」を整理する入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/switching/layer-2-forwarding-enhancements.md
- docs/switching/sonic-basic-l2-mode-test-plan.md
- docs/switching/switch-port-modes-and-vlan-cli-enhancement.md
- docs/switching/mclag-enhancements.md
- docs/switching/brief-introduction-of-iccp-code.md
- docs/switching/multiple-spanning-tree-protocol.md
- docs/switching/sonic-ip-lag-incremental-update.md
- docs/reference/cli/config-vlan.md
- docs/reference/cli/config-portchannel.md
- docs/reference/cli/config-interface.md
- docs/reference/config-db/vlan.md
- docs/reference/config-db/vlan-member.md
- docs/reference/config-db/vlan-interface.md
- docs/reference/config-db/vlan-sub-interface.md
- docs/reference/config-db/portchannel.md
- docs/reference/config-db/portchannel-member.md
- docs/reference/config-db/portchannel-interface.md
- docs/reference/config-db/port.md
- docs/reference/config-db/interface.md
- docs/reference/yang/sonic-vlan.md
- docs/reference/yang/sonic-vlan-sub-interface.md
- docs/reference/yang/sonic-portchannel.md
- docs/reference/yang/sonic-port.md
- docs/architecture/sonic-sub-port-interface-high-level-design.md
- docs/platform/sonictpidsettinghld1.md
- docs/reference/cli/show-vlan.md
- docs/reference/cli/show-mclag.md
- docs/switching/sonic-bum-storm-control.md
- docs/switching/link-event-damping-hld.md
- docs/switching/openconfig-support-for-portchannel-aggregate-interface.md
- docs/switching/add-support-for-vlan-interface-using-openconfig-yang.md
- docs/switching/lag-on-distributed-voq-system.md
- docs/switching/wake-on-lan-in-sonic.md
keywords:
- L2
- VLAN
- LAG
- MC-LAG
- teamd
- LACP
- bridge
- FDB
- MAC learning
related:
  cli:
  - config vlan
  - config portchannel
  - show vlan
  - config interface
  - show arp
  - show interfaces
  - show mclag
  config_db:
  - VLAN
  - VLAN_INTERFACE
  - PORTCHANNEL
  - VLAN_MEMBER
  - PORTCHANNEL_MEMBER
  - PORTCHANNEL_INTERFACE
  - VLAN_SUB_INTERFACE
  yang:
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-portchannel
  - sonic-mclag
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-global
---

# L2 / VLAN / LAG / MC-LAG

この章は、[SONiC](../../reference/glossary.md#term-sonic) を L2 switch として読むときに最初に迷う「[VLAN](../../reference/glossary.md#term-vlan)、VLAN interface、switchport、sub-port、[LAG](../../reference/glossary.md#term-lag)、MC-LAG はどの順番で理解すればよいか」を整理する入口です。

既存ページは [HLD](../../reference/glossary.md#term-hld)、CLI、[CONFIG_DB](../../reference/glossary.md#term-config_db)、[YANG](../../reference/glossary.md#term-yang) 参照が別々に並んでいます。ここでは、設計者や運用者が実際に持つ質問の順に、L2 forwarding の基本単位、VLAN と L3 SVI の境界、[PortChannel](../../reference/glossary.md#term-portchannel) と MC-LAG の責務、[FDB](../../reference/glossary.md#term-fdb) / STP / storm control の運用確認、OpenConfig や [VOQ](../../reference/glossary.md#term-voq) との接点を読み直します。

## この章で答える質問

- 物理ポートを L2 access / trunk として使う場合、どの CONFIG_DB テーブルが中心になるのか。
- VLAN interface と sub-port はどちらも dot1q を使うが、何が違うのか。
- PortChannel は VLAN メンバにも L3 interface にもなれるが、設定順序はどう考えるのか。
- MC-LAG / ICCP は通常の LAG と何が違い、どの状態を確認すべきか。
- MSTP、FDB flush、storm control、link event damping は L2 障害対応のどこに入るのか。
- OpenConfig VLAN / PortChannel、distributed VOQ LAG、Wake-on-LAN はこの章でどこまで扱うのか。

## 読み進め方

1. [概念](concept.md): VLAN、VLAN interface、sub-port、LAG、MC-LAG の違い。
2. [アーキテクチャ](architecture.md): CONFIG_DB から manager daemon、[APPL_DB](../../reference/glossary.md#term-appl_db)、[orchagent](../../reference/glossary.md#term-orchagent)、[SAI](../../reference/glossary.md#term-sai) へ流れる経路。
3. [設定](setup.md): VLAN / PortChannel / interface / sub-port / TPID の代表パターン。
4. [運用](operations.md): `show vlan`、`mclagdctl`、FDB、storm control、link damping の確認順。
5. [発展トピック](advanced.md): OpenConfig、distributed VOQ LAG、Wake-on-LAN、他章との境界。
6. [内部実装](internals.md): VlanMgr / teammgrd / PortsOrch / IntfMgr / FdbOrch の責務分担と APPL_DB / [STATE_DB](../../reference/glossary.md#term-state_db) の整合を実装側から見る。

## 関連ページ

- [L2 Forwarding 強化](../../switching/layer-2-forwarding-enhancements.md)
- [Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [MCLAG Enhancements](../../switching/mclag-enhancements.md)
- [CONFIG_DB: VLAN](../../reference/config-db/vlan.md)
- [CONFIG_DB: PORTCHANNEL](../../reference/config-db/portchannel.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (129 行) | meta |
| setup | ✅ 完成 (272 行) | meta |
| operations | ✅ 完成 (202 行) | meta |
| internals | ✅ 完成 (128 行) | meta |
| advanced | ✅ 完成 (107 行) | meta |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: L2 機能の考え方](concept.md)
- [アーキテクチャ: L2 のアーキテクチャ](architecture.md)
- [設定: L2 設定パターン](setup.md)
- [運用: L2 運用確認](operations.md)
- [内部実装](internals.md)
- [発展トピック: L2 発展トピック](advanced.md)

**関連する HLD 7 件**

- [MCLAG Enhancements（dynamic config / unique IP / isolation group / static MAC）](../../switching/mclag-enhancements.md)
- [ICCPd 内部構成（MC-LAG / MLACP FSM ファイル別マップ）](../../switching/brief-introduction-of-iccp-code.md)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](../../switching/openconfig-support-for-portchannel-aggregate-interface.md)
- [SONiC Basic L2 モードテストプラン（FDB / VLAN / SNMP の最小機能検証）](../../switching/sonic-basic-l2-mode-test-plan.md)
- [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)
- [L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）](../../switching/layer-2-forwarding-enhancements.md)
- [IP / LAG / MTU の Incremental Update（portmgrd / intfmgrd / teammgrd 分担）](../../switching/sonic-ip-lag-incremental-update.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](../../reference/runbooks/arp-entry-stuck.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [Platform / Port / Optics / PHY](../14-platform-port-optics/index.md)

**派生で読むべき章**

- [Dual-ToR と Mux 制御](../05-dual-tor/index.md)
- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [QoS / Buffer / PFC / Watermark](../08-qos-buffer/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
