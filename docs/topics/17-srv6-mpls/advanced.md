---
title: 発展トピック
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

base 機能の上で広がる SRv6 / MPLS / Path Tracing 関連のトピックを、他章へのリンクと一緒にまとめます。

## EVPN / BGP との接続

SRv6 と EVPN-VXLAN は「IPv6 underlay の上で L2/L3 サービスを運ぶ」点で目的が重なる領域があります。SONiC では現状、EVPN は VXLAN encap が中心で、SRv6 を underlay にする実装は HLD レベルでも限定的です。BGP 系の SRv6 family（BGP-LU / SR-MPLS / SRv6 L3VPN）を扱う場合は、FRR の SRv6 制御プレーン側の対応状況を最初に確認します。

- L3VPN over SRv6 を運用するには、FRR で SRv6 L3VPN family を有効化し、SONiC 側で `srv6orch` の VPN 経路（`srv6_prefix_agg_id_table_`、`vpn_sid`）が programming されることを確認します（[内部実装](internals.md) を参照）。
- EVPN-VXLAN の章は [03 VXLAN-EVPN](../03-vxlan-evpn/index.md) を参照してください。EVPN over SRv6 を試す場合の本章との接点は、VPN SID の運用と EVPN type-5 route の対応関係です。

## FRR の SRv6 統一管理

`sonic-frr-bgp-extended-unified-configuration-management-framework.md` で議論されている統一管理フレームワークは、bgpcfgd / frrcfgd の handler 群を再整理し、SRv6 / MPLS / EVPN を含む BGP 拡張の設定面を統一する方向にあります。Static SID は `SRv6Mgr` の vtysh 経由ですが、将来的に動的 SRv6（FRR の `segment-routing srv6` 設定の自動化）も同じ枠組みに乗ることが想定されます。

## SRv6 base HLD の後続 phase

SRv6 base HLD は Phase 1 として `END` / `END.DT46` / `H.Encaps.Red` を実装し、後続として次の項目が予定されています。

- `H.Encaps`（reduced でない通常 encap）
- `END.B6.Encaps[.Red]`（Binding SID）
- `END.X`（Adj SID） — 一部は SID L3Adj HLD で実装済み
- HMAC（SRH integrity）
- sBFD（segment routing BFD）
- anycast SID
- MySID counter

これらは段階的に `srv6orch` と SAI に追加されるため、運用設計時には「自社が依存する behavior が現在の master にあるか」をコード位置（[内部実装](internals.md)）で確認します。

## MPLS の動的シグナリング

LDP / RSVP-TE / SR-MPLS のような動的シグナリングは、master 時点では FRR 側機能に依存します。SONiC 側は `LABEL_ROUTE_TABLE` の入口を `fpmsyncd` 経由で持つため、FRR がどのプロトコルで LSP を立てても APP_DB → orchagent → SAI の道は同じです。これは「SONiC 側のデータパスを変えずに、制御プレーンを段階的に増やす」設計です。

## Path Tracing と Telemetry

Path Tracing Midpoint は MCD を HbH-PT に書くだけで、収集側は Regional Collector / TimeSeries DB を SONiC 外側で構築します。SONiC の Telemetry / gNMI 章（管理章）で扱う streaming telemetry とは目的が異なりますが、観測データの集約という点で連動させる設計余地があります。

## 関連章

- [02 BGP](../02-bgp/index.md): FRR / BGP 拡張、SRv6 family の制御プレーン。
- [03 VXLAN-EVPN](../03-vxlan-evpn/index.md): EVPN / overlay との接続。
- [04 VRF / ECMP](../04-vrf-ecmp/index.md): VPN / VRF の一般構造。

## 関連ページ

- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SRv6 VPN](../../routing/srv6-vpn-hld.md)
- [EVPN-VXLAN HLD](../../routing/evpn-vxlan-hld.md)
- [FRR BGP 統一管理フレームワーク](../../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md)
