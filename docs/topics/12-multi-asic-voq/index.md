---
title: Multi-ASIC / VOQ Chassis
description: Multi-ASIC / VOQ Chassis — この章は、SONiC が「1 つの NOS インスタンスで複数 ASIC を、または複数 line card を 1 つの論理スイッチとして見せる」ための仕組みをまとめて読むための入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/platform/1-sonic-on-multi-asic-platforms.md
- docs/platform/voq-sonic.md
- docs/categories/multi-asic.md
- docs/acl-qos/distributed-forwarding-in-a-virtual-output-queue-voq-architecture.md
- docs/platform/fabric-port-support-on-sonic.md
- docs/platform/recirculation-port-support-on-voq-chassis.md
- docs/internals/support-redis-databases-in-multiple-namespaces.md
- docs/platform/multi-asic-single-json-configuration-design.md
- docs/platform/db-design-for-multi-asic-scenarios.md
- docs/platform/automatic-module-provisioning-for-chassis.md
- docs/platform/single-asic-voq-fixed-system-sonic.md
- docs/internals/aggregate-voq-counters-in-sonic.md
- docs/system/platform-monitor-design-for-multi-asic-platforms.md
- docs/system/platform-monitor-requirement-for-chassis-subsystem.md
- docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md
- docs/routing/bgp-setup-for-voq-chassis.md
- docs/switching/lag-on-distributed-voq-system.md
- docs/platform/everflow-support-on-voq-chassis.md
- docs/routing/reliable-tsa.md
- docs/system/multi-asic-warm-reboot.md
keywords:
- Multi-ASIC
- VOQ
- chassis
- voq fabric
- namespace
- linecard
- supervisor
- 分散ルーティング
- マルチASIC
related:
  cli:
  - config bgp
  - show bgp
  - show interfaces
  - config acl
  - config vlan
  - show acl
  - show platform
  config_db:
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP_AF
  - BGP_AGGREGATE_ADDRESS
  - BGP_NEIGHBOR_AF
  - BGP_PEER_GROUP
  - SNMP
  yang:
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-sentinel
---

# Multi-ASIC / VOQ Chassis

この章は、[SONiC](../../reference/glossary.md#term-sonic) が「1 つの NOS インスタンスで複数 [ASIC](../../reference/glossary.md#term-asic) を、または複数 line card を 1 つの論理スイッチとして見せる」ための仕組みをまとめて読むための入口です。既存ページは [Multi-ASIC](../../reference/glossary.md#term-multi-asic) namespace、[VOQ](../../reference/glossary.md#term-voq) chassis、Chassis DB、fabric / system port、distributed forwarding、line card provisioning、aggregate counter、entity MIB といった [HLD](../../reference/glossary.md#term-hld) 単位に分かれているため、ここでは pizza-box 1 ASIC を前提にしてきた読者が chassis に拡張するときの質問順に並べ直します。

Multi-ASIC は同じ筐体内の複数 ASIC を namespace で分け、各 ASIC を独立した network namespace + [Redis](../../reference/glossary.md#term-redis) インスタンスとして動かす設計です。VOQ chassis は、その Multi-ASIC を複数 line card にまたがって連結し、supervisor の Chassis DB と fabric ASIC を介して「distributed VOQ アーキテクチャ」として 1 つに見せます。single-ASIC fixed VOQ system は、その VOQ 機構を 1 ASIC pizza-box に閉じ込めた中間形態です。

## この章で答える質問

- Multi-ASIC namespace と VOQ chassis は同じ概念か、どこから別物になるのか。
- Chassis DB、system port、fabric port、recirculation port、line card provisioning はどうつながるか。
- 設定は ASIC ごとに別ファイルか、それとも 1 枚の JSON で済むか。
- supervisor と line card のどちらから何を見ればよいか。
- VOQ chassis の [BGP](../../reference/glossary.md#term-bgp)、[LAG](../../reference/glossary.md#term-lag)、Everflow、TSA、warm reboot はどの章で読むのか。
- single-ASIC fixed VOQ はどんな移行用途で使うのか。

## 読み進め方

1. [概念](concept.md): namespace、chassis、fabric、system port、distributed VOQ の用語整理。
2. [アーキテクチャ](architecture.md): Chassis DB と各 ASIC namespace の DB、distributed forwarding の流れ、fabric / recirculation port の役割。
3. [設定](setup.md): single JSON、`asic.conf`、Golden Config、module provisioning、single-ASIC fixed VOQ 設定。
4. [運用](operations.md): aggregate VOQ counter、PMON、Entity MIB、supervisor / line card 観点の確認順。
5. [発展トピック](advanced.md): VOQ BGP、distributed LAG、VOQ Everflow、TSA、Multi-ASIC warm reboot、各章への橋渡し。
6. [内部実装](internals.md): Chassis DB / namespace ごとの DB の整合、system port allocation、fabric reachability の実装視点。

## 関連ページ

- [SONiC on Multi-ASIC Platforms](../../platform/1-sonic-on-multi-asic-platforms.md)
- [VOQ SONiC](../../platform/voq-sonic.md)
- [Multi-ASIC カテゴリ](../../categories/multi-asic.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (151 行) | meta |
| setup | ✅ 完成 (232 行) | meta |
| operations | ✅ 完成 (217 行) | meta |
| internals | ✅ 完成 (140 行) | meta |
| advanced | ✅ 完成 (108 行) | meta |

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

- [単一 ASIC VoQ 固定システム（chassisdb.conf による is_voq_chassis 分岐）](../../platform/single-asic-voq-fixed-system-sonic.md)
- [Error Handling Framework 概念（ERROR_DB / SWSS_RC / 報告のみの責務）](../../architecture/error-handling-framework-in-sonic-concepts.md)
- [Error Handling Framework 制限事項と HLD との乖離（コア機構未実装 / CRM 代替）](../../architecture/error-handling-framework-in-sonic-limitations.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [Trap Flow Counter（Host I/F Trap 単位の Generic Counter 集計）](../../architecture/sonic-trap-flow-counter-design.md)
- [SAI 失敗ハンドリング（handleSai*Status virtual + ERROR_DB）](../../platform/hld-for-handling-sai-failures.md)
- [VOQ シャーシの Fabric ポート（fabric ASIC 管理 / link monitoring）](../../platform/fabric-port-support-on-sonic.md)

**関連トラブルシュート 5 件**

- [APP_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)
- [BGP と FRR 制御プレーン](../02-bgp/index.md)

**派生で読むべき章**

- [DASH と SmartSwitch](../13-dash-smartswitch/index.md)

**補完的に読む章**

- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Platform / Port / Optics / PHY](../14-platform-port-optics/index.md)

<!-- glossary-links-injected: 5c9b3765d470 -->
