---
title: BGP / EVPN 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# BGP / EVPN 関連

## 概要

BGP、EVPN、VXLAN / VNET、route-map、prefix-list / prefix-set、BMP などルーティング制御を横断して追う入口です。

主要キーワード: `BGP`, `EVPN`, `VXLAN`, `VNET`, `route-map`, `prefix-list`, `prefix-set`, `BMP`

## 関連ページ

- [Policy Based Hashing（PBH: NVGRE / VxLAN inner 5-tuple）](../architecture/sonic-policy-based-hashing.md) (area: `architecture`, verification: `hld-only`)
- [VNET の Local Endpoint Forwarding（DPU 直結 nexthop の最適化）](../overlay/vnet-local-endpoint-forwarding.md) (area: `overlay`, verification: `code-verified`)
- [VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）](../overlay/vxlan-sonic.md) (area: `overlay`, verification: `code-verified`)
- [config bgp サブコマンド](../reference/cli/config-bgp.md) (area: `reference`, verification: `code-verified`)
- [config vxlan サブコマンド](../reference/cli/config-vxlan.md) (area: `reference`, verification: `code-verified`)
- [show bgp / show ip bgp / show ipv6 bgp サブコマンド](../reference/cli/show-bgp.md) (area: `reference`, verification: `code-verified`)
- [show route-map コマンド](../reference/cli/show-route-map.md) (area: `reference`, verification: `code-verified`)
- [BGP_AGGREGATE_ADDRESS テーブル](../reference/config-db/bgp-aggregate-address.md) (area: `reference`, verification: `code-verified`)
- [BGP_DEVICE_GLOBAL テーブル](../reference/config-db/bgp-device-global.md) (area: `reference`, verification: `code-verified`)
- [BGP_GLOBALS テーブル](../reference/config-db/bgp-globals.md) (area: `reference`, verification: `code-verified`)
- [BGP_NEIGHBOR_AF テーブル](../reference/config-db/bgp-neighbor-af.md) (area: `reference`, verification: `code-verified`)
- [BGP_NEIGHBOR テーブル](../reference/config-db/bgp-neighbor.md) (area: `reference`, verification: `code-verified`)
- [BGP_PEER_GROUP_AF テーブル](../reference/config-db/bgp-peer-group-af.md) (area: `reference`, verification: `code-verified`)
- [BGP_PEER_GROUP テーブル](../reference/config-db/bgp-peer-group.md) (area: `reference`, verification: `code-verified`)
- [PREFIX_LIST テーブル (BGP)](../reference/config-db/prefix-list.md) (area: `reference`, verification: `code-verified`)
- [PREFIX_SET テーブル](../reference/config-db/prefix-set.md) (area: `reference`, verification: `code-verified`)
- [ROUTE_MAP テーブル](../reference/config-db/route-map.md) (area: `reference`, verification: `code-verified`)
- [VXLAN_TUNNEL_MAP テーブル](../reference/config-db/vxlan-tunnel-map.md) (area: `reference`, verification: `code-verified`)
- [VXLAN_TUNNEL テーブル](../reference/config-db/vxlan-tunnel.md) (area: `reference`, verification: `code-verified`)
- [sonic-bgp-global YANG](../reference/yang/sonic-bgp-global.md) (area: `reference`, verification: `code-verified`)
- [sonic-bgp-neighbor YANG](../reference/yang/sonic-bgp-neighbor.md) (area: `reference`, verification: `code-verified`)
- [sonic-bgp-peergroup YANG](../reference/yang/sonic-bgp-peergroup.md) (area: `reference`, verification: `code-verified`)
- [sonic-route-map YANG](../reference/yang/sonic-route-map.md) (area: `reference`, verification: `code-verified`)
- [sonic-vxlan YANG](../reference/yang/sonic-vxlan.md) (area: `reference`, verification: `code-verified`)
- [BGP セッション向け BFD ハードウェアオフロード（bfdsyncd 経路）](../routing/bfd-hw-offload-for-bgp-session.md) (area: `routing`, verification: `discrepancy-found`)
- [BGP Loading Optimization（fpmsyncd flush / orchagent ring buffer / async sairedis）](../routing/bgp-loading-optimization-for-sonic.md) (area: `routing`, verification: `code-verified`)
- [BGP PIC（Prefix Independent Convergence / NHG 階層）](../routing/bgp-prefix-independent-convergence-architecture-document.md) (area: `routing`, verification: `code-verified`)
- [BBR 連動の BGP ルート集約（BGP_AGGREGATE_ADDRESS）](../routing/bgp-route-aggregation-with-bbr-awareness.md) (area: `routing`, verification: `code-verified`)
- [BGP Route Install Error Handling（ERROR_ROUTE_TABLE / FIB-install pending）](../routing/bgp-route-install-error-handling.md) (area: `routing`, verification: `discrepancy-found`)
- [BGP router-id を明示的に設定する（DEVICE_METADATA.bgp_router_id）](../routing/bgp-router-id-explicitly-configured.md) (area: `routing`, verification: `code-verified`)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (area: `routing`, verification: `code-verified`)
- [BGP Suppress FIB Pending（dplane_fpm_nl + RTM_F_OFFLOAD）](../routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md) (area: `routing`, verification: `hld-only`)
- [bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）](../routing/bgpcfgd-dynamic-peer-modification-support.md) (area: `routing`, verification: `code-verified`)
- [BMP（BGP Monitoring Protocol / BMP_STATE_DB）](../routing/bmp-for-monitoring-sonic-bgp-info.md) (area: `routing`, verification: `code-verified`)
- [EVPN VXLAN（FRR BGP-EVPN / VTEP / VRF / Type-2/Type-5）](../routing/evpn-vxlan-hld.md) (area: `routing`, verification: `discrepancy-found`)
- [EVPN VXLAN Multihoming（ESI / DF election / split-horizon）](../routing/evpn-vxlan-multihoming.md) (area: `routing`, verification: `discrepancy-found`)
- [Overlay ECMP with BFD monitoring（VxLAN VNet ルートと BFD 連動）](../routing/overlay-ecmp-with-bfd-monitoring.md) (area: `routing`, verification: `code-verified`)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (area: `routing`, verification: `code-verified`)
- [Weighted ECMP（WCMP / BGP link-bandwidth ext community）](../routing/sonic-weighted-ecmp.md) (area: `routing`, verification: `code-verified`)
- [ECMP inner packet hashing テストプラン（PBH 経由の VxLAN/NVGRE 内側 5-tuple ハッシュ）](../routing/test-plan-for-inner-packet-hashing-in-ecmp.md) (area: `routing`, verification: `code-verified`)
- [VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）](../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) (area: `routing`, verification: `hld-only`)

## 関連カテゴリ

- [Dual-ToR 関連](dual-tor.md)
- [Multi-ASIC / VOQ chassis 関連](multi-asic.md)
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md)
