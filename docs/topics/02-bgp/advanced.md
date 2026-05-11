---
title: 発展トピック
description: 発展トピック — この章の基本経路を押さえた後は、VoQ、BFD、EVPN の順に読むと BGP が他章へどうつながるかが見える。いずれも
  BGP 単体の話ではなく、シャーシ構成、障害検出、overlay control plane と結びつく。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show bgp
  - show bfd
  - config bgp
  - config vrf
  - config vxlan
  config_db:
  - VRF
  - BGP_PEER_RANGE
  - BGP_NEIGHBOR
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  - BGP_AGGREGATE_ADDRESS
  yang:
  - sonic-srv6
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
---

# 発展トピック

この章の基本経路を押さえた後は、VoQ、[BFD](../../reference/glossary.md#term-bfd)、[EVPN](../../reference/glossary.md#term-evpn) の順に読むと [BGP](../../reference/glossary.md#term-bgp) が他章へどうつながるかが見える。いずれも BGP 単体の話ではなく、シャーシ構成、障害検出、overlay control plane と結びつく。

## VoQ シャーシの BGP

VoQ シャーシでは、iBGP full mesh、addpath、multipath-relax、再帰解決など、単体 ToR より BGP 設定の前提が増える。[ECMP](../../reference/glossary.md#term-ecmp) 整合性を保つための設定が重要で、minigraph や [CONFIG_DB](../../reference/glossary.md#term-config_db) スキーマ拡張も関わる。詳細は [VoQ シャーシでの BGP 構成](../../routing/bgp-setup-for-voq-chassis.md) を参照する。

## BFD for BGP

BFD は BGP の keepalive より速く failure を検出するための補助である。BGP セッション向け BFD hardware offload では、bfdsyncd、local discriminator、remote 情報、IPv6 link-local、scale/default 値が論点になる。BGP PIC の検出契機としても BFD は重要である。詳細は [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md) を参照する。

## EVPN/VXLAN への接続

EVPN/[VXLAN](../../reference/glossary.md#term-vxlan) では [FRR](../../reference/glossary.md#term-frr) BGP-EVPN が Type-2/Type-5 route を扱い、VTEP、[VRF](../../reference/glossary.md#term-vrf)、VXLAN tunnel、symmetric IRB とつながる。underlay の BGP と overlay の BGP-EVPN を混同しないことが重要である。この章で扱った FRR、route-map、VRF、経路反映の考え方は EVPN 章の前提になる。詳細は [EVPN VXLAN](../../routing/evpn-vxlan-hld.md) を参照する。

## 関連ページ

- [VoQ シャーシでの BGP 構成](../../routing/bgp-setup-for-voq-chassis.md)
- [BGP セッション向け BFD ハードウェアオフロード](../../routing/bfd-hw-offload-for-bgp-session.md)
- [EVPN VXLAN](../../routing/evpn-vxlan-hld.md)

## 発展トピック

基本の peer/policy 設定を超えた領域では、SONiC は FRR の機能を [Redis](../../reference/glossary.md#term-redis) スキーマ経由で順次取り込んでいる。代表的なものを挙げる。

- **BGP Suppress FIB Pending**: FIB 未投入の prefix を peer に広告しないことで、ASIC が経路を持っていない状態で advertise してトラフィックブラックホールになるのを防ぐ。SONiC では `bgpcfgd` テンプレートと FRR の `bgp suppress-fib-pending` を組み合わせる。
- **BGP PIC (Prefix Independent Convergence) Core/Edge**: edge link 障害時の収束を nexthop group レベルで行い、prefix 数に依存しない切替を実現する。SONiC では nexthop group 構造 (`NEXT_HOP_GROUP_TABLE`) と [orchagent](../../reference/glossary.md#term-orchagent) の対応で表現される。
- **BMP (BGP Monitoring Protocol, RFC 7854)**: FRR の `bmpd` を Redis 経由で利用し、Adj-RIB-In / Adj-RIB-Out を外部 collector に流す。複数 station への並走 export を SONiC schema が `BGP_BMP` で表現する。
- **Dynamic Neighbor / Listen Range**: 大規模 ToR で peer 数を事前列挙したくない場合に有効。[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) で `BGP_PEER_RANGE` を組み立てる流れがある。
- **大規模経路ロード最適化**: `bgp-loading-optimization` [HLD](../../reference/glossary.md#term-hld) が、起動直後の peer 受信を加速するための queue tuning と `bgpd` の起動引数を扱う。経路投入のスループットが warm/cold reboot の収束時間を支配する。

## 既知の制約と回避方法

- **bgpcfgd テンプレート差分が見えにくい**: `/etc/sonic/frr/*.j2` をベースに `vtysh -c "show running-config"` で実際の FRR 設定を確認する。CONFIG_DB の `BGP_NEIGHBOR` だけ見ても FRR 側の最終形は分からないので、両方を照合する。
- **graceful restart と FRR upgrade の組み合わせ**: FRR メジャー版アップグレードでは GR 互換性が保証されない場合がある。`docker-fpm-frr` の再起動と warm reboot の境界を意識し、可能なら同じ FRR バージョン同士の peer に揃える。
- **multipath relax と AS path 比較の落とし穴**: `bestpath as-path multipath-relax` を有効にしないと iBGP 経路の ECMP が成立しないケースがある。検証は `show bgp ipv4 unicast <prefix>` で multipath 印を確認するのが速い。
- **BFD と BGP keepalive の二重判定**: BFD hardware offload を使うときは BGP keepalive を緩めにし、BFD で先に倒す設計にする。両方を短くすると flap が増える。

## 将来計画 / ロードマップ

- FRR と SONiC の通信チャネルは長らく [zebra](../../reference/glossary.md#term-zebra) [FPM](../../reference/glossary.md#term-fpm) (`fpmsyncd`) 経由だが、`frr-zebra-dplane-sonic` の議論が継続しており、[SAI](../../reference/glossary.md#term-sai) に近い形での経路 push が将来テーマになっている。
- IETF SR-[MPLS](../../reference/glossary.md#term-mpls) / [SRv6](../../reference/glossary.md#term-srv6) の FRR 対応が進むなかで、SONiC 側の `srv6orch` と BGP signaling の統合は [17 SRv6 / MPLS](../17-srv6-mpls/index.md) の発展トピックと交差する。
- BMP の Local-RIB / Loc-RIB monitoring (RFC 9069) は FRR 側で順次入っており、SONiC schema 拡張が見込まれる。

## 関連 RFC / 仕様書

- [RFC 4271](https://datatracker.ietf.org/doc/html/rfc4271) — BGP-4 本体
- [RFC 7911](https://datatracker.ietf.org/doc/html/rfc7911) — Add-Path
- [RFC 4456](https://datatracker.ietf.org/doc/html/rfc4456) — Route Reflector
- [RFC 7854](https://datatracker.ietf.org/doc/html/rfc7854) / [RFC 9069](https://datatracker.ietf.org/doc/html/rfc9069) — BMP / Loc-RIB
- [RFC 5880](https://datatracker.ietf.org/doc/html/rfc5880) — BFD
- [RFC 7432](https://datatracker.ietf.org/doc/html/rfc7432) / [RFC 9136](https://datatracker.ietf.org/doc/html/rfc9136) — EVPN / IP Prefix Route

## upstream 開発の最新動向

- [sonic-buildimage](../../reference/glossary.md#term-sonic-buildimage) の `dockers/docker-fpm-frr` 配下では FRR バージョン更新と graceful restart 周りの修正が継続している。FRR バージョンを上げる PR は warm reboot の影響範囲が広いので CI matrix を確認する。
- `sonic-bgpcfgd` ([sonic-swss-common](../../reference/glossary.md#term-sonic-swss-common) 配下) で BGP テンプレートの [YANG](../../reference/glossary.md#term-yang) 化が進んでおり、`sonic-bgp-*` の YANG モジュールに合わせて Jinja2 が縮小される傾向。
- 大規模経路下の起動時間短縮を狙った PR が `bgp-loading-optimization` 関連で複数 merge されており、`zebra` の FPM queue サイズや `bgpd` の `bgp listen limit` チューニングが議題になりやすい。

<!-- glossary-links-injected: 8214fd17dd58 -->
