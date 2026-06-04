---
title: gNMI / gNOI / OpenConfig / YANG
description: gNMI / gNOI / OpenConfig / YANG — この章は、SONiC の「モデル駆動管理」を、リクエストが入る入口から ConfigDB に到達するまでの順で読み直すための入口である。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- gNMI
- gNOI
- OpenConfig
- YANG
- telemetry
- northbound API
- gnmi-server
- Subscribe
- Set/Get
related:
  cli:
  - config bgp
  - show bgp
  - config vlan
  - show vlan
  - config portchannel
  - config qos
  - show nat
  config_db:
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_GROUP_AF
  - VLAN
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP
  - TELEMETRY
  yang:
  - sonic-bgp-global
  - sonic-bgp-peergroup
  - sonic-bgp-bbr
  - sonic-bgp-monitor
  - sonic-bgp-peerrange
  - sonic-bgp-aggregate-address
  - sonic-port
---

# gNMI / gNOI / OpenConfig / YANG

この章は、[SONiC](../../reference/glossary.md#term-sonic) の「モデル駆動管理」を、リクエストが入る入口から ConfigDB に到達するまでの順で読み直すための入口である。既存ページは [HLD](../../reference/glossary.md#term-hld) 単位で書かれており、Translib、Transformer、[gNMI](../../reference/glossary.md#term-gnmi) server、[gNOI](../../reference/glossary.md#term-gnoi) service が別の文書に分かれている。運用者・開発者が最初に知りたい境界は、どのプロトコル/モデルが何を直接いじっているか、という一点に集約される。

主な問いは次の 4 つ。

- REST / gNMI / Translib / Transformer はどの層で [CONFIG_DB](../../reference/glossary.md#term-config_db) に到達するのか。
- OpenConfig [YANG](../../reference/glossary.md#term-yang) と SONiC native YANG はいつ使い分けるのか。
- gNOI System / OS / File / Healthz は SONiC のどの service を呼んでいるのか。
- gNSI、master arbitration、save-on-set、dial-out subscription は運用上どこで効くのか。

## 読む順番

1. [概要](concept.md): Management Framework の全体像、gNMI / REST / CLI の位置付け、OpenConfig と SONiC YANG の使い分けを整理する。
2. [アーキテクチャ](architecture.md): gNMI server から Translib、Transformer、YANG validation、CONFIG_DB までの request flow を mermaid で追う。
3. [設定](setup.md): gNMI Get / Set / Subscribe、OpenConfig interface / [VLAN](../../reference/glossary.md#term-vlan) / [PortChannel](../../reference/glossary.md#term-portchannel) / [BGP](../../reference/glossary.md#term-bgp) の典型例。
4. [運用](operations.md): master arbitration、save-on-set、dial-out telemetry、subscription の競合制御と永続化。
5. [gNOI / gNSI](gnoi-gnsi.md): System、OS、File、Factory Reset、Healthz、gNSI の API と SONiC service の対応表。
6. [YANG リファレンス](yang-reference.md): 機能章別の YANG モジュール参照表。
7. [内部実装](internals.md): gNMI server / Translib / Transformer / [sonic-mgmt](../../reference/glossary.md#term-sonic-mgmt)-common の責務分担と、YANG → ABNF/CONFIG_DB 変換を実装側から見る。
8. [発展トピック](advanced.md): dial-out telemetry、master arbitration、gNSI、save-on-set、他章との境界。

## 統合した既存ページ

この章は management の HLD 派生ページ 14 件、system の telemetry 関連 2 件、switching の OpenConfig 関連 2 件、routing の subscription 関連 2 件、categories の入口 1 件、reference の YANG 参照を横断している。細部のスキーマ・操作・実装裏取りは各サブページ末尾の「関連ページ」から参照する。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 140 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 69 | ⚠️ プレースホルダ | code-verified | アーキテクチャ・データフロー |
| setup | 208 | ✅ 完成 | meta | セットアップ手順 |
| operations | 256 | ✅ 完成 | code-verified | 運用・デバッグ |
| internals | 126 | ✅ 完成 | meta | 内部実装 |
| gnoi-gnsi | 53 | ⚠️ プレースホルダ | meta | gNOI / gNSI API |
| yang-reference | 35 | ⚠️ プレースホルダ | meta | YANG リファレンス |
| advanced | 74 | ⚠️ プレースホルダ | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック: gNMI / OpenConfig の発展トピック](advanced.md)

**関連する HLD 7 件**

- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../../management/sonic-nos-configuration-methods.md)
- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../../management/sonic-config-update-validation-via-yang.md)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../../management/openconfig-support-for-ethernet-interfaces.md)
- [Redis Client Manager（RCM: connection pool / transactional client）](../../management/redis-client-manager-rcm-hld.md)
- [SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携）](../../management/sonic-gnmi-server-interface-design.md)
- [gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli）](../../management/gnmi-usage.md)
- [gNOI Healthz API（Get / Acknowledge / Artifact + DBUS host service）](../../management/gnoi-hld-for-healthz-api.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [show interfaces counters が突然リセットされる](../../reference/runbooks/interface-counters-reset.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)

**派生で読むべき章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)

**補完的に読む章**

- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
