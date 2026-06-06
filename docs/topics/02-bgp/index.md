---
title: BGP と FRR 制御プレーン
description: BGP と FRR 制御プレーン — この章は、SONiC の BGP を「設定を書く場所」「FRR へ渡る経路」「ASIC に入るまでの経路」「運用中に見る場所」の順に読み直すための入口である。既存ページは HLD 単位で詳しいが、BGP を運用する人が最初に知りたい境界は HLD の境界ではない。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
keywords:
- BGP
- FRR
- bgpcfgd
- frrcfgd
- fpmsyncd
- ピアリング
- ルーティング
- ASN
- EBGP unnumbered
- route-map
related:
  cli:
  - config bgp
  - show bgp
  - show bfd
  - show ip
  - clear
  - config vrf
  - config vxlan
  config_db:
  - BGP_NEIGHBOR
  - BGP_AGGREGATE_ADDRESS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_PEER_RANGE
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_NEIGHBOR_AF
  yang:
  - sonic-bgp-global
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-aggregate-address
  - sonic-bgp-bbr
  - sonic-bgp-sentinel
---

# BGP と FRR 制御プレーン

この章は、[SONiC](../../reference/glossary.md#term-sonic) の [BGP](../../reference/glossary.md#term-bgp) を「設定を書く場所」「[FRR](../../reference/glossary.md#term-frr) へ渡る経路」「[ASIC](../../reference/glossary.md#term-asic) に入るまでの経路」「運用中に見る場所」の順に読み直すための入口である。既存ページは [HLD](../../reference/glossary.md#term-hld) 単位で詳しいが、BGP を運用する人が最初に知りたい境界は HLD の境界ではない。

主な問いは次の 4 つ。

- BGP neighbor、peer group、address family、policy はどこで設定し、誰が FRR に反映するのか。
- bgpd、[zebra](../../reference/glossary.md#term-zebra)、[fpmsyncd](../../reference/glossary.md#term-fpmsyncd)、[orchagent](../../reference/glossary.md#term-orchagent)、[syncd](../../reference/glossary.md#term-syncd) は経路処理でどこまで責任を持つのか。
- BGP loading optimization、PIC、Suppress FIB Pending は、どの遅さや不整合を減らす機能なのか。
- BMP、CiscoBgp4MIB、dynamic peer、FRR upgrade、FRR-SONiC 通信チャネル変更は運用上どこに効くのか。

## 読む順番

1. [概要](concept.md): SONiC の BGP 制御プレーンを、設定面と経路面に分けて見る。
2. [アーキテクチャ](architecture.md): bgpd/zebra から fpmsyncd、orchagent、ASIC までの経路フローを追う。
3. [設定](setup.md): [CONFIG_DB](../../reference/glossary.md#term-config_db)、CLI、[YANG](../../reference/glossary.md#term-yang) のどれを入口にするかを決める。
4. [運用](operations.md): 状態確認、BMP/MIB 監視、FIB 未導入時の切り分けを扱う。
5. [内部実装](internals.md): 大量経路ロード、PIC、Suppress FIB Pending、dynamic peer を比較する。
6. [発展トピック](advanced.md): VoQ、[BFD](../../reference/glossary.md#term-bfd) for BGP、[EVPN](../../reference/glossary.md#term-evpn) へ進む。

## 統合した既存ページ

この章は routing の HLD 派生ページ 20 件と reference ページ 19 件を横断している。細部のスキーマ、CLI、実装裏取りは各サブページ末尾の「関連ページ」から参照する。

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 229 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 184 | ✅ 完成 | code-verified | アーキテクチャ・データフロー |
| setup | 231 | ✅ 完成 | meta | セットアップ手順 |
| operations | 183 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 148 | ✅ 完成 | meta | 内部実装 |
| advanced | 101 | ✅ 完成 | meta | 発展トピック |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [BGP PIC（Prefix Independent Convergence / NHG 階層）](../../routing/bgp-prefix-independent-convergence-architecture-document.md)
- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](../../routing/bgpcfgd-dynamic-peer-modification-support.md)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../../routing/bfd-hw-offload-for-bgp-session.md)
- [BGP Loading Optimization（fpmsyncd flush / orchagent ring buffer / async sairedis）](../../routing/bgp-loading-optimization-for-sonic.md)
- [fpmsyncd NextHop Group 拡張（dplane_fpm_nl / NEXTHOP_GROUP_TABLE）](../../routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md)
- [NEXT_HOP_GROUP_TABLE による APP_DB ルートとネクストホップ分離](../../routing/routing-and-next-hop-table-enhancement.md)
- [SRv6 VPN（L3VPN over SRv6 と SRv6 Policy）](../../routing/srv6-vpn-hld.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)
- [EVPN Type-2 route が広告されない](../../reference/runbooks/evpn-type2-not-advertised.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [VRF / ECMP / RIB-FIB パイプライン](../04-vrf-ecmp/index.md)

**派生で読むべき章**

- [VXLAN / EVPN / VNET オーバーレイ](../03-vxlan-evpn/index.md)
- [SRv6 / MPLS / Path Tracing](../17-srv6-mpls/index.md)
- [Multi-ASIC / VOQ Chassis](../12-multi-asic-voq/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)

<!-- glossary-links-injected: ec18b66e3507 -->
