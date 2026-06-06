---
title: VRF / ECMP / RIB-FIB パイプライン
description: VRF / ECMP / RIB-FIB パイプライン — SONiC の L3 転送を「VRF と interface を作る」「route が FRR から APPL_DB に来る」「orchagent が RIF / next hop / route object を ASIC に作る」「ECMP の種類を選ぶ」の順で読み直す章入口。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- VRF
- ECMP
- RIB
- FIB
- L3
- マルチパス
- next-hop
- default VRF
- 管理VRF
related:
  cli:
  - config vrf
  - config vrf add
  - config vrf del
  - config vrf bind
  - config vrf unbind
  - config route
  - config route add
  - config route del
  - show cli vrf
  - show cli mgmt-vrf
  - show cli ipv6 route
  - clear cli flowcnt-route
  config_db:
  - VRF
  - STATIC_ROUTE
  - FG_NHG
  - FG_NHG_PREFIX
  - FG_NHG_MEMBER
  - ROUTE_REDISTRIBUTE
  - LOOPBACK_INTERFACE
  yang:
  - sonic-vrf
  - sonic-mgmt_vrf
  - sonic-static-route
  - sonic-route-common
  - sonic-fine-grained-ecmp
  - sonic-interface
  - sonic-loopback-interface
---

# VRF / ECMP / RIB-FIB パイプライン

この章は、[SONiC](../../reference/glossary.md#term-sonic) の L3 転送を「[VRF](../../reference/glossary.md#term-vrf) と interface を作る」「route が [FRR](../../reference/glossary.md#term-frr) から [APPL_DB](../../reference/glossary.md#term-appl_db) に来る」「[orchagent](../../reference/glossary.md#term-orchagent) が [RIF](../../reference/glossary.md#term-rif) / next hop / route object を [ASIC](../../reference/glossary.md#term-asic) に作る」「[ECMP](../../reference/glossary.md#term-ecmp) の種類を選ぶ」という順番で読み直す入口です。

既存ページは VRF、static route、RIF counter、ECMP 拡張などの [HLD](../../reference/glossary.md#term-hld) 単位で分かれています。この章では、運用者や実装を追う読者が実際に持つ質問の順に並べ替え、詳細なスキーマやコード裏取りは各ページの関連リンクへ譲ります。

## この章で答える質問

- VRF、interface、static route、next hop group はどの順番で理解すればよいか。
- `CONFIG_DB` / FRR / `APPL_DB` / orchagent / `ASIC_DB` のどこで route の形が変わるか。
- ECMP、WCMP、Fine Grained ECMP、Ordered ECMP、Class Based Forwarding は何が違うか。
- route counter、RIF counter、flow counter、loopback action は運用中にどこを見るか。
- [VRRP](../../reference/glossary.md#term-vrrp)、SAG、TSA、path tracing のような周辺機能はこの章のどこまでを前提にしているか。

## 読む順番

1. [概念](concept.md): VRF、RIF、static route、IPv6 link-local、management VRF を L3 の読み順として整理する。
2. [アーキテクチャ](architecture.md): FRR から `ROUTE_TABLE`、`NEXT_HOP_GROUP_TABLE`、RouteOrch、[SAI](../../reference/glossary.md#term-sai) route object までの流れを追う。
3. [設定](setup.md): `config vrf`、`config route`、[CONFIG_DB](../../reference/glossary.md#term-config_db)、[YANG](../../reference/glossary.md#term-yang) を使った VRF 付き route の最小例を扱う。
4. [運用](operations.md): route / FIB / interface / RIF counter / route flow counter の確認順をまとめる。
5. [ECMP family](ecmp.md): ECMP、WCMP、FG ECMP、Ordered ECMP、Generic Hash、CBF の選び方を比較する。
6. [発展トピック](advanced.md): VRRP、SAG、TSA、他章への橋渡しを整理する。
7. [内部実装](internals.md): RouteOrch / NeighOrch / NhgOrch の責務と、ROUTE / NEIGH / NEXT_HOP_GROUP テーブルの整合を実装側から見る。

## 統合した既存ページ

この章は routing / architecture / internals / reference の既存ページ 32 件を横断しています。個別コマンド、テーブル、YANG、HLD の詳細は各サブページ末尾の「関連ページ」から参照してください。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 180 | ✅ 完成 | code-verified | 概念・位置付け |
| architecture | 75 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| setup | 264 | ✅ 完成 | meta | セットアップ手順 |
| operations | 186 | ✅ 完成 | meta | 運用・デバッグ |
| ecmp | 59 | ⚠️ プレースホルダ | meta | ECMP 詳細 |
| internals | 128 | ✅ 完成 | meta | 内部実装 |
| advanced | 100 | ✅ 完成 | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: L3 基盤と VRF](concept.md)
- [アーキテクチャ: RIB-FIB と Route Object 生成](architecture.md)
- [設定: VRF と Static Route の設定](setup.md)
- [運用: Route / Interface / Counter の確認](operations.md)
- [内部実装](internals.md)
- [発展トピック: 発展トピックへの橋渡し](advanced.md)

**関連する HLD 7 件**

- [VRF サポート（vrfmgrd / vrforch / FRR vrf-aware）](../../routing/sonic-vrf-support-design-spec-draft.md)
- [linkmgrd のデフォルトルート連動（DualToR mux 制御）](../../routing/default-route.md)
- [Fine Grained ECMP（FG_NHG / fgnhgorch）](../../routing/sonic-fine-grained-ecmp.md)
- [DHCPv6 リレー（dhcp-relay docker 内の dhcrelay -6 プロセス）](../../routing/dhcp-relay-for-ipv6-hld.md)
- [dual-tor mux 跨ぎの multi-nexthop route ループ回避（MuxOrch::updateRoute）](../../routing/multiple-nexthop-route-hld.md)
- [Management VRF 設計（201911 release / l3mdev + cgroups）](../../routing/sonic-management-vrf-design-document-201911-release.md)
- [Route Flow Counter（ROUTE_MATCH / Route Pattern Orch）](../../routing/sonic-route-flow-counter-design.md)

**関連トラブルシュート 5 件**

- [DHCP Relay で IP が払い出されない](../../reference/runbooks/dhcp-relay.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [ARP / Neighbor エントリが古い IP-MAC を保持し続ける](../../reference/runbooks/arp-entry-stuck.md)
- [BGP route が広告されない](../../reference/runbooks/bgp-route-not-advertised.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [BGP と FRR 制御プレーン](../02-bgp/index.md)
- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)
- [SRv6 / MPLS / Path Tracing](../17-srv6-mpls/index.md)

**補完的に読む章**

- [Multi-ASIC / VOQ Chassis](../12-multi-asic-voq/index.md)
- [NAT / DHCP Relay / Time-DNS Services](../16-nat-dhcp-dns/index.md)

<!-- glossary-links-injected: f08c435ee15d -->
