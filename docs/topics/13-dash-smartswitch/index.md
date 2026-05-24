---
title: DASH と SmartSwitch
description: DASH と SmartSwitch — この章は、SONiC で「NPU スイッチに DPU をぶら下げ、その上で DASH オーバーレイを処理する」SmartSwitch 構成を読み解くための入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/categories/dash.md
- docs/categories/smartswitch.md
- docs/overlay/sonic-dash-hld.md
- docs/overlay/dash-sonic-kvm.md
- docs/overlay/smartswitch-eni-based-forwarding.md
- docs/architecture/smart-switch-database-design.md
- docs/architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md
- docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md
- docs/acl-qos/dash-acl-tags.md
- docs/system/smart-switch-ip-address-assignment.md
- docs/management/smart-switch-gnmi-feedback-design-omit-in-toc.md
- docs/platform/smartswitch-pmon-high-level-design.md
- docs/system/smart-switch-reboot-high-level-design.md
- docs/platform/smartswitch-dpu-graceful-shutdown.md
- docs/system/independent-dpu-upgrade.md
- docs/management/gnoi-hld-for-system-apis.md
- docs/management/gnoi-hld-for-os-apis.md
keywords:
- DASH
- SmartSwitch
- DPU
- appliance
- ENI
- ACL flow
- high-availability
- smart NIC offload
related:
  cli:
  - config acl
  - show acl
  - config vnet
  - config bgp
  - show bgp
  - show platform
  - show feature
  config_db:
  - ACL_RULE
  - ACL_TABLE
  - VNET
  - FEATURE
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP_AF
  yang:
  - sonic-vnet
  - sonic-bgp-bbr
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-aggregate-address
---

# DASH と SmartSwitch

この章は、[SONiC](../../reference/glossary.md#term-sonic) で「[NPU](../../reference/glossary.md#term-npu) スイッチに [DPU](../../reference/glossary.md#term-dpu) をぶら下げ、その上で [DASH](../../reference/glossary.md#term-dash) オーバーレイを処理する」[SmartSwitch](../../reference/glossary.md#term-smartswitch) 構成を読み解くための入口です。

DASH 系と SmartSwitch 系の既存 [HLD](../../reference/glossary.md#term-hld) は、NPU 側 / DPU 側 / HA / 管理経路にまたがって分散しています。ここでは「NPU と DPU はどう役割を分けているのか」「コントローラから入れた設定はどの DB を通って DPU に届くのか」「HA フェイルオーバーや DPU の reboot / upgrade はどの daemon が動かすのか」という運用者・設計者の質問順に並べ直します。

## この章で答える質問

- DASH、DPU、SmartSwitch、[ENI](../../reference/glossary.md#term-eni) Based Forwarding はそれぞれ何を指しているのか。
- NPU 側 [Redis](../../reference/glossary.md#term-redis) と DPU 側 overlay Redis はどう分かれ、どう同期するのか。
- ENI ベース転送と DASH [ACL](../../reference/glossary.md#term-acl) タグはどの ACL レイヤに入るのか。
- SmartSwitch HA（HAMgrD）と DPU の reboot / upgrade / graceful shutdown はどの順序で動くのか。
- [gNMI](../../reference/glossary.md#term-gnmi) フィードバックと [gNOI](../../reference/glossary.md#term-gnoi) 系 API は SmartSwitch でどこに位置付けられるのか。

## 読み進め方

1. [概念](concept.md): DASH / DPU / SmartSwitch / ENI / HA の用語と位置付け。
2. [内部構造](internals.md): NPU-DPU DB アーキテクチャ、ENI ベース転送、DASH ACL タグ。
3. [設定](setup.md): DPU IP 割当、gNMI フィードバック、DASH KVM での検証。
4. [運用](operations.md): HA フェイルオーバー、PMON、reboot / shutdown / upgrade。
5. [発展トピック](advanced.md): gNOI 系との関係、[Multi-ASIC](../../reference/glossary.md#term-multi-asic) / [VOQ](../../reference/glossary.md#term-voq) との境界、管理章への橋渡し。

## 関連ページ

- [DASH 関連](../../categories/dash.md)
- [SmartSwitch 関連](../../categories/smartswitch.md)
- [SONiC-DASH アーキテクチャ概観](../../overlay/sonic-dash-hld.md)
- [Smart Switch のデータベース構成](../../architecture/smart-switch-database-design.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (213 行) | meta |
| setup | ✅ 完成 (298 行) | meta |
| operations | ✅ 完成 (266 行) | meta |
| internals | ✅ 完成 (183 行) | meta |
| advanced | ✅ 完成 (155 行) | meta |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: DASH と SmartSwitch の考え方](concept.md)
- [設定: DPU の IP 割当・gNMI 連携・KVM 検証](setup.md)
- [運用: HA / PMON / reboot / upgrade の運用](operations.md)
- [内部実装: NPU-DPU DB と ENI ベース転送の内部構造](internals.md)
- [発展トピック: gNOI 連携と他章との境界](advanced.md)

**関連する HLD 7 件**

- [DASH SONiC KVM（BMv2 ベース仮想 DPU）](../../overlay/dash-sonic-kvm.md)
- [単一 ASIC VoQ 固定システム（chassisdb.conf による is_voq_chassis 分岐）](../../platform/single-asic-voq-fixed-system-sonic.md)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)
- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../../overlay/smartswitch-eni-based-forwarding.md)
- [ICMP Hardware Offload（DualToR link prober の NPU 化）](../../platform/icmp-hardware-offload.md)
- [SONiC-DASH（Disaggregated APIs for SONiC Hosts）アーキテクチャ概観](../../overlay/sonic-dash-hld.md)
- [VXLAN / VNet 概念（VTEP + VNet + L2/L3 トンネル）](../../overlay/vxlan-sonic-concepts.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [SmartSwitch DPU が応答しない](../../reference/runbooks/smartswitch-dpu-unresponsive.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Multi-ASIC / VOQ Chassis](../12-multi-asic-voq/index.md)

<!-- glossary-links-injected: 3abb11a5818e -->
