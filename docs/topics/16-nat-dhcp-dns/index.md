---
title: NAT / DHCP Relay / Time-DNS Services
description: NAT / DHCP Relay / Time-DNS Services — この章は、SONiC が「edge / management 側で動く付帯サービス」と呼べる機能群、つまり NAT、DHCP relay と DHCP server、NTP / chrony / DNS、そして TWAMP Light や…
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/architecture/nat-in-sonic.md
- docs/architecture/dhcpv4-relay-agent.md
- docs/architecture/dhcpv6-relay-agent.md
- docs/routing/dhcp-relay-for-ipv6-hld.md
- docs/routing/dhcp-relay-per-interface-counter.md
- docs/management/ipv4-port-based-dhcp-server-in-sonic.md
- docs/management/dhcp-relay-v4-specify-gaaddr-as-primary-interface-s-gateway-explicitly.md
- docs/reference/cli/config-nat.md
- docs/reference/cli/show-nat.md
- docs/reference/cli/config-dhcp-relay.md
- docs/reference/config-db/nat.md
- docs/reference/config-db/dhcpv4-relay.md
- docs/reference/config-db/dhcp-server-ipv4.md
- docs/reference/yang/sonic-nat.md
- docs/reference/yang/sonic-dhcp-server.md
- docs/acl-qos/dhcp-dos-mitigation-in-sonic.md
- docs/system/sonic-network-time-protocol-ntp-client-configuration.md
- docs/system/sonic-migration-to-chrony.md
- docs/system/static-dns-configuration.md
- docs/reference/config-db/ntp-global.md
- docs/reference/config-db/ntp-server.md
- docs/reference/yang/sonic-ntp.md
- docs/reference/yang/sonic-dns.md
- docs/system/twamp-light-hld.md
- docs/architecture/1-udev-rules-design-for-terminal-server.md
keywords:
- NAT
- DHCP Relay
- DNS
- NTP
- Time service
- dhcrelay
- natsyncd
- natmgrd
- サービス
related:
  cli:
  - config nat
  - show nat
  - config acl
  - config interface
  - config qos
  - config vlan
  - config vrf
  config_db:
  - NAT
  - VLAN
  - COPP_GROUP
  - COPP_TRAP
  - ACL_RULE
  - DHCP_SERVER_IPV4
  - FEATURE
  yang:
  - sonic-nat
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-copp
  - sonic-dhcp-server
  - sonic-vrf
  - sonic-dns
---

# NAT / DHCP Relay / Time-DNS Services

この章は、[SONiC](../../reference/glossary.md#term-sonic) が「edge / management 側で動く付帯サービス」と呼べる機能群、つまり [NAT](../../reference/glossary.md#term-nat)、DHCP relay と DHCP server、NTP / chrony / DNS、そして TWAMP Light や terminal server のような測定・補助サービスをまとめて読むための入口です。これらは [BGP](../../reference/glossary.md#term-bgp) や [ACL](../../reference/glossary.md#term-acl) のように data plane の主役ではありませんが、ToR / management スイッチを「使える装置」にするための薄い層であり、container と daemon の境界、management [VRF](../../reference/glossary.md#term-vrf) との関係を把握しないと運用で迷います。

NAT は data plane に踏み込むがフローテーブル管理が中心、DHCP relay は L2/L3 broadcast を upstream へ橋渡しする agent、DHCP server は kea を内蔵してポート単位で leases を払い出す機能、time / DNS は OS レイヤ寄りの設定で management VRF 越しに通信する、というように責務がはっきり分かれます。章内のページでは、まずこれらを「どの container / daemon が処理するか」で並べ直します。

## この章で答える質問

- NAT、DHCPv4 relay、DHCPv6 relay、DHCP server は SONiC のどの container / daemon が処理するか。
- DHCPv4 / DHCPv6、per-interface counter、Option 82 / Option 79 はどう設定・監視するか。
- NTP / chrony / static DNS は management VRF とどう関係するか。
- DHCP DoS 緩和、giaddr 固定のような派生機能はどの層に乗っているか。
- TWAMP Light や terminal server はサービス系としてどこに置くか。

## 読み進め方

1. [概念](concept.md): edge service の範囲と、NAT / DHCP relay / DHCP server / time-DNS の責務分担。
2. [アーキテクチャ](architecture.md): `docker-nat`、`docker-dhcp-relay`、`docker-dhcp-server`、kea、chrony と packet flow。
3. [設定](setup.md): NAT、DHCP relay、DHCP server の [CONFIG_DB](../../reference/glossary.md#term-config_db) / CLI / [YANG](../../reference/glossary.md#term-yang) リファレンス。
4. [運用](operations.md): counter、DoS 緩和、service health の確認順序。
5. [発展トピック](advanced.md): NTP / chrony 移行、static DNS、TWAMP Light、terminal server udev。
6. [内部実装](internals.md): natsyncd / natorch / dhcp_relayd / kea-dhcp / chrony の責務分担と CONFIG_DB / [APPL_DB](../../reference/glossary.md#term-appl_db) / [SAI](../../reference/glossary.md#term-sai) への変換を実装側から見る。

## 関連ページ

- [NAT in SONiC](../../architecture/nat-in-sonic.md)
- [DHCPv4 Relay Agent](../../architecture/dhcpv4-relay-agent.md)
- [DHCPv6 Relay Agent](../../architecture/dhcpv6-relay-agent.md)
- [ポートベース IPv4 DHCP Server](../../management/ipv4-port-based-dhcp-server-in-sonic.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| advanced | 120 | ✅ 完成 | meta | 発展トピック |
| architecture | 90 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| concept | 187 | ✅ 完成 | meta | 概念・位置付け |
| internals | 128 | ✅ 完成 | meta | 内部実装 |
| operations | 215 | ✅ 完成 | meta | 運用・デバッグ |
| setup | 224 | ✅ 完成 | meta | セットアップ手順 |

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

- [SWSS docker warm restart（state restore / consistency / sync up）](../../system/sonic-swss-docker-warm-restart.md)
- [BUM ストームコントロール（PORT_STORM_CONTROL）](../../switching/sonic-bum-storm-control.md)
- [YANG モデル既知問題と検証](../../system/yang-model-issues-and-validation.md)
- [Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server）](../../system/smart-switch-ip-address-assignment.md)
- [SONiC Boot Chart（systemd-bootchart 統合）](../../system/sonic-boot-chart.md)
- [SONiC NTP client（chrony / NTP_SERVER / mgmt VRF）](../../system/sonic-network-time-protocol-ntp-client-configuration.md)
- [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](../../switching/add-support-for-vlan-interface-using-openconfig-yang.md)

**関連トラブルシュート 5 件**

- [DHCP Relay で IP が払い出されない](../../reference/runbooks/dhcp-relay.md)
- [PINS gRPC (P4Runtime) が応答しない](../../reference/runbooks/pins-grpc-unresponsive.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [ACL ルールが効かない / counter が増えない](../../reference/runbooks/acl-rule-no-hit.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [Dual-ToR と Mux 制御](../05-dual-tor/index.md)

**補完的に読む章**

- [ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)
- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
