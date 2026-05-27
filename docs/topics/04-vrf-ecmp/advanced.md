---
title: 発展トピックへの橋渡し
description: 発展トピックへの橋渡し — VRF / RIF / route / NHG の読み方を押さえると、周辺機能の設計意図が追いやすくなります。このページでは、章
  04 から次に読む候補を整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/routing/virtual-router-redundancy-protocol-adaptation-hld.md
- docs/architecture/sag-high-level-design-for-sonic.md
- docs/routing/reliable-tsa.md
related:
  cli:
  - config vlan
  - show vlan
  - config vnet
  - config snmp
  - config portchannel
  - config bgp
  - show bgp
  config_db:
  - VRF
  - VLAN
  - VNET
  - SNMP
  - MGMT_VRF_CONFIG
  - VLAN_SUB_INTERFACE
  - VLAN_INTERFACE
  yang:
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-vnet
  - sonic-snmp
  - sonic-portchannel
  - sonic-srv6
  - sonic-bgp-monitor
---

# 発展トピックへの橋渡し

[VRF](../../reference/glossary.md#term-vrf) / [RIF](../../reference/glossary.md#term-rif) / route / NHG の読み方を押さえると、周辺機能の設計意図が追いやすくなります。このページでは、章 04 から次に読む候補を整理します。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [architecture](architecture.md) と、area HLD の [sonic-vrf-support-design-spec-draft](../../routing/sonic-vrf-support-design-spec-draft.md), [sonic-management-vrf-design-document-201911-release](../../routing/sonic-management-vrf-design-document-201911-release.md), [sonic-weighted-ecmp](../../routing/sonic-weighted-ecmp.md) で完結する。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `config vrf` 系コマンド、[reference/config_db/VRF](../../reference/config-db/index.md), `MGMT_VRF_CONFIG`, `INTERFACE`, `ROUTE` に集約されている。
- **本ページ**は基本 VRF/RIF/route を押さえた読者向けに、[VRRP](../../reference/glossary.md#term-vrrp) / SAG / TSA / NHG scale / WCMP / VRF leaking / fine-grained ECMP といった発展領域だけを扱う。

## Fine-Grained ECMP と Weighted ECMP

`fine-grained-ecmp` HLD は、L4 ヘッダのハッシュ入力を変えずに、特定 nexthop bucket への偏りを管理者が制御するための仕組み。具体的には `FG_NHG_PREFIX`, `FG_NHG_MEMBER` テーブルで bucket → member の bind を細粒度に変更し、特定 server 群への traffic を warm-take-down できる。NHG bucket 数は power-of-two で、SAI `SAI_NEXT_HOP_GROUP_ATTR_HASH_BUCKET_COUNT` に直接対応する。

Weighted ECMP (`sonic-weighted-ecmp`) は member ごとに weight を持つ点が fine-grained と異なり、SAI 側で `SAI_NEXT_HOP_GROUP_TYPE_DYNAMIC_UNORDERED_ECMP` を要求するため platform 対応が分かれる。

## VRRP は interface と VRF の冗長化

VRRP は、複数ルータが 1 つの仮想 router address を共有し、Master 障害時に Backup が引き継ぐ L3 冗長プロトコルです。[SONiC](../../reference/glossary.md#term-sonic) では Ethernet、[VLAN](../../reference/glossary.md#term-vlan)、sub-interface、[PortChannel](../../reference/glossary.md#term-portchannel)、non-default VRF が関係します。

この章の前提で見るなら、VRRP は「どの L3 interface / VRF 上で VIP と VMAC を扱うか」「[FRR](../../reference/glossary.md#term-frr) vrrpd と [CONFIG_DB](../../reference/glossary.md#term-config_db) がどう連携するか」の機能です。詳細は [VRRP](../../routing/virtual-router-redundancy-protocol-adaptation-hld.md) を参照してください。

## SAG は VLAN RIF の gateway MAC を揃える

Static Anycast Gateway は、[EVPN](../../reference/glossary.md#term-evpn)/[VXLAN](../../reference/glossary.md#term-vxlan) fabric などで複数 leaf が同じ default gateway IP / MAC を提供するための仕組みです。L3 interface と RIF の MAC、IPv6 link-local の me-route 更新が関係します。

現行ページでは community master への取り込み状況に discrepancy があるため、利用前提ではなく設計理解として読みます。詳細は [SAG for SONiC](../../architecture/sag-high-level-design-for-sonic.md) を参照してください。

## TSA は経路広告を止めて traffic を逃がす

TSA は Traffic-Shift Away のための運用機能で、[BGP](../../reference/glossary.md#term-bgp) に route policy を適用して対象装置へ traffic が来ないようにします。FIB pipeline そのものではなく、RIB に入る前の制御プレーン運用に近い機能です。

VoQ Chassis では Supervisor と Line Card の TSA 状態同期が課題になります。詳細は [Reliable TSA](../../routing/reliable-tsa.md) を参照してください。

## 他章との境界

| 読みたいこと | 次に読む章 |
|--------------|------------|
| BGP が route を選ぶまで | BGP と FRR 制御プレーン |
| EVPN / [VNET](../../reference/glossary.md#term-vnet) / Overlay [ECMP](../../reference/glossary.md#term-ecmp) | VXLAN / EVPN / VNET |
| [SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) | Segment Routing / MPLS |
| counter や telemetry の全体 | Observability / Telemetry 系の章 |
| test plan や [VS](../../reference/glossary.md#term-vs) test | テスト計画の章 |

## 関連ページ

- [VRRP](../../routing/virtual-router-redundancy-protocol-adaptation-hld.md)
- [SAG for SONiC](../../architecture/sag-high-level-design-for-sonic.md)
- [Reliable TSA](../../routing/reliable-tsa.md)

## 発展トピック

VRF / NHG / route の基本動作を超えた領域では、scale 改善と障害収束の最適化が主題になる。

- **NHG ([Next Hop Group](../../reference/glossary.md#term-next-hop-group)) スケール拡張**: ECMP/WCMP の path 数を増やすほど [SAI](../../reference/glossary.md#term-sai) / [ASIC](../../reference/glossary.md#term-asic) のリソースを食う。SONiC では NHG を route 間で共有して resource 消費を抑えるが、shared NHG の更新中に flap が出ないよう [orchagent](../../reference/glossary.md#term-orchagent) が swap 戦略を持つ。
- **WCMP (Weighted ECMP)**: SAI の `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT` を使い、capacity の異なる link でも均等に近づける配分が可能。SONiC では特定 ASIC でのみ実用に乗っている段階。
- **VRF leaking**: 同一 SONiC 内で複数 VRF 間に route を leak する設計。FRR の `import vrf` 設定と SONiC の `VRF` テーブルの組み合わせで実現。route-target で leak 範囲を絞る。
- **管理用 VRF (mgmt VRF)**: `MGMT_VRF_CONFIG` で management 経路と data plane 経路を完全分離。telemetry / NTP / DNS / [SNMP](../../reference/glossary.md#term-snmp) の `bind-to-vrf` を確認する。
- **SAG / VRRP の組み合わせ**: SAG が default gateway 系の MAC を fabric 全体で揃える一方、VRRP は per-segment で master/backup を切り替える。両者は競合しうるので、deployment 単位で片方に寄せる。

## 既知の制約と回避方法

- **VRF 削除時の RIF cleanup race**: VRF を削除する直前まで他 orch が RIF を使っていると、[APPL_DB](../../reference/glossary.md#term-appl_db) / [ASIC_DB](../../reference/glossary.md#term-asic_db) に残骸が残る。手順としては「VRF 上の interface を先に外す」「BGP/static route を flush する」「最後に VRF を消す」を厳守する。
- **NHG resize 中の transient loss**: shared NHG を更新する瞬間に短い loss が発生しうる。重要 prefix では `bgp suppress-fib-pending` と PIC を組み合わせる。
- **mgmt VRF と DNS resolver**: glibc resolver の bind 先 source IP を mgmt VRF に固定する設定が抜けると DNS が data VRF に漏れる。`resolv.conf` と `ip vrf exec` を併用する。
- **VRRPv3 IPv6 の link-local 衝突**: VMAC を変更すると IPv6 link-local が再生成されない実装があり、ND が古い MAC を返す。`ip -6 neigh flush` 系で起こしなおす。

## 将来計画 / ロードマップ

- ECMP fast reroute と PIC の協調は継続テーマ。`bgp-pic` [HLD](../../reference/glossary.md#term-hld) と `nexthop-group-fast-failover` 系の提案が交差する。
- SAG の community master 取り込みは段階的で、ベンダー fork 側で先行する状況。SONiC main 側の [YANG](../../reference/glossary.md#term-yang) / orch 整備の進捗を `architecture/sag-high-level-design-for-sonic` の "Future Work" で追う。
- VRF レベルの metrics (per-VRF route count / drop / nexthop unreachable) は telemetry 章 ([09](../09-telemetry-snmp/index.md), [10](../10-gnmi-openconfig/index.md)) の OpenConfig schema 拡張に依存する。

## 関連 RFC / 仕様書

- [RFC 4364](https://datatracker.ietf.org/doc/html/rfc4364) — BGP/MPLS IP VPNs (VRF モデルの源流)
- [RFC 5798](https://datatracker.ietf.org/doc/html/rfc5798) — VRRPv3
- [RFC 7432](https://datatracker.ietf.org/doc/html/rfc7432) — EVPN (VRF leak の overlay 版)
- [RFC 2992](https://datatracker.ietf.org/doc/html/rfc2992) — ECMP hashing 議論
- [RFC 7196](https://datatracker.ietf.org/doc/html/rfc7196) — IS-IS Routing for Anycast (SAG 概念の参考)

## upstream 開発の最新動向

- `sonic-swss` の `vrforch` / `routeorch` で NHG 共有の最適化と memory 削減 PR が継続的に入っている。
- FRR の VRF leaking 周りは IPv6 source address selection と `set src` のバグ修正が時折入る。SONiC 側は FRR バージョン更新でこれを取り込む。
- mgmt VRF を前提とした `host-system` 系 daemon (chrony, snmpd, gnmi server) の bind 設定改善 PR が散発的にあり、deployment ガイドラインの変化につながる。

## トラブルシュート観点

- VRF 削除が hang する場合、`ip vrf show` と `redis-cli -n 4 hgetall "VRF|<name>"` の差分を確認する。RIF が残っているなら、対応 interface の `vrf_name` を unset してから削除する。
- ECMP path が偏るときは、ASIC hash seed (`SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_SEED`) と hash-field 設定を `redis-cli -n 1 hgetall "SAI_OBJECT_TYPE_HASH:..."` で確認。inner header をハッシュ入力に入れていない platform は ECMP 偏り易い。
- mgmt VRF からの telemetry が届かない場合、`ip vrf exec mgmt curl ...` で経路自体を切り分け、`gnmi-server` の `--bind-vrf` または `host-system` 起動引数で VRF 指定が抜けていないか確認する。

## 検証パスとラボ要件

- VRF leaking の検証は `sonic-mgmt` の `vrf` test suite で network namespace を分けたシナリオを再現できる。leak 経路の `next-hop-vrf <other>` 設定と FIB 上の経路存在を `show ip route vrf <name>` で確認する。
- WCMP の動作は `wcmp_manager` の weight 反映遅延を計測することで実機差を見える化できる。SAI vendor によっては bucket resize が atomic でなく数 ms の transient loss を伴う。

<!-- glossary-links-injected: 9fb3fca99a59 -->
