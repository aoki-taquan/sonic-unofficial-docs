---
title: Overlay 発展トピック
description: Overlay 発展トピック — ここでは、基本の VXLAN / VNET / EVPN の延長に見えるが、別の前提や別の orch を持つ機能を整理します。設計検討では同じ
  overlay として並びますが、運用手順や実装成熟度は同一ではありません。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/routing/evpn-vxlan-multihoming.md
- docs/overlay/smartswitch-eni-based-forwarding.md
- docs/overlay/nvgre-tunnel-in-sonic.md
- docs/platform/subnet-decapsulation-with-sonic.md
- docs/overlay/vnet-local-endpoint-forwarding.md
related:
  cli:
  - config vlan
  - show vlan
  - config vnet
  - show bfd
  - show arp
  - show acl
  - config acl
  config_db:
  - SUBNET_DECAP
  - VNET
  - VLAN
  - VRF
  - NVGRE_TUNNEL
  - TUNNEL_DECAP_TABLE
  - VXLAN_TUNNEL_MAP
  yang:
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-vnet
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
---

# Overlay 発展トピック

ここでは、基本の [VXLAN](../../reference/glossary.md#term-vxlan) / [VNET](../../reference/glossary.md#term-vnet) / [EVPN](../../reference/glossary.md#term-evpn) の延長に見えるが、別の前提や別の orch を持つ機能を整理します。設計検討では同じ overlay として並びますが、運用手順や実装成熟度は同一ではありません。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と、area HLD の [vxlan-sonic](../../overlay/vxlan-sonic.md), [sonic-dash-hld](../../overlay/sonic-dash-hld.md), [evpn-vxlan-multihoming](../../routing/evpn-vxlan-multihoming.md) に集約されている。tunnel [orchagent](../../reference/glossary.md#term-orchagent) と FRR EVPN の協調は area HLD 側で詳細化されている。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config vxlan` / `config vnet` 系コマンド、[reference/config_db/VXLAN_TUNNEL](../../reference/config-db/index.md), `VNET`, `VNET_INTERFACE`, `EVPN_NVO` に集約されている。
- **本ページ** は基本 VXLAN/VNET/EVPN を踏まえた読者向けに、EVPN MH, NVGRE, Subnet decap, Overlay ECMP w/ BFD, DASH 連携といった発展領域だけを扱う。

## EVPN multihoming

EVPN multihoming は、host を複数 leaf に接続し、[BGP](../../reference/glossary.md#term-bgp)-EVPN の Type-1 / Type-4、ESI、DF election、split-horizon で重複転送とループを避ける機能です。通常の EVPN VXLAN が Type-2 / Type-5 で MAC/IP/prefix を配るのに対し、multihoming は Ethernet Segment の制御を追加します。

既存ページでは、`EVPN_ETHERNET_SEGMENT` や [EVPN-MH](../../reference/glossary.md#term-evpn-mh) 用 CLI / [YANG](../../reference/glossary.md#term-yang) が現行 master で確認できない可能性も示されています。利用判断では [FRR](../../reference/glossary.md#term-frr)、[SAI](../../reference/glossary.md#term-sai)、[ASIC](../../reference/glossary.md#term-asic)、[SONiC](../../reference/glossary.md#term-sonic) schema の対応状況を個別に確認してください。

## DASH / SmartSwitch 連携

[SmartSwitch](../../reference/glossary.md#term-smartswitch) [ENI](../../reference/glossary.md#term-eni) based forwarding は、ENI と [DPU](../../reference/glossary.md#term-dpu) の対応を [NPU](../../reference/glossary.md#term-npu) 側に理解させ、[ACL](../../reference/glossary.md#term-acl) の `REDIRECT` で local nexthop または tunnel nexthop へ送る設計です。VXLAN tunnel nexthop 表記を ACL action が解釈するため、VNET/VXLAN の tunnel nexthop 管理と接点があります。

VNET local endpoint forwarding は、DPU が local にいる場合に tunnel route ではなく通常 [ECMP](../../reference/glossary.md#term-ecmp) route を使う最適化です。failover 中の transient state では、tunnel decap 後のパケットを local nexthop へ redirect する高優先 ACL が使われます。

## NVGRE

NVGRE は VXLAN と同じく overlay encapsulation ですが、GRE と VSID を使います。SONiC の NVGRE [HLD](../../reference/glossary.md#term-hld) は decap 側を中心にしており、`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` と `nvgreorch` は VXLAN 系 orch とは別です。

VXLAN/VNET の章で一緒に読む価値があるのは、tenant ID を tunnel map で inner L2 domain に戻す考え方、ASIC tunnel resource、inner packet hashing の課題が似ているためです。EVPN control plane と一体に扱うべき機能ではありません。

## Subnet decap

Subnet decap は VXLAN overlay ではなく、[VLAN](../../reference/glossary.md#term-vlan) subnet 宛の [IPinIP](../../reference/glossary.md#term-ipinip) decap を自動生成して Netscan probe を処理する platform 機能です。`TUNNEL_DECAP_TABLE` や tunnel term という部品は共通ですが、tenant overlay を作るものではありません。

この機能を VXLAN のトラブルシュートに混ぜると判断を誤ります。見るべきポイントは `SUBNET_DECAP`、自動生成される `IPINIP_SUBNET` / `IPINIP_V6_SUBNET`、warm reboot 後の [APPL_DB](../../reference/glossary.md#term-appl_db) 再投入です。

## 関連ページ

- [EVPN VXLAN Multihoming](../../routing/evpn-vxlan-multihoming.md)
- [SmartSwitch ENI Based Forwarding](../../overlay/smartswitch-eni-based-forwarding.md)
- [VNET の Local Endpoint Forwarding](../../overlay/vnet-local-endpoint-forwarding.md)
- [NVGRE トンネル](../../overlay/nvgre-tunnel-in-sonic.md)
- [VLAN Subnet Decap](../../platform/subnet-decapsulation-with-sonic.md)

## 発展トピック

- **Overlay ECMP with [BFD](../../reference/glossary.md#term-bfd) monitoring**: VNET tunnel nexthop に BFD を貼ることで、underlay の障害を検出して nexthop group から外す。`overlay-ecmp-with-bfd-monitoring` HLD と `overlay-ecmp-enhancements` で扱う。VNET の規模が大きいときに収束時間を支配する要素になる。
- **EVPN Type-5 (IP Prefix Route)**: tenant [VRF](../../reference/glossary.md#term-vrf) の prefix を route target 経由で配る方法。Type-2 ベースの MAC/IP モデルと、Type-5 ベースの prefix モデルが共存するときの優先度を意識する。
- **[DSCP](../../reference/glossary.md#term-dscp) remapping for tunnel traffic**: outer DSCP を VNET 単位で書き換える機能。`overlay/dscp-remapping-for-tunnel-traffic` で扱われ、[QoS](../../reference/glossary.md#term-qos) 章 ([08 QoS](../08-qos-buffer/index.md)) の DSCP-to-TC マップと組み合わさる。
- **Symmetric IRB**: ingress / egress 双方で L3VNI を経由する設計。FRR 側設定と SONiC schema 双方で `VXLAN_TUNNEL_MAP` に L3 mapping を入れる。
- **VXLAN counters / drop visibility**: `COUNTERS_DB` に tunnel ごとの ingress/egress カウンタが入る。tunnel drop の切り分けは ASIC SAI 側のカウンタも併用する。

## 既知の制約と回避方法

- **EVPN multihoming (Type-1/Type-4) の SONiC 対応**: master でも YANG / orch / SAI 全層が揃っているかは ASIC 依存。production 投入前に `EVPN_ETHERNET_SEGMENT` の有無、FRR `evpn mh es` の動作、SAI の split horizon サポートを個別に確認する。
- **inner hashing が不十分なケース**: VXLAN inner header の 5-tuple がハッシュに入らない ASIC では、ECMP / [LAG](../../reference/glossary.md#term-lag) の偏りが出る。SAI hash setting (`SAI_SWITCH_ATTR_LAG_HASH_*`) と platform docs を照合する。
- **NVGRE と VXLAN の同居**: 同じ port での同時受信は ASIC によっては未対応。`nvgreorch` の HLD は decap 中心で、encap シナリオは限定されている。
- **Subnet decap を VNET の障害切り分けに使わない**: 名前が似ているが目的が違う。`SUBNET_DECAP` は VLAN subnet 宛 IPinIP の自動 decap で、VNET overlay とは別経路。

## 将来計画 / ロードマップ

- `evpn-vxlan-hld` には Type-2 MAC mobility、[ARP](../../reference/glossary.md#term-arp) suppression、ND suppression、Type-5 集約などの拡張が "Future Work" として継続議論されている。
- [DASH](../../reference/glossary.md#term-dash) / SmartSwitch との接続で、VNET tunnel nexthop と ENI redirect の責務分担が再整理されつつある。[13 DASH / SmartSwitch](../13-dash-smartswitch/index.md) の advanced と相互参照。
- IPv6 overlay (VXLAN over IPv6 underlay) のサポート拡大が議題。

## 関連 RFC / 仕様書

- [RFC 7348](https://datatracker.ietf.org/doc/html/rfc7348) — VXLAN
- [RFC 7432](https://datatracker.ietf.org/doc/html/rfc7432) — BGP [MPLS](../../reference/glossary.md#term-mpls)-Based Ethernet VPN
- [RFC 8365](https://datatracker.ietf.org/doc/html/rfc8365) — EVPN over VXLAN/NVGRE
- [RFC 9135](https://datatracker.ietf.org/doc/html/rfc9135) — Integrated Routing and Bridging in EVPN
- [RFC 9136](https://datatracker.ietf.org/doc/html/rfc9136) — IP Prefix Advertisement in EVPN
- [RFC 7637](https://datatracker.ietf.org/doc/html/rfc7637) — NVGRE
- [RFC 8926](https://datatracker.ietf.org/doc/html/rfc8926) — Geneve (将来 overlay 候補として参照)

## upstream 開発の最新動向

- FRR 側の EVPN 機能拡張に追従して `bgpcfgd` の Jinja2 と YANG モジュールが更新されることが多い。EVPN MH の SONiC 対応は段階的で、PR 単位で SAI 側依存を確認する必要がある。
- `sonic-swss` 配下の `vnetorch` / `vxlanorch` は tunnel nexthop group の扱いに関する PR が継続しており、scale 改善と memory 削減が主軸。
- SmartSwitch / DASH 関連で `vnet-local-endpoint-forwarding` のような近接最適化 HLD が追加されており、VNET の用途が DC overlay から DASH service へ広がっている。

## トラブルシュート観点

- [VTEP](../../reference/glossary.md#term-vtep) の `show vxlan tunnel` で remote VTEP が学習されない場合は、BGP-EVPN のセッションと Type-3 (Inclusive Multicast Ethernet Tag) の advertise 状況を `vtysh -c "show bgp l2vpn evpn"` で確認する。
- MAC 学習が片寄っている場合、Type-2 経路の VNI と local VLAN-VNI mapping の整合を `VXLAN_TUNNEL_MAP` で点検。FRR 側 `evpn vni <id>` も必須。
- inner hash の偏りは `show interfaces counters` の per-port 分布で見える。ASIC SAI の `SAI_SWITCH_ATTR_LAG_HASH_IPV4` に inner 5-tuple が含まれていない場合、SAI vendor docs と platform `hash.json` の見直しが必要。

## 検証パスとラボ要件

- KVM-based VS lab (`sonic-mgmt` ansible playbook 中の `vxlan-evpn` topology) で EVPN Type-2/3/5 の基本動作を再現できる。`virsh` で VTEP を 3 台立て、leaf-spine で `bgp l2vpn evpn` を運用する。
- DASH/SmartSwitch 系の検証は DPU sim (`sonic-dash-kvm` HLD 参照) を併用する。VNET tunnel と ENI redirect の責務分担を観察できる。

## 関連ページ (追補)

- [Overlay ECMP enhancements](../../routing/overlay-ecmp-enhancements.md)
- [Overlay ECMP with BFD monitoring](../../routing/overlay-ecmp-with-bfd-monitoring.md)
- [DSCP remapping for tunnel traffic](../../overlay/dscp-remapping-for-tunnel-traffic.md)
- [SONiC DASH HLD](../../overlay/sonic-dash-hld.md)
- [VXLAN SONiC concepts/internals/operations](../../overlay/vxlan-sonic.md)

<!-- glossary-links-injected: 7b27b638c4f3 -->
