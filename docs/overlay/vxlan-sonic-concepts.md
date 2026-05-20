---
title: VXLAN / VNet 概念（VTEP + VNet + L2/L3 トンネル）
description: VXLAN / VNet の概念・用語・設計思想。VTEP（VXLAN Tunnel End Point）と VNet（Virtual Network）の関係、L2
  VXLAN / L3 VXLAN の作り分け、Phase 1 / Phase 2 スコープを整理する。
area: overlay
verification: code-verified
last_verified: 2026-05-09
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/vxlan/Vxlan_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - VXLAN_TUNNEL
  - VXLAN_TUNNEL_MAP
  - VNET
  - VRF
  - VLAN
  - VXLAN_EVPN_NVO
  - BGP_NEIGHBOR
  cli:
  - config vlan
  - config vxlan
  - config vnet
  - config bgp
  - show bgp
  - config vrf
  - show vlan
  yang:
  - sonic-vxlan
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-vlan
  - sonic-vnet
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
---

# VXLAN / VNet 概念

このページは [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) の派生ページで、**概念・用語・スコープ** に絞って整理する。設定・運用は [vxlan-sonic-operations.md](vxlan-sonic-operations.md)、Orch 群の内部実装は [vxlan-sonic-internals.md](vxlan-sonic-internals.md)、制限事項は [vxlan-sonic-limitations.md](vxlan-sonic-limitations.md) を参照。

## 1. VTEP と VNet の関係

[SONiC](../reference/glossary.md#term-sonic) の [VXLAN](../reference/glossary.md#term-vxlan) は **[VTEP](../reference/glossary.md#term-vtep)（VXLAN Tunnel End Point）と VNet（Virtual Network）の組み合わせ** で実装される[^1]。VTEP は VXLAN encap/decap を行う物理エンドポイント、VNet は **同一 VTEP 内に複数並立する仮想ネットワーク** を識別する論理境界である。1 つの VTEP が複数 VNet を保持し、各 VNet が独自の [VRF](../reference/glossary.md#term-vrf) または BRIDGE として動作する。

[HLD](../reference/glossary.md#term-hld) のスコープ[^1]:

- **Phase 1**: VTEP として動作。顧客 VM ↔ ベアメタルサーバ間の VNet ピアリング、Symmetric IRB（RIOT）の分散 VXLAN ルーティング
- **Phase 2**: [BGP](../reference/glossary.md#term-bgp) [EVPN](../reference/glossary.md#term-evpn) 統合、L2 VXLAN（タグ・無タグ）、HER（Head End Replication）、CLI 整備

Kernel VRF（L3mdev）の programming は **本 HLD のスコープ外**[^1]。

## 2. L2 VXLAN と L3 VXLAN の作り分け

`VxlanOrch` は `VXLAN_TUNNEL` / `VXLAN_TUNNEL_MAP` から **L2 VXLAN（[VLAN](../reference/glossary.md#term-vlan) ↔ VNI）** と **L3 VXLAN（VRF ↔ VNI）** を **別トンネル** として作る[^1]。それぞれに encap/decap mapper を attach。

| 区分 | mapper | 主用途 |
|------|--------|--------|
| L2 VXLAN | `VLAN_ID ↔ VNI` | 同一 broadcast domain の延伸 |
| L3 VXLAN | `VIRTUAL_ROUTER_ID ↔ VNI` | tenant 間 routing、Symmetric IRB |

L3 VXLAN は **`VIRTUAL_ROUTER_ID ↔ VNI` mapper が中核**。VTEP は P2MP の termination として登録する[^1]。

## 3. VNet ピアリングの考え方

`VNET` テーブルの `peer_list` 属性で **他 VNet を peer として宣言** すると、`VnetRouteOrch` がピア VNet にも経路を複製する[^1]。同テナント内で複数 VNet を疎通させたい場合に使う。

## 4. スケール目標（Phase 1）

| 項目 | 想定値 |
|------|-------|
| VNI 数 | 8K |
| Tunnel encap 数 | 128K |
| VM 数 | 512K |
| VRF 数 | 128 |
| ルート数 | 512K |

設計目標であり実 [ASIC](../reference/glossary.md#term-asic) のスケールに依存する[^1]。

## 関連ページ

- [VXLAN / VNet 全体設計（概要ハブ）](vxlan-sonic.md) — 元 HLD ページ
- [vxlan-sonic-operations.md](vxlan-sonic-operations.md) — 設定 / CLI / 確認手順
- [vxlan-sonic-internals.md](vxlan-sonic-internals.md) — Orch 内部実装と [SAI](../reference/glossary.md#term-sai) 属性
- [vxlan-sonic-limitations.md](vxlan-sonic-limitations.md) — 制限事項と既知の課題

## 引用元

[^1]: `sonic-net/SONiC` `doc/vxlan/Vxlan_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 7b27b638c4f3 -->
