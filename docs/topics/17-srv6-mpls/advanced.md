---
title: 発展トピック
description: "発展トピック — base 機能の上で広がる SRv6 / MPLS / Path Tracing 関連のトピックを、他章へのリンクと一緒にまとめます。"
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/srv6-vpn-hld.md
  - docs/routing/evpn-vxlan-hld.md
  - docs/routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md
---

# 発展トピック

base 機能の上で広がる [SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) / Path Tracing 関連のトピックを、他章へのリンクと一緒にまとめます。

## EVPN / BGP との接続

SRv6 と [EVPN](../../reference/glossary.md#term-evpn)-[VXLAN](../../reference/glossary.md#term-vxlan) は「IPv6 underlay の上で L2/L3 サービスを運ぶ」点で目的が重なる領域があります。SONiC では現状、EVPN は VXLAN encap が中心で、SRv6 を underlay にする実装は [HLD](../../reference/glossary.md#term-hld) レベルでも限定的です。[BGP](../../reference/glossary.md#term-bgp) 系の SRv6 family（BGP-LU / SR-MPLS / SRv6 L3VPN）を扱う場合は、[FRR](../../reference/glossary.md#term-frr) の SRv6 制御プレーン側の対応状況を最初に確認します。

- L3VPN over SRv6 を運用するには、FRR で SRv6 L3VPN family を有効化し、SONiC 側で `srv6orch` の VPN 経路（`srv6_prefix_agg_id_table_`、`vpn_sid`）が programming されることを確認します（[内部実装](internals.md) を参照）。
- EVPN-VXLAN の章は [03 VXLAN-EVPN](../03-vxlan-evpn/index.md) を参照してください。EVPN over SRv6 を試す場合の本章との接点は、VPN SID の運用と EVPN type-5 route の対応関係です。

## FRR の SRv6 統一管理

`sonic-frr-bgp-extended-unified-configuration-management-framework.md` で議論されている統一管理フレームワークは、[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) / frrcfgd の handler 群を再整理し、SRv6 / MPLS / EVPN を含む BGP 拡張の設定面を統一する方向にあります。Static SID は `SRv6Mgr` の vtysh 経由ですが、将来的に動的 SRv6（FRR の `segment-routing srv6` 設定の自動化）も同じ枠組みに乗ることが想定されます。

## SRv6 base HLD の後続 phase

SRv6 base HLD は Phase 1 として `END` / `END.DT46` / `H.Encaps.Red` を実装し、後続として次の項目が予定されています。

- `H.Encaps`（reduced でない通常 encap）
- `END.B6.Encaps[.Red]`（Binding SID）
- `END.X`（Adj SID） — 一部は SID L3Adj HLD で実装済み
- HMAC（SRH integrity）
- sBFD（segment routing BFD）
- anycast SID
- MySID counter

これらは段階的に `srv6orch` と [SAI](../../reference/glossary.md#term-sai) に追加されるため、運用設計時には「自社が依存する behavior が現在の master にあるか」をコード位置（[内部実装](internals.md)）で確認します。

## MPLS の動的シグナリング

LDP / RSVP-TE / SR-MPLS のような動的シグナリングは、master 時点では FRR 側機能に依存します。SONiC 側は `LABEL_ROUTE_TABLE` の入口を `fpmsyncd` 経由で持つため、FRR がどのプロトコルで LSP を立てても APP_DB → [orchagent](../../reference/glossary.md#term-orchagent) → SAI の道は同じです。これは「SONiC 側のデータパスを変えずに、制御プレーンを段階的に増やす」設計です。

## Path Tracing と Telemetry

Path Tracing Midpoint は MCD を HbH-PT に書くだけで、収集側は Regional Collector / TimeSeries DB を SONiC 外側で構築します。SONiC の Telemetry / [gNMI](../../reference/glossary.md#term-gnmi) 章（管理章）で扱う streaming telemetry とは目的が異なりますが、観測データの集約という点で連動させる設計余地があります。

## 関連章

- [02 BGP](../02-bgp/index.md): FRR / BGP 拡張、SRv6 family の制御プレーン。
- [03 VXLAN-EVPN](../03-vxlan-evpn/index.md): EVPN / overlay との接続。
- [04 VRF / ECMP](../04-vrf-ecmp/index.md): VPN / [VRF](../../reference/glossary.md#term-vrf) の一般構造。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 VPN](../../routing/srv6-vpn-hld.md)
- [EVPN-VXLAN HLD](../../routing/evpn-vxlan-hld.md)
- [FRR BGP 統一管理フレームワーク](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)

## 発展トピック

- **uSID (Micro SID)**: 単一 128-bit SID に複数の short SID を carry する圧縮方式 (`uSID`)。SRH の depth を抑えて ASIC リソースを節約する。
- **TI-LFA (Topology-Independent Loop-Free Alternates)**: SR ベースで FRR (Fast Reroute) を実現する手法。SONiC で実装するには FRR 側と SAI 側双方の対応が必要。
- **SRv6 OAM (RFC 9259)**: SRv6 経路の OAM probing。ping / traceroute の拡張で end-to-end SID path を検証する。
- **L3VPN over SRv6 (draft-ietf-bess-srv6-services)**: BGP VPN family を SRv6 underlay で運ぶ。FRR の `address-family ipv4 vpn` + SRv6 locator 設定がドライバ。
- **flow label entropy**: SRv6 outer IPv6 の flow label を inner 5-tuple から生成し、[ECMP](../../reference/glossary.md#term-ecmp) hash entropy を維持する。

## 既知の制約と回避方法

- **`H.Encaps` 未実装での制限**: reduced 版のみ動く段階では、特定 vendor の interop で SRH が違う形になる。peer 側の SRH format を必ず確認する。
- **MPLS LDP の SONiC 直接サポート不足**: SONiC は MPLS data plane を持つが、LDP の運用例は少ない。SR-MPLS / BGP-LU 経由のシグナリングが現実的。
- **SRv6 SID 数 vs ASIC capacity**: SID encode capability と processing depth が ASIC で違う。`SAI_OBJECT_TYPE_MY_SID_ENTRY` の capacity を必ず確認。
- **SRv6 と MPLS 共存**: 同一 router で SRv6 と MPLS を同時に扱うとき、orch 側のリソース取り合いが起こる。設計を分離するのが安全。

## 将来計画 / ロードマップ

- `segment-routing-over-ipv6-srv6-hld` の Phase 2 以降が継続テーマ。HMAC、sBFD、Binding SID、Adj SID が段階的に対応予定。
- FRR 側で SRv6 control plane の拡張が継続。SONiC は FRR バージョン更新で取り込む。
- Path Tracing の集約パスと SONiC telemetry 統合の議論が future work。

## 関連 RFC / 仕様書

- [RFC 8754](https://datatracker.ietf.org/doc/html/rfc8754) — IPv6 Segment Routing Header (SRH)
- [RFC 8986](https://datatracker.ietf.org/doc/html/rfc8986) — SRv6 Network Programming
- [RFC 9252](https://datatracker.ietf.org/doc/html/rfc9252) — BGP Overlay Services Based on SRv6
- [RFC 9259](https://datatracker.ietf.org/doc/html/rfc9259) — OAM for SRv6
- [RFC 5036](https://datatracker.ietf.org/doc/html/rfc5036) — LDP
- [RFC 3209](https://datatracker.ietf.org/doc/html/rfc3209) — RSVP-TE
- [RFC 8660](https://datatracker.ietf.org/doc/html/rfc8660) — SR-MPLS
- [Path Tracing draft (draft-filsfils-spring-path-tracing)](https://datatracker.ietf.org/doc/draft-filsfils-spring-path-tracing/)

## upstream 開発の最新動向

- `sonic-swss` の `srv6orch` で SID table、locator、MY_SID 拡張の PR が継続。FRR との [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) 整合も並行。
- FRR upstream で SRv6 関連の PR が活発で、SONiC FRR バージョン更新と同期して機能が増える。
- Path Tracing midpoint の SAI extension が議論段階。実装は限定的だが HLD で expectation が示されている。

<!-- glossary-links-injected: 7c1ab6e0d97f -->
