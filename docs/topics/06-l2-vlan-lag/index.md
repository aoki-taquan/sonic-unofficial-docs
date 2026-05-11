---
title: L2 / VLAN / LAG / MC-LAG
description: "L2 / VLAN / LAG / MC-LAG — この章は、SONiC を L2 switch として読むときに最初に迷う「VLAN、VLAN interface、switchport、sub-port、LAG、MC-LAG はどの順番で理解すればよいか」を整理する入口です。"
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
---

# L2 / VLAN / LAG / MC-LAG

この章は、SONiC を L2 switch として読むときに最初に迷う「VLAN、VLAN interface、switchport、sub-port、LAG、MC-LAG はどの順番で理解すればよいか」を整理する入口です。

既存ページは HLD、CLI、CONFIG_DB、YANG 参照が別々に並んでいます。ここでは、設計者や運用者が実際に持つ質問の順に、L2 forwarding の基本単位、VLAN と L3 SVI の境界、PortChannel と MC-LAG の責務、FDB / STP / storm control の運用確認、OpenConfig や VOQ との接点を読み直します。

## この章で答える質問

- 物理ポートを L2 access / trunk として使う場合、どの CONFIG_DB テーブルが中心になるのか。
- VLAN interface と sub-port はどちらも dot1q を使うが、何が違うのか。
- PortChannel は VLAN メンバにも L3 interface にもなれるが、設定順序はどう考えるのか。
- MC-LAG / ICCP は通常の LAG と何が違い、どの状態を確認すべきか。
- MSTP、FDB flush、storm control、link event damping は L2 障害対応のどこに入るのか。
- OpenConfig VLAN / PortChannel、distributed VOQ LAG、Wake-on-LAN はこの章でどこまで扱うのか。

## 読み進め方

1. [概念](concept.md): VLAN、VLAN interface、sub-port、LAG、MC-LAG の違い。
2. [アーキテクチャ](architecture.md): CONFIG_DB から manager daemon、APPL_DB、orchagent、SAI へ流れる経路。
3. [設定](setup.md): VLAN / PortChannel / interface / sub-port / TPID の代表パターン。
4. [運用](operations.md): `show vlan`、`mclagdctl`、FDB、storm control、link damping の確認順。
5. [発展トピック](advanced.md): OpenConfig、distributed VOQ LAG、Wake-on-LAN、他章との境界。
6. [内部実装](internals.md): VlanMgr / PortChannelMgr / IntfMgr / FdbOrch の責務分担と APPL_DB / STATE_DB の整合を実装側から見る。

## 関連ページ

- [L2 Forwarding 強化](../../switching/layer-2-forwarding-enhancements.md)
- [Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [MCLAG Enhancements](../../switching/mclag-enhancements.md)
- [CONFIG_DB: VLAN](../../reference/config-db/vlan.md)
- [CONFIG_DB: PORTCHANNEL](../../reference/config-db/portchannel.md)

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

