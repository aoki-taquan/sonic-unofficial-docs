---
title: VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）
description: 'SONiC の VXLAN / VNet 全体設計のハブページ。VTEP（VXLAN Tunnel End Point）と VNet（Virtual Network）の組み合わせで実装され、Phase 1 では VM↔ベアメタル間の VNet ピアリングと Symmetric IRB、Phase 2 では BGP EVPN 統合・L2 VXLAN・HER を扱う。概念・設定/運用・内部実装・制限の派生 4 ページへの導線を示す。'
area: overlay
verification: code-verified
last_verified: 2026-06-06
page_kind: split-hub
sources:
- repo: sonic-net/SONiC
  path: doc/vxlan/Vxlan_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VXLAN_TUNNEL
  - VXLAN_TUNNEL_MAP
  - VNET
  - INTERFACE
  - VLAN_INTERFACE
  - NEIGH_TABLE
  - VRF
  cli:
  - config vxlan
  - show vxlan
  - show mac
  - config vlan
  - config vnet
  - config vrf
  - config bgp
  yang:
  - sonic-vxlan
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-vlan
  - sonic-vnet
  - sonic-vrf
  - sonic-bgp-peergroup
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 03 章: VXLAN / EVPN とオーバーレイ](../topics/03-vxlan-evpn/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    現行 master で実装済みを確認。`sonic-swss/orchagent/vxlanorch.h:268,414,462,499,512,541` で `VxlanTunnelOrch` / `VxlanTunnelMapOrch` / `VxlanVrfMapOrch` / `EvpnRemoteVnip2pOrch` / `EvpnRemoteVnip2mpOrch` / `EvpnNvoOrch`、`vnetorch.h:250,362,381,504,618` で `VNetOrch` / `MonitorOrch` / `BfdMonitorOrch` / `VNetRouteOrch` / `VNetCfgRouteOrch`、`sonic-swss-common/common/schema.h:85-87,435` で `APP_VXLAN_TUNNEL_TABLE_NAME` / `APP_VXLAN_TUNNEL_MAP_TABLE_NAME` / `APP_VXLAN_FDB_TABLE_NAME` / `STATE_VXLAN_TUNNEL_TABLE_NAME`、`vxlanorch.cpp:534,903,1160` で EVPN 経由のトンネル生成 (`TNL_CREATION_SRC_EVPN`) を確認（verified at: 2026-05-09）。HLD で言及される実装は `VxlanOrch` ではなく **`VxlanTunnelOrch`**（複数の Orch2 派生クラスに分割）として現行 master に存在する。

# VXLAN / VNet 全体設計（VxlanOrch / VnetOrch / VRF mapper）

!!! info "章分割済み（このページは概要ハブ）"
    本ページは元 HLD の **概要ハブ** に絞り、詳細は派生ページに分割している。詳細を読む場合は以下へ:

    - **[VXLAN / VNet 概念](vxlan-sonic-concepts.md)** — VTEP と VNet の関係、L2 / L3 VXLAN の作り分け、Phase 1 / Phase 2 スコープ、スケール目標
    - **[VXLAN / VNet 設定と運用](vxlan-sonic-operations.md)** — CONFIG_DB / APP_DB スキーマ、`config vxlan` / `show vxlan` CLI、VNet ピアリング設定例、トラブルシュート
    - **[VXLAN / VNet 内部実装](vxlan-sonic-internals.md)** — Orch 群（`VxlanTunnelOrch` / `VnetOrch` / `VnetRouteOrch` / `VrfMgrD` 等）と SAI 属性対応表
    - **[VXLAN / VNet 制限事項と既知の課題](vxlan-sonic-limitations.md)** — Warm restart 非対応、Phase 1 スコープ外項目、`sonic-swss#2829` 等の既知の問題

## 読み手が知りたいこと

1. [SONiC](../reference/glossary.md#term-sonic) の [VXLAN](../reference/glossary.md#term-vxlan) は **[VTEP](../reference/glossary.md#term-vtep) と VNet の組合せ** とよく言われるが、両者の関係は？ → [概念](vxlan-sonic-concepts.md)
2. **L2 VXLAN と L3 VXLAN** はどう作り分けられる？ → [概念](vxlan-sonic-concepts.md) / [SAI](../reference/glossary.md#term-sai) 属性は [内部実装](vxlan-sonic-internals.md)
3. **どの [orchagent](../reference/glossary.md#term-orchagent) が何を担当** するのか？ → [内部実装](vxlan-sonic-internals.md)
4. **[CONFIG_DB](../reference/glossary.md#term-config_db) / APP_DB に何を入れれば** VNet ピアリングが動くのか？ → [設定と運用](vxlan-sonic-operations.md)
5. **[BGP](../reference/glossary.md#term-bgp) [EVPN](../reference/glossary.md#term-evpn) との関係**は？ Phase 1 と Phase 2 で何が違う？ → [概念](vxlan-sonic-concepts.md) / [制限事項](vxlan-sonic-limitations.md)
6. **Warm restart** は使えるのか？ → [制限事項](vxlan-sonic-limitations.md)
7. トラブル時に最低限見るテーブルは？ → [設定と運用 §トラブルシューティング](vxlan-sonic-operations.md#5)

## 全体像（VTEP + VNet + Orch 群）

SONiC の VXLAN は **VTEP（VXLAN Tunnel End Point）と VNet（Virtual Network）の組み合わせ** で実装される。[HLD](../reference/glossary.md#term-hld) は次のスコープを定める[^1]:

- **Phase 1**: VTEP として動作。顧客 VM ↔ ベアメタルサーバ間の VNet ピアリング、Symmetric IRB（RIOT）の分散 VXLAN ルーティング
- **Phase 2**: BGP EVPN 統合、L2 VXLAN（タグ・無タグ）、HER（Head End Replication）、CLI 整備

Kernel [VRF](../reference/glossary.md#term-vrf)（L3mdev）の programming は **本 HLD のスコープ外**[^1]。

主要 orchagent と CONFIG_DB → APP_DB → SAI の流れ:

```mermaid
flowchart TB
    subgraph CONFIG_DB
      VXT[VXLAN_TUNNEL]
      VXM[VXLAN_TUNNEL_MAP]
      VNET[VNET]
      INTF[INTERFACE / VLAN_INTERFACE]
      NEIGH[NEIGH_TABLE]
    end
    VNET --> VRFM[VrfMgrD]
    VRFM -->|kernel L3mdev| KERN[Linux kernel]
    VRFM --> VNETT[(APP_DB VNET_TABLE)]
    VNETT --> VNO[VnetOrch]
    INTF --> IM[IntfMgrD]
    IM -->|VRF 確認後| ITT[(APP_DB INTF_TABLE)]
    ITT --> IO[IntfsOrch]
    IO --> VNO
    VXT --> VXO[VxlanTunnelOrch]
    VXM --> VXO
    NEIGH --> NB[NeighOrch]
    VNO --> VXO
    VNO --> VRO[VnetRouteOrch]
    VRO --> APPR[(APP_DB VNET_ROUTE_*)]
    APPR --> VRO
    VRO --> SAI[SAI/SDK]
    VXO --> SAI
    FDB[FdbOrch] --> VXO
```

各 Orch の責務分担は [vxlan-sonic-internals.md](vxlan-sonic-internals.md) を参照。SAI 属性対応（`SAI_TUNNEL_TYPE_VXLAN` / mapper / termination）も同ページ。

## 干渉する機能

- **BGP EVPN（Phase 2）**: 経路供給源として `VNET_ROUTE_TUNNEL_TABLE` を埋める。詳細は [EVPN VXLAN HLD](../routing/evpn-vxlan-hld.md)
- **[VLAN](../reference/glossary.md#term-vlan) / VLAN_MEMBER**: L2 VXLAN は VLAN ↔ VNI mapping 前提
- **VRF（通常 VRF）**: `VrfOrch` 経由
- **[DASH](../reference/glossary.md#term-dash) / [SmartSwitch](../reference/glossary.md#term-smartswitch)**: 新しい HLD（[ENI Based Forwarding](smartswitch-eni-based-forwarding.md)）は本 HLD の VxLAN tunnel を利用
- **MC-[LAG](../reference/glossary.md#term-lag) / dual-ToR**: 拡張あり

制限事項の詳細は [vxlan-sonic-limitations.md](vxlan-sonic-limitations.md) を参照。

<!-- evidence:
source: sonic-net/SONiC/doc/vxlan/Vxlan_hld.md#L299-L330 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  VxlanOrch creates the tunnel and attaches encap and decap mappers. Seperate tunnels are created for L2 Vxlan and L3 Vxlan ...
  VnetOrch creates ingress/Egress (based on context) VRF or BRIDGE in SAI for a VNet and also maintains the peering list.
  VnetRouteOrch fetch the VRF and peering information for replicating the routes
reasoning: VxlanOrch / VnetOrch / VnetRouteOrch の責務分担と peer_list 経路複製の根拠。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/SONiC/doc/vxlan/Vxlan_hld.md#L299-L330 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)"

    **出典**:

    `sonic-net/SONiC/doc/vxlan/Vxlan_hld.md#L299-L330 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)`

    **抜粋**:

    ```text
    VxlanOrch creates the tunnel and attaches encap and decap mappers. Seperate tunnels are created for L2 Vxlan and L3 Vxlan ...
    VnetOrch creates ingress/Egress (based on context) VRF or BRIDGE in SAI for a VNet and also maintains the peering list.
    VnetRouteOrch fetch the VRF and peering information for replicating the routes
    ```

    **判断根拠**: VxlanOrch / VnetOrch / VnetRouteOrch の責務分担と peer_list 経路複製の根拠。

<!-- evidence-rendered:end -->

## 関連トピック

- [Topics: VXLAN / EVPN](../topics/03-vxlan-evpn/index.md) — VXLAN/EVPN 全体像
- [HLD: EVPN VXLAN](../routing/evpn-vxlan-hld.md)

## 関連ページ
- [CLI: config vxlan](../reference/cli/config-vxlan.md)
- [CONFIG_DB: VXLAN_TUNNEL](../reference/config-db/vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](../reference/config-db/vxlan-tunnel-map.md)
- [YANG: sonic-vxlan](../reference/yang/sonic-vxlan.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/Vxlan_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: VXLAN / EVPN / VNET オーバーレイ](../topics/03-vxlan-evpn/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 97b009f45d48 -->
